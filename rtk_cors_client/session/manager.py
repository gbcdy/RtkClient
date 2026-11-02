# -*- coding: utf-8 -*-
"""SessionManager — оркестрация подключения и сбора данных (без Qt).

Инкапсулирует «мозг» NTRIPWorker из монолитного rtk4.py:
  * цикл приёма байтов из сокета,
  * декодирование chunked / парсинг RTCM-кадров,
  * dispatch сообщений в коллекторы,
  * периодическая отправка GGA, статистика, таймауты СК,
  * сохранение raw RTCM и финального отчёта через экспортеры.

Класс не зависит от PyQt5 и полностью тестируется офлайн
(см. tests/test_session_manager.py) — сеть передаётся как инъекция.
"""
import socket
import time
from datetime import datetime
from pathlib import Path

from rtk_cors_client.config.constants import (
    COORDINATE_SYSTEM_MESSAGES,
    DATA_DIR_NAME,
    KNOWN_RTCM_MESSAGES,
    LOGS_DIR_NAME,
    PROPRIETARY_RANGE,
    PROPRIETARY_TARGETS,
    USER_AGENT,
)
from rtk_cors_client.exporters.raw_rtcm import RawRTCMExporter
from rtk_cors_client.ntrip.chunked import ChunkedTransferDecoder
from rtk_cors_client.rtcm.collectors import create_default_registry
from rtk_cors_client.rtcm.messages import RTCMMessageDecoder
from rtk_cors_client.rtcm.parser import RTCMFrameParser
from rtk_cors_client.session.coordinator import CollectionCoordinator
from rtk_cors_client.utils.nmea import generate_gga


