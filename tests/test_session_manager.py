# -*- coding: utf-8 -*-
"""Автотесты SessionManager с фейковым сокетом (без сети и без Qt).

Проверяются ключевые сценарии реконструированного ядра:
  * NTRIP v1: рукопожатие 200 OK, разбор RTCM-кадров, dispatch в коллекторы;
  * NTRIP v2 chunked: декодирование chunk-фреймов перед парсером кадров;
  * отправка GGA после подключения;
  * ошибки авторизации (401);
  * сборка финального JSON-отчёта координатором.

Запуск:  python -m unittest tests.test_session_manager -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rtk_cors_client.config.constants import DEFAULT_CONFIG  # noqa: E402
from rtk_cors_client.ntrip.crc24q import CRC24Q  # noqa: E402
from rtk_cors_client.session.manager import SessionManager  # noqa: E402
from tests.fake_socket import FakeSocket  # noqa: E402


def build_rtcm_frame(payload: bytes) -> bytes:
    """Собирает корректный RTCM-кадр: 0xD3 + длина + payload + CRC24Q."""
    length = len(payload)
    header = bytes([0xD3, (length >> 8) & 0x03, length & 0xFF])
    crc = CRC24Q.calculate(header + payload)
    return header + payload + bytes([(crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF])


def frame_1005(station_id=7, x_mm=3791672990000 // 100):
    """Урезанный, но структурно валидный кадр 1005 (msg_id из первых 12 бит)."""
    body = bytearray(9)
    body[0] = (station_id >> 4) & 0xFF          # DF002 bits + start of DF003
    body[1] = ((station_id & 0xF) << 4) | 0x08  # station tail + ARFC flag=1... (unused)
    #DF014..; msg id occupies first 12 bits:
    b = bytearray(9)
    b[0] = 0x03  # 1005 = 0b000001111101 -> first byte 0x03, next nibble F...
    b[1] = 0xE0 | 0x00
    b[2] = 0x00
    # Просто задаём msg_id корректно: 12 бит = 1005 = 0x3ED
    val = (1005 << 52)  # верхние 12 байт-бит из 64
    # соберём первые 8 байт payload big-endian из val + нули
    hi = val.to_bytes(8, "big")
    return build_rtcm_frame(hi + b"\x00" * 3)


class RecordingCallbacks:
    """Коллбэки-шпионы (интерфейс как у CallbackBridge, но без Qt)."""

    def __init__(self):
        self.log = []
        self.rtcm = []           # (msg_id, name, params)
        self.unknown = []         # (msg_id, raw)
        self.status = []          # статусы
        self.stats = []           # словари статистики
        self.progress = []        # словари прогресса
        self.complete = []
        self.cs = []              # (msg_id, params)
        self.last_msg = []

    def log_message(self, message, level="info"):
        self.log.append((message, level))

    def rtcm_message(self, msg_id, msg_name, params):
        self.rtcm.append((msg_id, msg_name, params))

    def unknown_message(self, msg_id, raw_data):
        self.unknown.append((msg_id, raw_data))

    def status_changed(self, status):
        self.status.append(status)

    def stats_updated(self, stats):
        self.stats.append(stats)

    def last_message_updated(self, msg_info):
        self.last_msg.append(msg_info)

    def collection_progress(self, progress):
        self.progress.append(progress)

    def collection_complete(self, progress):
        self.complete.append(progress)

    def cs_message_received(self, msg_id, params):
        self.cs.append((msg_id, params))


def make_manager(responses, tmpdir, **cfg_overrides):
    config = dict(DEFAULT_CONFIG)
    config.update(cfg_overrides)
    config["save_raw_rtcm"] = False
    config["save_params_json"] = False
    sock = FakeSocket(responses)
    mgr = SessionManager(
        config=config,
        socket_factory=lambda: sock,
        callbacks=RecordingCallbacks(),
        data_dir=Path(tmpdir) / "data",
        logs_dir=Path(tmpdir) / "logs",
    )
    return mgr, sock


HEADER_V1 = b"NTRIP/1.0 200 OK\r\nContent-type: gnss/data\r\n\r\n"
HEADER_V2 = (b"NTRIP/2.0 200 OK\r\nContent-Type: gnss/data\r\n"
             b"Transfer-Encoding: chunked\r\n\r\n")


class TestConnectAndParse(unittest.TestCase):
    def test_v1_handshake_and_frames(self):
        """NTRIP v1: подключение, первый GGA, разбор двух RTCM-кадров."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f1 = frame_1005()
            f2 = build_rtcm_frame(bytes([0x03, 0xEA, 0x00]) + b"\x00" * 6)  # 1002-like id
            mgr, sock = make_manager([HEADER_V1, f1, f2], td)
            mgr.run()

            # Запрос GET отправлен с Basic-авторизацией
            req = sock.sent_text()
            self.assertIn("GET /", req)
            self.assertIn("Authorization: Basic", req)

            # Статусы: Подключение... -> Подключено -> Отключено
            self.assertEqual(mgr.callbacks.status[:3],
                             ["Подключение...", "Подключено", "Отключено"])

            # Кадры распознаны по msg_id
            ids = [mid for mid, _n, _p in mgr.callbacks.rtcm]
            self.assertIn(1005, ids)

            # Статистика обновлена
            self.assertGreater(mgr.stats["messages_parsed"], 0)
            self.assertEqual(mgr.stats["messages_valid"], mgr.stats["messages_parsed"])

            # GGA отправлен (запрос + минимум один GGA)
            self.assertGreaterEqual(mgr.stats["gga_sent"], 1)
            self.assertIn("GPGGA", sock.sent_text())

    def test_v2_chunked_decoding(self):
        """NTRIP v2: RTCM-кадры внутри chunked-фреймов декодируются."""
        import tempfile
        frame = frame_1005()
        chunk = ("%X\r\n" % len(frame)).encode() + frame + b"\r\n" + b"0\r\n\r\n"
        with tempfile.TemporaryDirectory() as td:
            mgr, sock = make_manager([HEADER_V2, chunk], td)
            mgr.run()
            ids = [mid for mid, _n, _p in mgr.callbacks.rtcm]
            self.assertIn(1005, ids)
            self.assertTrue(any("chunked" in m for m, _l in mgr.callbacks.log))

    def test_auth_failure_401(self):
        """401 -> статус 'Ошибка подключения', run() завершается сразу."""
        import tempfile
        hdr = b"NTRIP/1.0 401 Unauthorized\r\n\r\n"
        with tempfile.TemporaryDirectory() as td:
            mgr, sock = make_manager([hdr], td)
            mgr.run()
            self.assertEqual(mgr.callbacks.status[-1], "Ошибка подключения")
            self.assertEqual(mgr.stats["messages_parsed"], 0)
            self.assertFalse(sock.closed is False)  # cleanup закрыл сокет

    def test_unknown_proprietary_message(self):
        """Неизвестное проприетарное сообщение -> unknown_message сигнал."""
        import tempfile
        # msg_id 4094 — вне известных словарей, но в проприетарном диапазоне?
        from rtk_cors_client.config.constants import PROPRIETARY_RANGE
        lo, hi = PROPRIETARY_RANGE
        pid = hi - 1
        payload = (pid.to_bytes(2, "big") + b"\x00" * 7)
        # Первые 12 бит payload = msg_id
        p = bytearray(9)
        p[0] = (pid >> 4) & 0xFF
        p[1] = ((pid & 0x0F) << 4) & 0xFF
        frame = build_rtcm_frame(bytes(p))
        with tempfile.TemporaryDirectory() as td:
            mgr, sock = make_manager([HEADER_V1, frame], td,
                                     log_unknown_messages=True)
            mgr.run()
            self.assertEqual(len(mgr.callbacks.unknown), 1)
            self.assertEqual(mgr.callbacks.unknown[0][0], pid)
            self.assertEqual(mgr.stats["unknown_messages"], 1)


class TestCoordinatorReport(unittest.TestCase):
    def test_final_report_structure(self):
        """Финальный отчёт содержит все секции оригинала."""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            config = dict(DEFAULT_CONFIG)
            mgr, sock = make_manager([HEADER_V1], td)
            path = mgr.coordinator.save_final_report(mgr.stats.copy())
            self.assertTrue(path.exists())
            report = json.loads(path.read_text(encoding="utf-8"))
            for section in ("report_time", "config", "stats", "base_station",
                            "antenna", "system_parameters", "coordinate_system",
                            "geoid_and_cs", "all_collected_messages",
                            "unknown_proprietary", "cs_messages_status"):
                self.assertIn(section, report)

    def test_progress_after_dispatch(self):
        """После приёма 1005 прогресс показывает has_base_coords=True."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            mgr, sock = make_manager([HEADER_V1, frame_1005()], td)
            mgr.run()
            self.assertTrue(mgr.callbacks.progress)
            last = mgr.callbacks.progress[-1]
            self.assertTrue(last["has_base_coords"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