class SessionManager:
    def __init__(self, config: dict, socket_factory=None, callbacks=None,
                 registry=None, data_dir=None, logs_dir=None):
        """
        Args:
            config: словарь конфигурации (как ConfigManager.config).
            socket_factory: вызываемый объект, возвращающий сокет
                            (по умолчанию socket.socket — для тестов подменяется).
            callbacks: опциональный объект с методами-коллбэками
                       log/rtcm_message/unknown_message/status_changed/
                       stats_updated/last_message_updated/collection_progress/
                       collection_complete/cs_message_received.
            registry: CollectorRegistry (по умолчанию — встроенные коллекторы).
        """
        self.config = config
        self.socket_factory = socket_factory or (lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.callbacks = callbacks

        self.registry = registry if registry is not None else create_default_registry()
        self.data_dir = Path(data_dir) if data_dir else Path(DATA_DIR_NAME)
        self.logs_dir = Path(logs_dir) if logs_dir else Path(LOGS_DIR_NAME)

        self.coordinator = CollectionCoordinator(
            config=self.config,
            registry=self.registry,
            log_fn=self._log,
            emit_progress=lambda p: self._emit("collection_progress", p),
            emit_complete=lambda p: self._emit("collection_complete", p),
            request_stop=self.stop,
            data_dir=self.data_dir,
        )

        self.frame_parser = RTCMFrameParser()
        self.chunked_decoder = ChunkedTransferDecoder(
            on_terminal_chunk=lambda: self._log("📦 Сервер отправил терминальный chunk (0)", "info")
        )
        self.raw_exporter = RawRTCMExporter()

        self.running = False
        self.sock = None
        self.stats = self._initial_stats()
        self._last_bytes = 0
        self._last_time = time.time()

    # ------------------------------------------------------------------
    # Статистика / коллбэки
    # ------------------------------------------------------------------
    def _initial_stats(self) -> dict:
        return {
            "connected_since": None,
            "bytes_received": 0,
            "bytes_sent": 0,
            "messages_parsed": 0,
            "messages_valid": 0,
            "messages_crc_failed": 0,
            "unknown_messages": 0,
            "gga_sent": 0,
            "bytes_per_sec": 0.0,
            "last_message_id": None,
            "last_message_name": None,
            "last_message_time": None,
        }

    def _emit(self, name, *args):
        cb = getattr(self.callbacks, name, None) if self.callbacks else None
        if callable(cb):
            cb(*args)

    def _log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._emit("log_message", f"[{timestamp}] {message}", level)

    # ------------------------------------------------------------------
    # Соединение
    # ------------------------------------------------------------------
    def _basic_auth(self) -> str:
        """Base64-строка 'login:password' из конфигурации."""
        import base64
        raw = f"{self.config['username']}:{self.config['password']}"
        return base64.b64encode(raw.encode()).decode()

    def _build_request(self, path: str) -> str:
        """HTTP-запрос NTRIP v1/v2 (используется и для SOURCETABLE)."""
        return (
            f"GET /{path} HTTP/1.1\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
            f"Authorization: Basic {self._basic_auth()}\r\n"
            f"Accept: */*\r\n"
            f"Host: {self.config['ntrip_server']}:{self.config['ntrip_port']}\r\n"
            f"Ntrip-Version: Ntrip/2.0\r\n"
            f"Connection: close\r\n\r\n"
        )

    def connect(self) -> bool:
        """Подключение к NTRIP-серверу. Возвращает True при успехе."""
        server = self.config["ntrip_server"]
        port = self.config["ntrip_port"]
        mountpoint = self.config["mountpoint"]

        self._emit("status_changed", "Подключение...")
        self._log(f"Подключение к {server}:{port}/{mountpoint}")

        try:
            self.sock = self.socket_factory()
            self.sock.settimeout(10)
            self.sock.connect((server, port))
            self.sock.settimeout(1.0)

            request = self._build_request(mountpoint)
            self.sock.send(request.encode())
            self.stats["bytes_sent"] += len(request)

            response = b""
            while b"\r\n\r\n" not in response:
                chunk = self.sock.recv(1024)
                if not chunk:
                    raise ConnectionError("Сервер закрыл соединение")
                response += chunk

            header_end = response.find(b"\r\n\r\n")
            header = response[:header_end].decode('utf-8', errors='ignore')
            remaining_data = response[header_end + 4:]

            if "transfer-encoding: chunked" in header.lower():
                self._log("📦 Режим NTRIP v2 chunked encoding", "info")
                self.chunked = True
            else:
                self.chunked = False

            if "200 OK" in header or "ICY 200 OK" in header:
                self._log("✅ Аккаунт валиден, подключение установлено", "success")
                self._emit("status_changed", "Подключено")
                self.stats["connected_since"] = datetime.now().isoformat()

                if self.config.get("save_raw_rtcm"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    raw_path = self.data_dir / f"stream_{timestamp}.rtcm"
                    self.raw_exporter.open(raw_path)
                    self._log(f"📁 Сырой поток: {raw_path.name}")

                gga = self._make_gga()
                self.sock.send(gga.encode())
                self.stats["bytes_sent"] += len(gga)
                self.stats["gga_sent"] += 1
                self._log(f"📤 Отправлен первый GGA {gga}", "info")

                cs_timeout = self.config.get("cs_messages_timeout", 120)
                self._log("ℹ️ Ожидание сообщений системы координат (1021-1027, 1300, 1302)...", "info")
                self._log(f"ℹ️ Таймаут ожидания: {cs_timeout}с", "info")

                if remaining_data:
                    self._feed(remaining_data)

                return True
            elif "401" in header:
                raise PermissionError("Ошибка авторизации")
            elif "404" in header:
                raise FileNotFoundError("Маунтпоинт не найден")
            elif "SOURCETABLE" in header:
                raise ValueError("Получена таблица источников")
            else:
                raise ConnectionError(f"Неожиданный ответ:\n{header[:200]}")

        except Exception as e:
            self._log(f"❌ Ошибка подключения: {e}", "error")
            self._emit("status_changed", "Ошибка подключения")
            # освобождаем сокет при неудачном подключении (как в оригинале)
            if self.sock is not None:
                try:
                    self.sock.close()
                except Exception:
                    pass
            return False

    def _make_gga(self) -> str:
        return generate_gga(
            self.config["base_lat"],
            self.config["base_lon"],
            self.config["base_alt"],
            noise_std=self.config.get("noise_std", 0.00001),
        )

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Блокирующий цикл приёма (аналог QThread.run оригинала)."""
        self.running = True

        if not self.connect():
            return

        last_gga_time = time.time()
        gga_interval = self.config.get("gga_interval", 2.0)
        auto_stop_timeout = self.config.get("auto_stop_timeout", 300)
        start_time = time.time()
        last_cs_check = start_time

        try:
            while self.running:
                try:
                    try:
                        data = self.sock.recv(4096)
                    except socket.timeout:
                        data = None

                    if data:
                        self.stats["bytes_received"] += len(data)
                        self.raw_exporter.write_bytes(data)
                        self._feed(data)

                    now = time.time()
                    if now - self._last_time >= 1.0:
                        elapsed = now - self._last_time
                        self.stats["bytes_per_sec"] = (
                            (self.stats["bytes_received"] - self._last_bytes) / elapsed
                        )
                        self._last_bytes = self.stats["bytes_received"]
                        self._last_time = now

                    if now - last_gga_time >= gga_interval:
                        gga = self._make_gga()
                        try:
                            self.sock.send(gga.encode())
                            self.stats["bytes_sent"] += len(gga)
                            self.stats["gga_sent"] += 1
                            last_gga_time = now
                            self._log(f"Отправка GGA: {gga}", "info")
                        except Exception as e:
                            self._log(f"❌ Ошибка отправки GGA: {e}", "error")
                            break

                    if now - last_cs_check >= 10.0:
                        self.coordinator.check_cs_timeout(self.stats.get("connected_since"))
                        last_cs_check = now

                    self._emit("stats_updated", self.stats.copy())

                    if (self.config.get("auto_stop_on_complete") and
                            now - start_time > auto_stop_timeout):
                        self._log(
                            f"⏰ Таймаут автоостановки ({auto_stop_timeout}с). Сохраняем что есть...",
                            "warning",
                        )
                        self.coordinator.save_final_report(self.stats.copy())
                        self._emit("collection_complete", {})
                        break

                except socket.timeout:
                    continue
                except Exception as e:
                    if "10038" in str(e) or "not a socket" in str(e).lower():
                        self._log("🔌 Сокет закрыт", "info")
                        break
                    self._log(f"❌ Ошибка в цикле: {e}", "error")
                    break

        except Exception as e:
            self._log(f"❌ Критическая ошибка: {e}", "error")
        finally:
            if self.config.get("save_params_json") and self.stats["messages_parsed"] > 0 \
                    and not self.coordinator.report_saved:
                self.coordinator.save_final_report(self.stats.copy())
            self.cleanup()

    def stop(self) -> None:
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def cleanup(self) -> None:
        """Закрытие сокета и файловых ресурсов."""
        self.stop()
        self.raw_exporter.close()
        self._emit("status_changed", "Отключено")
        self._log("Соединение закрыто, ресурсы освобождены")

    # ------------------------------------------------------------------
    # Обработка данных
    # ------------------------------------------------------------------
    def _feed(self, data: bytes) -> None:
        """chunked → декодер, иначе напрямую в парсер кадров; разбор кадров."""
        if getattr(self, "chunked", False):
            extracted = self.chunked_decoder.feed(data)
            if extracted:
                frames = self.frame_parser.feed_and_parse(extracted)
            else:
                frames = []
        else:
            frames = self.frame_parser.feed_and_parse(data)

        for frame in frames:
            self._handle_frame(frame)

    def _handle_frame(self, frame) -> None:
        msg_id = frame.msg_id
        msg_name = KNOWN_RTCM_MESSAGES.get(msg_id, f"Unknown_{msg_id}")

        try:
            params = RTCMMessageDecoder.parse(frame.data)
        except Exception as e:
            if self.config.get("log_unknown_messages"):
                self._log(f"⚠️ Ошибка парсинга ID={msg_id}: {e}", "warning")
            return

        is_proprietary = msg_id in PROPRIETARY_RANGE
        is_known = msg_id in KNOWN_RTCM_MESSAGES
        is_cs_message = msg_id in COORDINATE_SYSTEM_MESSAGES

        # Dispatch в коллекторы (реестр)
        self.registry.dispatch(msg_id, params, frame.data)

        # Неизвестное проприетарное — сохраняем HEX-дампы в ProprietaryCollector
        if is_proprietary and not is_known:
            from rtk_cors_client.rtcm.collectors.proprietary import ProprietaryCollector
            for c in self.registry.collectors():
                if isinstance(c, ProprietaryCollector):
                    c.collect_unknown(msg_id, frame.data)
                    break

        # Сигнал в GUI о сообщении СК
        if is_cs_message:
            self._emit("cs_message_received", msg_id, params)

        if is_proprietary and not is_known:
            self.stats["unknown_messages"] += 1
            self._emit("unknown_message", msg_id, frame.data)
            if self.config.get("log_unknown_messages"):
                self._log(
                    f"⚠️ Неизвестное проприетарное ID={msg_id}, {frame.payload_length} байт",
                    "warning",
                )
        else:
            self._emit("rtcm_message", msg_id, msg_name, params)

            if msg_id in (1005, 1006, 1033):
                self._log(f"📡 Параметры базы: {msg_name}", "info")
            elif is_cs_message:
                cs_info = COORDINATE_SYSTEM_MESSAGES[msg_id]
                self._log(f"🌍 СК: {cs_info['name']} — {cs_info['description']}", "success")
            elif msg_id in PROPRIETARY_TARGETS:
                self._log(f"🌍 Проприетарное (СК/геоид?): {msg_name}", "info")

        self.stats["messages_parsed"] += 1
        self.stats["messages_valid"] += 1
        self.stats["last_message_id"] = msg_id
        self.stats["last_message_name"] = msg_name
        self.stats["last_message_time"] = datetime.now().strftime("%H:%M:%S")

        self._emit("last_message_updated", {
            "id": msg_id,
            "name": msg_name,
            "time": self.stats["last_message_time"],
            "length": frame.payload_length,
        })

        self.coordinator.on_message(msg_id)
