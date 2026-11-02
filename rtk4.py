#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK CORS Client — v3.0
+ Полная поддержка сообщений 1021-1027 (параметры СК)
+ Поддержка 1300/1302 (названия CRS)
+ Диагностика отсутствия сообщений СК
+ Расширенный финальный отчёт с параметрами СК
+ Увеличенный таймаут для ожидания редких сообщений
"""
import sys
import os
import json
import time
import base64
import socket
import re
import io
import numpy as np
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QGridLayout, QGroupBox, QLabel,
                              QLineEdit, QPushButton, QTextEdit, QTabWidget,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QFileDialog, QStatusBar, QCheckBox,
                              QDoubleSpinBox, QSpinBox, QComboBox, QFrame,
                              QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor
from pyrtcm import RTCMReader, RTCMMessage


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

DEFAULT_CONFIG = {
    "ntrip_server": "rtk.example.com",
    "ntrip_port": 2101,
    "mountpoint": "VRS_1",
    "username": "user",
    "password": "pass",
    "base_lat": 55.7558,
    "base_lon": 37.6173,
    "base_alt": 150.0,
    "gga_interval": 2.0,
    "noise_std": 0.00001,
    "save_raw_rtcm": True,
    "save_params_json": True,
    "log_unknown_messages": True,
    "auto_stop_on_complete": False,
    "auto_stop_timeout": 300,  # ⭐ УВЕЛИЧЕНО: 5 минут для ожидания редких сообщений
    "cs_messages_timeout": 120,  # ⭐ НОВОЕ: через сколько сек предупреждать об отсутствии СК
}

CONFIG_FILE = "config.json"
LOGS_DIR = Path("logs")
DATA_DIR = Path("data")

# ============================================================================
# ⭐ НОВОЕ: СООБЩЕНИЯ СИСТЕМЫ КООРДИНАТ (1021-1027, 1300, 1302)
# ============================================================================

COORDINATE_SYSTEM_MESSAGES = {
    1021: {
        "name": "Helmert / Molodensky (упрощенное)",
        "description": "7 параметров преобразования Гельмерта + параметры эллипсоидов",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF403": "Transformation Method (0=Helmert, 1=Molodensky)",
            "DF392": "Sigma translation X (mm)",
            "DF393": "Sigma translation Y (mm)",
            "DF394": "Sigma translation Z (mm)",
            "DF388": "Translation X (mm)",
            "DF389": "Translation Y (mm)",
            "DF405": "Translation Z (mm)",
            "DF395": "Sigma rotation X (0.0001 arcsec)",
            "DF396": "Sigma rotation Y (0.0001 arcsec)",
            "DF397": "Sigma rotation Z (0.0001 arcsec)",
            "DF398": "Rotation X (0.0001 arcsec)",
            "DF399": "Rotation Y (0.0001 arcsec)",
            "DF406": "Rotation Z (0.0001 arcsec)",
            "DF400": "Sigma scale (1e-8)",
            "DF401": "Scale (1e-8)",
            "DF407": "Source ellipsoid (DA, DF)",
            "DF402": "Target ellipsoid (DA, DF)",
            "DF404": "Horizontal shift residuals",
            "DF408": "Vertical shift residuals",
            "DF409": "Iteration limit",
            "DF410": "Number of residuals",
        }
    },
    1022: {
        "name": "Molodensky-Badekas",
        "description": "10 параметров преобразования + координаты центра вращения",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF403": "Transformation Method",
            "DF392": "Sigma translation X",
            "DF393": "Sigma translation Y",
            "DF394": "Sigma translation Z",
            "DF388": "Translation X",
            "DF389": "Translation Y",
            "DF405": "Translation Z",
            "DF395": "Sigma rotation X",
            "DF396": "Sigma rotation Y",
            "DF397": "Sigma rotation Z",
            "DF398": "Rotation X",
            "DF399": "Rotation Y",
            "DF406": "Rotation Z",
            "DF400": "Sigma scale",
            "DF401": "Scale",
            "DF407": "Source ellipsoid",
            "DF402": "Target ellipsoid",
            "DF411": "X rotation point (m)",
            "DF412": "Y rotation point (m)",
            "DF413": "Z rotation point (m)",
            "DF404": "Horizontal shift residuals",
            "DF408": "Vertical shift residuals",
            "DF409": "Iteration limit",
            "DF410": "Number of residuals",
        }
    },
    1023: {
        "name": "Grid residuals (эллипсоидальная ИГД)",
        "description": "Сетка поправок (рестивов) для высот и плановых координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF414": "Number of grid points X",
            "DF415": "Number of grid points Y",
            "DF416": "Grid spacing X (arcsec)",
            "DF417": "Grid spacing Y (arcsec)",
            "DF418": "Grid origin latitude (arcsec)",
            "DF419": "Grid origin longitude (arcsec)",
            "DF420": "Grid name",
            "DF421": "Projection type",
            "DF422": "Residuals (horizontal)",
            "DF423": "Residuals (vertical)",
        }
    },
    1024: {
        "name": "Grid residuals (плоская сетка)",
        "description": "Детальная сеточная модель локальных искажений",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF414": "Number of grid points X",
            "DF415": "Number of grid points Y",
            "DF416": "Grid spacing X (m)",
            "DF417": "Grid spacing Y (m)",
            "DF418": "Grid origin X (m)",
            "DF419": "Grid origin Y (m)",
            "DF420": "Grid name",
            "DF421": "Projection type",
            "DF422": "Residuals (horizontal)",
            "DF423": "Residuals (vertical)",
        }
    },
    1025: {
        "name": "Projection parameters (общие)",
        "description": "Параметры проекции (кроме Ламберта и Меркатора)",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF421": "Projection type",
            "DF420": "Projection name",
            "DF427": "Projection parameters",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
        }
    },
    1026: {
        "name": "Lambert Conic Conformal (2SP)",
        "description": "Равноугольная коническая проекция Ламберта с двумя стандартными параллелями",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF420": "Projection name",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
            "DF428": "Projection center latitude",
            "DF429": "Projection center longitude",
            "DF430": "Standard parallel 1 latitude",
            "DF431": "Standard parallel 2 latitude",
            "DF432": "False easting",
            "DF433": "False northing",
        }
    },
    1027: {
        "name": "Oblique Mercator",
        "description": "Косоугольная проекция Меркатора",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF391": "Target-System ID",
            "DF420": "Projection name",
            "DF424": "Geoid model",
            "DF425": "Geoid separator",
            "DF426": "Geoid undulation",
            "DF434": "Projection center latitude",
            "DF435": "Projection center longitude",
            "DF436": "Azimuth of initial line",
            "DF437": "Angle from rectified to skewed grid",
            "DF438": "Scale factor on initial line",
            "DF439": "False easting",
            "DF440": "False northing",
        }
    },
    1300: {
        "name": "CRS Name (source)",
        "description": "Название исходной системы координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF390": "Source-System ID",
            "DF522": "Source CRS name",
        }
    },
    1302: {
        "name": "CRS Name (target)",
        "description": "Название целевой системы координат",
        "fields": {
            "DF386": "Message Number",
            "DF387": "Reference-Station ID",
            "DF391": "Target-System ID",
            "DF523": "Target CRS name",
        }
    },
}

# Все целевые сообщения
TARGET_MESSAGES = {
    1005: "Координаты базы (ECEF)",
    1006: "Координаты базы + высота",
    1007: "Описание антенны",
    1008: "Описание антенны + серийный номер",
    1013: "Системные параметры",
    1033: "Приёмник и антенна",
    1230: "GLONASS Code-Phase Biases",
    # ⭐ НОВОЕ: Сообщения СК
    1021: "Helmert / Molodensky",
    1022: "Molodensky-Badekas",
    1023: "Grid residuals (эллипсоид)",
    1024: "Grid residuals (плоская сетка)",
    1025: "Projection parameters (общие)",
    1026: "Lambert Conic Conformal",
    1027: "Oblique Mercator",
    1300: "CRS Name (source)",
    1302: "CRS Name (target)",
}

PROPRIETARY_TARGETS = {
    4076: "Septentrio/Trimble (СК/геоид?)",
    4077: "Tersus/PointOne",
    4089: "Navicom",
    4101: "Navicom",
    4102: "Navicom",
}

KNOWN_RTCM_MESSAGES = {
    1005: "Static RTK Reference Station ARP (ECEF)",
    1006: "Static RTK Reference Station ARP with Height",
    1007: "Antenna Descriptor",
    1008: "Antenna Descriptor & Serial Number",
    1013: "System Parameters",
    1019: "GPS Ephemerides",
    1020: "GLONASS Ephemerides",
    1033: "Receiver and Antenna Description",
    1042: "BeiDou Ephemerides",
    1044: "QZSS Ephemerides",
    1045: "Galileo F/NAV Ephemerides",
    1046: "Galileo I/NAV Ephemerides",
    1074: "GPS MSM4", 1075: "GPS MSM5", 1077: "GPS MSM7",
    1084: "GLONASS MSM4", 1085: "GLONASS MSM5", 1087: "GLONASS MSM7",
    1094: "Galileo MSM4", 1095: "Galileo MSM5", 1097: "Galileo MSM7",
    1114: "QZSS MSM4", 1117: "QZSS MSM7",
    1124: "BeiDou MSM4", 1127: "BeiDou MSM7",
    1230: "GLONASS Code-Phase Biases",
    # ⭐ НОВОЕ: Сообщения СК
    1021: "Helmert / Molodensky (CRS transform)",
    1022: "Molodensky-Badekas (CRS transform)",
    1023: "Grid residuals (ellipsoidal)",
    1024: "Grid residuals (planar)",
    1025: "Projection parameters (general)",
    1026: "Lambert Conic Conformal (2SP)",
    1027: "Oblique Mercator",
    1300: "CRS Name (source system)",
    1302: "CRS Name (target system)",
    # Проприетарные
    4072: "Mitsubishi Electric (Proprietary)",
    4076: "Septentrio/Trimble (Proprietary)",
    4077: "Tersus/PointOne (Proprietary)",
    4089: "Navipedia/Navicom (Proprietary)",
    4094: "China (Proprietary)", 4095: "China (Proprietary)",
    4101: "Navicom (Proprietary)", 4102: "Navicom (Proprietary)",
}

PROPRIETARY_RANGE = range(4001, 4096)


# ============================================================================
# CRC24Q
# ============================================================================

class CRC24Q:
    CRC24Q_INIT = 0x000000
    CRC24Q_POLY = 0x1864CFB
    _table = None
    
    @classmethod
    def _init_table(cls):
        if cls._table is not None:
            return
        cls._table = []
        for i in range(256):
            crc = i << 16
            for _ in range(8):
                crc <<= 1
                if crc & 0x1000000:
                    crc ^= cls.CRC24Q_POLY
            cls._table.append(crc & 0xFFFFFF)
    
    @classmethod
    def calculate(cls, data: bytes) -> int:
        cls._init_table()
        crc = cls.CRC24Q_INIT
        for byte in data:
            crc = ((crc << 8) & 0xFFFFFF) ^ cls._table[(crc >> 16) ^ byte]
        return crc


# ============================================================================
# МЕНЕДЖЕР КОНФИГУРАЦИИ
# ============================================================================

class ConfigManager:
    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = Path(config_path)
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                return True
            except Exception as e:
                print(f"Ошибка загрузки конфига: {e}")
                return False
        return False

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")
            return False

    def update(self, data: dict):
        self.config.update(data)

    def get(self, key, default=None):
        return self.config.get(key, default)


# ============================================================================
# ПАРСЕР SOURCETABLE
# ============================================================================

class SourcetableParser:
    @staticmethod
    def parse(raw_text: str) -> list:
        mountpoints = []
        for line in raw_text.splitlines():
            line = line.strip()
            if line.startswith("STR;"):
                parts = line.split(";")
                if len(parts) >= 10:
                    try:
                        mp = {
                            "mountpoint": parts[1],
                            "identifier": parts[2] if len(parts) > 2 else "",
                            "format": parts[3] if len(parts) > 3 else "",
                            "format_details": parts[4] if len(parts) > 4 else "",
                            "carrier": parts[5] if len(parts) > 5 else "",
                            "nav_system": parts[6] if len(parts) > 6 else "",
                            "network": parts[7] if len(parts) > 7 else "",
                            "country": parts[8] if len(parts) > 8 else "",
                            "latitude": float(parts[9]) if len(parts) > 9 and parts[9] else 0.0,
                            "longitude": float(parts[10]) if len(parts) > 10 and parts[10] else 0.0,
                            "nmea": parts[11] if len(parts) > 11 else "",
                            "solution": parts[12] if len(parts) > 12 else "",
                            "generator": parts[13] if len(parts) > 13 else "",
                            "compression": parts[14] if len(parts) > 14 else "",
                            "authentication": parts[15] if len(parts) > 15 else "",
                            "fee": parts[16] if len(parts) > 16 else "",
                            "bitrate": parts[17] if len(parts) > 17 else "",
                        }
                        mountpoints.append(mp)
                    except (ValueError, IndexError) as e:
                        print(f"Ошибка парсинга строки STR: {e}")
        return mountpoints


# ============================================================================
# СИГНАЛЫ
# ============================================================================

class NTRIPSignals(QObject):
    log_message = pyqtSignal(str, str)
    rtcm_message = pyqtSignal(int, str, dict)
    unknown_message = pyqtSignal(int, bytes)
    status_changed = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    sourcetable_received = pyqtSignal(list)
    last_message_updated = pyqtSignal(dict)
    collection_progress = pyqtSignal(dict)
    collection_complete = pyqtSignal(dict)
    cs_message_received = pyqtSignal(int, dict)  # ⭐ НОВОЕ: получено сообщение СК


# ============================================================================
# ПОТОК SOURCETABLE
# ============================================================================

class SourcetableWorker(QThread):
    def __init__(self, config: dict, signals: NTRIPSignals):
        super().__init__()
        self.config = config
        self.signals = signals
    
    def run(self):
        server = self.config["ntrip_server"]
        port = self.config["ntrip_port"]
        username = self.config["username"]
        password = self.config["password"]
        
        self.signals.log_message.emit(f"🔍 Запрос SOURCETABLE с {server}:{port}...", "info")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((server, port))
            
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            
            request = (
                f"GET / HTTP/1.1\r\n"
                f"User-Agent: NTRIP Trimble Access/23.10\r\n"
                f"Authorization: Basic {credentials}\r\n"
                f"Ntrip-Version: Ntrip/2.0\r\n"
                f"Connection: close\r\n\r\n"
            )
            sock.send(request.encode())
            
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if len(response) > 1_000_000:
                    break
            
            sock.close()
            text = response.decode('utf-8', errors='ignore')
            
            if "401" in text.split("\r\n")[0]:
                self.signals.log_message.emit("❌ Ошибка авторизации при запросе SOURCETABLE", "error")
                return
            
            if "SOURCETABLE" not in text and "STR;" not in text:
                self.signals.log_message.emit(f"❌ Сервер не вернул SOURCETABLE. Ответ: {text[:200]}", "error")
                return
            
            mountpoints = SourcetableParser.parse(text)
            
            if mountpoints:
                self.signals.log_message.emit(f"✅ Получено {len(mountpoints)} маунтпоинтов", "success")
                self.signals.sourcetable_received.emit(mountpoints)
            else:
                self.signals.log_message.emit("⚠️ SOURCETABLE получен, но маунтпоинты не найдены", "warning")
                
        except Exception as e:
            self.signals.log_message.emit(f"❌ Ошибка получения SOURCETABLE: {e}", "error")


# ============================================================================
# ПОТОК NTRIP КЛИЕНТА
# ============================================================================

class NTRIPWorker(QThread):
    def __init__(self, config: dict, signals: NTRIPSignals):
        super().__init__()
        self.config = config
        self.signals = signals
        self.running = False
        self.socket = None
        self.buffer = bytearray()
        
        self.chunked_mode = False
        self.chunk_buffer = bytearray()
        
        self.stats = {
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
        
        self.collected_params = {}
        self.unknown_proprietary = {}
        
        # ⭐ НОВОЕ: Отслеживание времени первого прихода сообщений СК
        self.cs_first_seen = {}  # {msg_id: timestamp}
        self.cs_warning_shown = False
        
        self._last_bytes = 0
        self._last_time = time.time()
        
        self.f_raw = None
        self.f_params = None
        
        LOGS_DIR.mkdir(exist_ok=True)
        DATA_DIR.mkdir(exist_ok=True)
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
    
    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.signals.log_message.emit(f"[{timestamp}] {message}", level)
    
    def connect_ntrip(self):
        server = self.config["ntrip_server"]
        port = self.config["ntrip_port"]
        mountpoint = self.config["mountpoint"]
        username = self.config["username"]
        password = self.config["password"]
        
        self.signals.status_changed.emit("Подключение...")
        self.log(f"Подключение к {server}:{port}/{mountpoint}")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((server, port))
            self.socket.settimeout(1.0)
            
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            
            request = (
                f"GET /{mountpoint} HTTP/1.1\r\n"
                f"User-Agent: NTRIP Trimble Access/23.10\r\n"
                f"Authorization: Basic {credentials}\r\n"
                f"Ntrip-Version: Ntrip/2.0\r\n"
                f"Connection: keep-alive\r\n\r\n"
            )
            self.socket.send(request.encode())
            self.stats["bytes_sent"] += len(request)
            
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = self.socket.recv(1024)
                if not chunk:
                    raise ConnectionError("Сервер закрыл соединение")
                response += chunk
            
            header_end = response.find(b"\r\n\r\n")
            header = response[:header_end].decode('utf-8', errors='ignore')
            remaining_data = response[header_end + 4:]
            
            if "Transfer-Encoding: chunked" in header.lower():
                self.chunked_mode = True
                self.log("📦 Режим NTRIP v2 chunked encoding", "info")
            
            if "200 OK" in header or "ICY 200 OK" in header:
                self.log("✅ Аккаунт валиден, подключение установлено", "success")
                self.signals.status_changed.emit("Подключено")
                self.stats["connected_since"] = datetime.now().isoformat()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if self.config.get("save_raw_rtcm"):
                    self.f_raw = open(DATA_DIR / f"stream_{timestamp}.rtcm", "wb")
                    self.log(f"📁 Сырой поток: stream_{timestamp}.rtcm")
                
                if self.config.get("save_params_json"):
                    self.f_params = open(DATA_DIR / f"params_{timestamp}.json", "w", encoding="utf-8")
                
                gga = self.generate_gga()
                self.socket.send(gga.encode())
                self.stats["bytes_sent"] += len(gga)
                self.stats["gga_sent"] += 1

                self.log(f"📤 Отправлен первый GGA {gga}", "info")
                
                # ⭐ НОВОЕ: Информационное сообщение о СК
                self.log("ℹ️ Ожидание сообщений системы координат (1021-1027, 1300, 1302)...", "info")
                self.log(f"ℹ️ Таймаут ожидания: {self.config.get('cs_messages_timeout', 120)}с", "info")
                
                if remaining_data:
                    if self.chunked_mode:
                        self.chunk_buffer.extend(remaining_data)
                    else:
                        self.buffer.extend(remaining_data)
                
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
            self.log(f"❌ Ошибка подключения: {e}", "error")
            self.signals.status_changed.emit("Ошибка подключения")
            return False
    
    def generate_gga(self):
        base_lat = self.config["base_lat"]
        base_lon = self.config["base_lon"]
        base_alt = self.config["base_alt"]
        noise_std = self.config.get("noise_std", 0.00001)
        
        curr_lat = base_lat + np.random.normal(0, noise_std)
        curr_lon = base_lon + np.random.normal(0, noise_std)
        
        lat_deg = int(abs(curr_lat))
        lat_min = (abs(curr_lat) - lat_deg) * 60
        lon_deg = int(abs(curr_lon))
        lon_min = (abs(curr_lon) - lon_deg) * 60
        
        lat_dir = 'N' if curr_lat >= 0 else 'S'
        lon_dir = 'E' if curr_lon >= 0 else 'W'
        
        timestamp = time.strftime('%H%M%S.00', time.gmtime())
        
        body = (
            f"GPGGA,{timestamp},"
            f"{lat_deg:02d}{lat_min:07.4f},{lat_dir},"
            f"{lon_deg:03d}{lon_min:07.4f},{lon_dir},"
            f"4,12,0.8,{base_alt:.1f},M,0.0,M,,"
        )
        
        checksum = 0
        for char in body:
            checksum ^= ord(char)
        
        return f"${body}*{checksum:02X}\r\n"
    
    def process_chunked_data(self, data: bytes):
        self.chunk_buffer.extend(data)
        extracted = bytearray()
        
        while True:
            crlf_pos = self.chunk_buffer.find(b"\r\n")
            if crlf_pos == -1:
                break
            
            size_str = self.chunk_buffer[:crlf_pos].decode('ascii', errors='ignore').strip()
            
            if ';' in size_str:
                size_str = size_str.split(';')[0].strip()
            
            try:
                chunk_size = int(size_str, 16)
            except ValueError:
                self.chunk_buffer = self.chunk_buffer[crlf_pos + 2:]
                continue
            
            if chunk_size == 0:
                self.log("📦 Сервер отправил терминальный chunk (0)", "info")
                break
            
            data_start = crlf_pos + 2
            data_end = data_start + chunk_size
            total_needed = data_end + 2
            
            if len(self.chunk_buffer) < total_needed:
                break
            
            extracted.extend(self.chunk_buffer[data_start:data_end])
            self.chunk_buffer = self.chunk_buffer[total_needed:]
        
        return bytes(extracted)
    
    def parse_rtcm_buffer(self):
        iterations = 0
        max_iterations = 10000
        
        while len(self.buffer) >= 3 and iterations < max_iterations:
            iterations += 1
            
            if self.buffer[0] != 0xD3:
                self.buffer.pop(0)
                continue
            
            if len(self.buffer) < 3:
                break
            
            length = ((self.buffer[1] & 0x03) << 8) | self.buffer[2]
            
            if length > 1023:
                self.buffer.pop(0)
                continue
            
            frame_len = 3 + length + 3
            if len(self.buffer) < frame_len:
                break
            
            frame = bytes(self.buffer[:frame_len])
            
            payload_with_header = frame[:-3]
            received_crc = (frame[-3] << 16) | (frame[-2] << 8) | frame[-1]
            computed_crc = CRC24Q.calculate(payload_with_header)
            
            if received_crc != computed_crc:
                self.stats["messages_crc_failed"] += 1
                self.buffer.pop(0)
                continue
            
            if len(frame) >= 5:
                msg_id = (frame[3] << 4) | (frame[4] >> 4)
                
                try:
                    parsed = RTCMReader.parse(frame)
                    msg_name = KNOWN_RTCM_MESSAGES.get(msg_id, f"Unknown_{msg_id}")
                    
                    params = {}
                    if hasattr(parsed, '__dict__'):
                        for key, value in parsed.__dict__.items():
                            if not key.startswith('_'):
                                params[key] = self._serialize_value(value)
                    
                    is_proprietary = msg_id in PROPRIETARY_RANGE
                    is_known = msg_id in KNOWN_RTCM_MESSAGES
                    is_cs_message = msg_id in COORDINATE_SYSTEM_MESSAGES
                    
                    # ⭐ НОВОЕ: Обработка сообщений СК
                    if is_cs_message:
                        self._handle_cs_message(msg_id, params, frame)
                    
                    self.collected_params[msg_id] = {
                        "name": msg_name,
                        "params": params,
                        "count": self.collected_params.get(msg_id, {}).get("count", 0) + 1,
                        "last_time": datetime.now().isoformat(),
                    }
                    
                    if is_proprietary and not is_known:
                        self.stats["unknown_messages"] += 1
                        if msg_id not in self.unknown_proprietary:
                            self.unknown_proprietary[msg_id] = {"count": 0, "hex_samples": []}
                        self.unknown_proprietary[msg_id]["count"] += 1
                        if len(self.unknown_proprietary[msg_id]["hex_samples"]) < 5:
                            self.unknown_proprietary[msg_id]["hex_samples"].append(frame.hex())
                        
                        self.signals.unknown_message.emit(msg_id, frame)
                        if self.config.get("log_unknown_messages"):
                            self.log(f"⚠️ Неизвестное проприетарное ID={msg_id}, {length} байт", "warning")
                    else:
                        self.signals.rtcm_message.emit(msg_id, msg_name, params)
                        
                        if msg_id in [1005, 1006, 1033]:
                            self.log(f"📡 Параметры базы: {msg_name}", "info")
                        elif is_cs_message:
                            cs_info = COORDINATE_SYSTEM_MESSAGES[msg_id]
                            self.log(f"🌍 СК: {cs_info['name']} — {cs_info['description']}", "success")
                        elif msg_id in PROPRIETARY_TARGETS:
                            self.log(f"🌍 Проприетарное (СК/геоид?): {msg_name}", "info")
                    
                    self.stats["messages_parsed"] += 1
                    self.stats["messages_valid"] += 1
                    self.stats["last_message_id"] = msg_id
                    self.stats["last_message_name"] = msg_name
                    self.stats["last_message_time"] = datetime.now().strftime("%H:%M:%S")
                    
                    self.signals.last_message_updated.emit({
                        "id": msg_id,
                        "name": msg_name,
                        "time": self.stats["last_message_time"],
                        "length": length
                    })
                    
                    self._update_collection_progress()
                    
                except Exception as e:
                    if self.config.get("log_unknown_messages"):
                        self.log(f"⚠️ Ошибка парсинга ID={msg_id}: {e}", "warning")
            
            del self.buffer[:frame_len]
    
    def _handle_cs_message(self, msg_id: int, params: dict, raw_frame: bytes):
        """Обработка сообщений системы координат"""
        now = time.time()
        
        # Запоминаем время первого прихода
        if msg_id not in self.cs_first_seen:
            self.cs_first_seen[msg_id] = now
        
        # Сохраняем сырые данные (для fallback, если pyrtcm не разобрал)
        self.collected_params.setdefault(msg_id, {})
        self.collected_params[msg_id]["raw_hex"] = raw_frame.hex()
        
        # Сигнал в GUI
        self.signals.cs_message_received.emit(msg_id, params)
    
    def _serialize_value(self, value):
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return str(value)
    
    def _update_collection_progress(self):
        collected_ids = set(self.collected_params.keys())
        
        target_ids = set(TARGET_MESSAGES.keys())
        proprietary_collected = [mid for mid in collected_ids if mid in PROPRIETARY_TARGETS]
        
        has_base_coords = bool(collected_ids & {1005, 1006})
        has_antenna = bool(collected_ids & {1007, 1008, 1033})
        has_proprietary = len(proprietary_collected) > 0
        
        # ⭐ НОВОЕ: Отслеживание сообщений СК
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = sorted(list(collected_ids & cs_ids))
        has_cs = len(cs_collected) > 0
        
        progress = {
            "has_base_coords": has_base_coords,
            "has_antenna": has_antenna,
            "has_proprietary": has_proprietary,
            "has_cs": has_cs,  # ⭐ НОВОЕ
            "cs_collected": cs_collected,  # ⭐ НОВОЕ
            "collected_ids": sorted(list(collected_ids)),
            "target_ids": sorted(list(target_ids)),
            "proprietary_collected": proprietary_collected,
            "total_collected": len(collected_ids),
            "is_complete": has_base_coords and has_antenna,
        }
        
        self.signals.collection_progress.emit(progress)
        
        if self.config.get("auto_stop_on_complete") and progress["is_complete"]:
            self.log("✅ Все обязательные данные собраны. Автоостановка...", "success")
            self._save_final_report()
            self.signals.collection_complete.emit(progress)
            self.stop()
    
    def _check_cs_timeout(self):
        """⭐ НОВОЕ: Проверка таймаута ожидания сообщений СК"""
        if self.cs_warning_shown:
            return
        
        cs_timeout = self.config.get("cs_messages_timeout", 120)
        connected_since = self.stats.get("connected_since")
        if not connected_since:
            return
        
        try:
            start = datetime.fromisoformat(connected_since)
            elapsed = (datetime.now() - start).total_seconds()
        except:
            return
        
        if elapsed > cs_timeout:
            cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
            collected_ids = set(self.collected_params.keys())
            missing_cs = cs_ids - collected_ids
            
            if missing_cs:
                self.cs_warning_shown = True
                missing_names = [f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})" 
                                for mid in sorted(missing_cs)]
                
                self.log(f"⚠️ ВНИМАНИЕ: Сообщения СК не получены за {cs_timeout}с!", "warning")
                self.log(f"⚠️ Отсутствуют: {', '.join(missing_names)}", "warning")
                self.log("💡 Возможные причины:", "warning")
                self.log("   1. Провайдер шлёт их редко (раз в 5-10 минут)", "warning")
                self.log("   2. Координаты ровера вне зоны действия МСК", "warning")
                self.log("   3. Провайдер не передаёт параметры СК через RTCM", "warning")
                self.log("   4. Параметры СК зашиты в проприетарных сообщениях", "warning")
                self.log("💡 Рекомендация: увеличить таймаут или проверить координаты", "warning")
    
    def _save_final_report(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = DATA_DIR / f"final_report_{timestamp}.json"
        
        report = {
            "report_time": datetime.now().isoformat(),
            "config": self.config,
            "stats": self.stats,
            "base_station": self._extract_base_station(),
            "antenna": self._extract_antenna(),
            "system_parameters": self._extract_system_parameters(),
            "coordinate_system": self._extract_coordinate_system(),  # ⭐ НОВОЕ
            "geoid_and_cs": self._extract_geoid_and_cs(),
            "all_collected_messages": {
                str(mid): data for mid, data in self.collected_params.items()
            },
            "unknown_proprietary": {
                str(mid): data for mid, data in self.unknown_proprietary.items()
            },
            "cs_messages_status": {  # ⭐ НОВОЕ
                str(mid): {
                    "name": COORDINATE_SYSTEM_MESSAGES[mid]["name"],
                    "received": mid in self.collected_params,
                    "first_seen": datetime.fromtimestamp(self.cs_first_seen[mid]).isoformat() 
                                  if mid in self.cs_first_seen else None,
                }
                for mid in COORDINATE_SYSTEM_MESSAGES.keys()
            },
        }
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self.log(f"💾 Финальный отчёт сохранён: {report_path}", "success")
        except Exception as e:
            self.log(f"❌ Ошибка сохранения отчёта: {e}", "error")
    
    def _extract_base_station(self):
        result = {}
        
        if 1005 in self.collected_params:
            p = self.collected_params[1005]["params"]
            result["msg_1005"] = {
                "reference_station_id": p.get("DF003"),
                "ecef_x_m": p.get("DF025"),
                "ecef_y_m": p.get("DF026"),
                "ecef_z_m": p.get("DF027"),
            }
            try:
                x = float(p.get("DF025", 0)) / 10000.0
                y = float(p.get("DF026", 0)) / 10000.0
                z = float(p.get("DF027", 0)) / 10000.0
                lat, lon, alt = self._ecef_to_wgs84(x, y, z)
                result["wgs84"] = {"lat": lat, "lon": lon, "alt": alt}
            except Exception as e:
                result["wgs84_error"] = str(e)
        
        if 1006 in self.collected_params:
            p = self.collected_params[1006]["params"]
            result["msg_1006"] = {
                "reference_station_id": p.get("DF003"),
                "ecef_x_m": p.get("DF025"),
                "ecef_y_m": p.get("DF026"),
                "ecef_z_m": p.get("DF027"),
                "antenna_height_m": p.get("DF141"),
            }
            try:
                x = float(p.get("DF025", 0)) / 10000.0
                y = float(p.get("DF026", 0)) / 10000.0
                z = float(p.get("DF027", 0)) / 10000.0
                lat, lon, alt = self._ecef_to_wgs84(x, y, z)
                result["wgs84"] = {"lat": lat, "lon": lon, "alt": alt}
            except Exception as e:
                result["wgs84_error"] = str(e)
        
        return result
    
    def _ecef_to_wgs84(self, x, y, z):
        a = 6378137.0
        f = 1 / 298.257223563
        b = a * (1 - f)
        e2 = (a**2 - b**2) / a**2
        ep2 = (a**2 - b**2) / b**2
        
        p = np.sqrt(x**2 + y**2)
        theta = np.arctan2(z * a, p * b)
        
        lon = np.arctan2(y, x)
        lat = np.arctan2(
            z + ep2 * b * np.sin(theta)**3,
            p - e2 * a * np.cos(theta)**3
        )
        N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
        alt = p / np.cos(lat) - N
        
        return np.degrees(lat), np.degrees(lon), alt
    
    def _extract_antenna(self):
        result = {}
        
        if 1007 in self.collected_params:
            p = self.collected_params[1007]["params"]
            result["msg_1007"] = {
                "antenna_descriptor": p.get("DF143"),
                "antenna_setup_id": p.get("DF144"),
            }
        
        if 1008 in self.collected_params:
            p = self.collected_params[1008]["params"]
            result["msg_1008"] = {
                "antenna_descriptor": p.get("DF143"),
                "antenna_serial": p.get("DF004"),
                "antenna_setup_id": p.get("DF144"),
            }
        
        if 1033 in self.collected_params:
            p = self.collected_params[1033]["params"]
            result["msg_1033"] = {
                "receiver_descriptor": p.get("DF029"),
                "receiver_serial": p.get("DF030"),
                "receiver_fw": p.get("DF232"),
                "antenna_descriptor": p.get("DF143"),
                "antenna_serial": p.get("DF004"),
                "antenna_setup_id": p.get("DF144"),
            }
        
        return result
    
    def _extract_system_parameters(self):
        result = {}
        if 1013 in self.collected_params:
            result["msg_1013"] = self.collected_params[1013]["params"]
        if 1230 in self.collected_params:
            result["msg_1230"] = self.collected_params[1230]["params"]
        return result
    
    # ⭐ НОВОЕ: Извлечение параметров системы координат
    def _extract_coordinate_system(self):
        """Извлечение параметров СК из сообщений 1021-1027, 1300, 1302"""
        result = {
            "received": [],
            "missing": [],
            "transforms": {},
            "grids": {},
            "projections": {},
            "crs_names": {},
        }
        
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        collected_ids = set(self.collected_params.keys())
        
        # Преобразования (1021, 1022)
        for mid in [1021, 1022]:
            if mid in self.collected_params:
                p = self.collected_params[mid]["params"]
                result["received"].append(mid)
                result["transforms"][f"msg_{mid}"] = {
                    "name": COORDINATE_SYSTEM_MESSAGES[mid]["name"],
                    "source_system_id": p.get("DF390"),
                    "target_system_id": p.get("DF391"),
                    "translation_x_mm": p.get("DF388"),
                    "translation_y_mm": p.get("DF389"),
                    "translation_z_mm": p.get("DF405"),
                    "rotation_x_arcsec": p.get("DF398"),
                    "rotation_y_arcsec": p.get("DF399"),
                    "rotation_z_arcsec": p.get("DF406"),
                    "scale_ppb": p.get("DF401"),
                    "source_ellipsoid": p.get("DF407"),
                    "target_ellipsoid": p.get("DF402"),
                    "all_params": p,
                }
            else:
                result["missing"].append(mid)
        
        # Сетки поправок (1023, 1024)
        for mid in [1023, 1024]:
            if mid in self.collected_params:
                p = self.collected_params[mid]["params"]
                result["received"].append(mid)
                result["grids"][f"msg_{mid}"] = {
                    "name": COORDINATE_SYSTEM_MESSAGES[mid]["name"],
                    "source_system_id": p.get("DF390"),
                    "target_system_id": p.get("DF391"),
                    "grid_points_x": p.get("DF414"),
                    "grid_points_y": p.get("DF415"),
                    "grid_spacing_x": p.get("DF416"),
                    "grid_spacing_y": p.get("DF417"),
                    "grid_origin_x": p.get("DF418"),
                    "grid_origin_y": p.get("DF419"),
                    "grid_name": p.get("DF420"),
                    "all_params": p,
                }
            else:
                result["missing"].append(mid)
        
        # Проекции (1025, 1026, 1027)
        for mid in [1025, 1026, 1027]:
            if mid in self.collected_params:
                p = self.collected_params[mid]["params"]
                result["received"].append(mid)
                proj_data = {
                    "name": COORDINATE_SYSTEM_MESSAGES[mid]["name"],
                    "source_system_id": p.get("DF390"),
                    "target_system_id": p.get("DF391"),
                    "projection_name": p.get("DF420"),
                    "geoid_model": p.get("DF424"),
                    "all_params": p,
                }
                
                # Специфичные параметры для каждой проекции
                if mid == 1026:  # Lambert
                    proj_data.update({
                        "center_lat": p.get("DF428"),
                        "center_lon": p.get("DF429"),
                        "std_parallel_1": p.get("DF430"),
                        "std_parallel_2": p.get("DF431"),
                        "false_easting": p.get("DF432"),
                        "false_northing": p.get("DF433"),
                    })
                elif mid == 1027:  # Oblique Mercator
                    proj_data.update({
                        "center_lat": p.get("DF434"),
                        "center_lon": p.get("DF435"),
                        "azimuth": p.get("DF436"),
                        "rectified_to_skewed": p.get("DF437"),
                        "scale_factor": p.get("DF438"),
                        "false_easting": p.get("DF439"),
                        "false_northing": p.get("DF440"),
                    })
                
                result["projections"][f"msg_{mid}"] = proj_data
            else:
                result["missing"].append(mid)
        
        # Названия CRS (1300, 1302)
        for mid in [1300, 1302]:
            if mid in self.collected_params:
                p = self.collected_params[mid]["params"]
                result["received"].append(mid)
                if mid == 1300:
                    result["crs_names"]["source"] = {
                        "system_id": p.get("DF390"),
                        "name": p.get("DF522"),
                    }
                elif mid == 1302:
                    result["crs_names"]["target"] = {
                        "system_id": p.get("DF391"),
                        "name": p.get("DF523"),
                    }
            else:
                result["missing"].append(mid)
        
        return result
    
    def _extract_geoid_and_cs(self):
        result = {}
        
        for msg_id in PROPRIETARY_TARGETS:
            if msg_id in self.collected_params:
                result[f"msg_{msg_id}"] = {
                    "name": PROPRIETARY_TARGETS[msg_id],
                    "params": self.collected_params[msg_id]["params"],
                    "count": self.collected_params[msg_id]["count"],
                }
        
        for msg_id, data in self.unknown_proprietary.items():
            result[f"unknown_{msg_id}"] = {
                "name": f"Unknown proprietary {msg_id}",
                "count": data["count"],
                "hex_samples": data["hex_samples"],
                "note": "Требует анализа. Возможно содержит параметры СК/геоида/коррекции",
            }
        
        return result
    
    def run(self):
        self.running = True
        
        if not self.connect_ntrip():
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
                        data = self.socket.recv(4096)
                    except socket.timeout:
                        data = None
                    
                    if data:
                        self.stats["bytes_received"] += len(data)
                        
                        if self.f_raw:
                            self.f_raw.write(data)
                            self.f_raw.flush()
                        
                        if self.chunked_mode:
                            extracted = self.process_chunked_data(data)
                            if extracted:
                                self.buffer.extend(extracted)
                                self.parse_rtcm_buffer()
                        else:
                            self.buffer.extend(data)
                            self.parse_rtcm_buffer()
                    
                    now = time.time()
                    if now - self._last_time >= 1.0:
                        elapsed = now - self._last_time
                        self.stats["bytes_per_sec"] = (
                            (self.stats["bytes_received"] - self._last_bytes) / elapsed
                        )
                        self._last_bytes = self.stats["bytes_received"]
                        self._last_time = now
                    
                    if now - last_gga_time >= gga_interval:
                        gga = self.generate_gga()
                        try:
                            self.socket.send(gga.encode())
                            self.stats["bytes_sent"] += len(gga)
                            self.stats["gga_sent"] += 1
                            last_gga_time = now
                            self.log(f"Отправка GGA: {gga}", "info")
                        except Exception as e:
                            self.log(f"❌ Ошибка отправки GGA: {e}", "error")
                            break
                    
                    # ⭐ НОВОЕ: Проверка таймаута СК (раз в 10 сек)
                    if now - last_cs_check >= 10.0:
                        self._check_cs_timeout()
                        last_cs_check = now
                    
                    self.signals.stats_updated.emit(self.stats.copy())
                    
                    if (self.config.get("auto_stop_on_complete") and 
                        now - start_time > auto_stop_timeout):
                        self.log(f"⏰ Таймаут автоостановки ({auto_stop_timeout}с). Сохраняем что есть...", "warning")
                        self._save_final_report()
                        self.signals.collection_complete.emit({})
                        break
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if "10038" in str(e) or "not a socket" in str(e).lower():
                        self.log("🔌 Сокет закрыт", "info")
                        break
                    self.log(f"❌ Ошибка в цикле: {e}", "error")
                    break
                    
        except Exception as e:
            self.log(f"❌ Критическая ошибка: {e}", "error")
        finally:
            if self.config.get("save_params_json") and self.stats["messages_parsed"] > 0:
                self._save_final_report()
            self.cleanup()
    
    def cleanup(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.f_raw:
            try:
                self.f_raw.flush()
                self.f_raw.close()
            except:
                pass
        if self.f_params:
            try:
                self.f_params.flush()
                self.f_params.close()
            except:
                pass
        self.signals.status_changed.emit("Отключено")
        self.log("Соединение закрыто, ресурсы освобождены")


# ============================================================================
# ГЛАВНОЕ ОКНО
# ============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.signals = NTRIPSignals()
        self.worker = None
        self.sourcetable_worker = None
        self.mountpoints_data = []
        
        self.init_ui()
        self.connect_signals()
        self.load_config_to_ui()
        
        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.update_uptime)
        self.uptime_timer.start(1000)
    
    def init_ui(self):
        self.setWindowTitle("RTK CORS Client — v3.0 (с поддержкой СК)")
        self.setMinimumSize(1200, 850)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.tab_connection = self.create_connection_tab()
        self.tabs.addTab(self.tab_connection, "🔌 Подключение")
        
        self.tab_collection = self.create_collection_tab()
        self.tabs.addTab(self.tab_collection, "🎯 Сбор данных")
        
        # ⭐ НОВОЕ: Вкладка параметров СК
        self.tab_cs = self.create_cs_tab()
        self.tabs.addTab(self.tab_cs, "🌍 Система координат")
        
        self.tab_log = self.create_log_tab()
        self.tabs.addTab(self.tab_log, "📋 Лог событий")
        
        self.tab_params = self.create_params_tab()
        self.tabs.addTab(self.tab_params, "📊 Параметры системы")
        
        self.tab_stats = self.create_stats_tab()
        self.tabs.addTab(self.tab_stats, "📈 Статистика")
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Статус: Отключено")
        self.status_bar.addWidget(self.status_label)
    
    def create_connection_tab(self):
        widget = QWidget()
        
        # Scroll area для длинной формы
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # NTRIP Сервер
        group_server = QGroupBox("NTRIP Сервер")
        server_layout = QGridLayout()
        
        server_layout.addWidget(QLabel("Сервер:"), 0, 0)
        self.edit_server = QLineEdit()
        server_layout.addWidget(self.edit_server, 0, 1)
        
        server_layout.addWidget(QLabel("Порт:"), 0, 2)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(2101)
        server_layout.addWidget(self.spin_port, 0, 3)
        
        server_layout.addWidget(QLabel("Маунтпоинт:"), 1, 0)
        self.combo_mountpoint = QComboBox()
        self.combo_mountpoint.setEditable(True)
        self.combo_mountpoint.setMinimumWidth(200)
        server_layout.addWidget(self.combo_mountpoint, 1, 1)
        
        self.btn_fetch_sourcetable = QPushButton("🔄 Получить список")
        self.btn_fetch_sourcetable.clicked.connect(self.fetch_sourcetable)
        server_layout.addWidget(self.btn_fetch_sourcetable, 1, 2, 1, 2)
        
        group_server.setLayout(server_layout)
        layout.addWidget(group_server)
        
        # Авторизация
        group_auth = QGroupBox("Авторизация")
        auth_layout = QGridLayout()
        
        auth_layout.addWidget(QLabel("Логин:"), 0, 0)
        self.edit_username = QLineEdit()
        auth_layout.addWidget(self.edit_username, 0, 1)
        
        auth_layout.addWidget(QLabel("Пароль:"), 0, 2)
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        auth_layout.addWidget(self.edit_password, 0, 3)
        
        group_auth.setLayout(auth_layout)
        layout.addWidget(group_auth)
        
        # Координаты ровера
        group_rover = QGroupBox("Координаты ровера (базовые)")
        rover_layout = QGridLayout()
        
        rover_layout.addWidget(QLabel("Широта (°):"), 0, 0)
        self.spin_lat = QDoubleSpinBox()
        self.spin_lat.setRange(-90, 90)
        self.spin_lat.setDecimals(6)
        rover_layout.addWidget(self.spin_lat, 0, 1)
        
        rover_layout.addWidget(QLabel("Долгота (°):"), 0, 2)
        self.spin_lon = QDoubleSpinBox()
        self.spin_lon.setRange(-180, 180)
        self.spin_lon.setDecimals(6)
        rover_layout.addWidget(self.spin_lon, 0, 3)
        
        rover_layout.addWidget(QLabel("Высота (м):"), 1, 0)
        self.spin_alt = QDoubleSpinBox()
        self.spin_alt.setRange(-1000, 10000)
        self.spin_alt.setDecimals(2)
        rover_layout.addWidget(self.spin_alt, 1, 1)
        
        rover_layout.addWidget(QLabel("Интервал GGA (с):"), 1, 2)
        self.spin_gga_interval = QDoubleSpinBox()
        self.spin_gga_interval.setRange(0.5, 10.0)
        self.spin_gga_interval.setSingleStep(0.5)
        rover_layout.addWidget(self.spin_gga_interval, 1, 3)
        
        rover_layout.addWidget(QLabel("Шум (°):"), 2, 0)
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0, 0.001)
        self.spin_noise.setDecimals(6)
        self.spin_noise.setSingleStep(0.000001)
        rover_layout.addWidget(self.spin_noise, 2, 1)
        
        # ⭐ НОВОЕ: Подсказка о зоне МСК
        hint_lbl = QLabel("💡 Для получения параметров СК (1021-1027) координаты должны быть в зоне действия МСК")
        hint_lbl.setStyleSheet("color: #2196F3; font-style: italic;")
        hint_lbl.setWordWrap(True)
        rover_layout.addWidget(hint_lbl, 3, 0, 1, 4)
        
        group_rover.setLayout(rover_layout)
        layout.addWidget(group_rover)
        
        # Опции
        group_options = QGroupBox("Опции")
        options_layout = QVBoxLayout()
        
        self.check_save_raw = QCheckBox("Сохранять сырой RTCM поток")
        self.check_save_raw.setChecked(True)
        options_layout.addWidget(self.check_save_raw)
        
        self.check_save_params = QCheckBox("Сохранять параметры в JSON")
        self.check_save_params.setChecked(True)
        options_layout.addWidget(self.check_save_params)
        
        self.check_log_unknown = QCheckBox("Логировать неизвестные сообщения")
        self.check_log_unknown.setChecked(True)
        options_layout.addWidget(self.check_log_unknown)
        
        auto_stop_layout = QHBoxLayout()
        self.check_auto_stop = QCheckBox("🎯 Автоостановка после сбора всех данных")
        auto_stop_layout.addWidget(self.check_auto_stop)
        
        auto_stop_layout.addWidget(QLabel("Таймаут (с):"))
        self.spin_auto_timeout = QSpinBox()
        self.spin_auto_timeout.setRange(30, 1800)
        self.spin_auto_timeout.setValue(300)  # ⭐ УВЕЛИЧЕНО
        self.spin_auto_timeout.setSingleStep(30)
        auto_stop_layout.addWidget(self.spin_auto_timeout)
        auto_stop_layout.addStretch()
        
        options_layout.addLayout(auto_stop_layout)
        
        # ⭐ НОВОЕ: Таймаут ожидания СК
        cs_timeout_layout = QHBoxLayout()
        cs_timeout_layout.addWidget(QLabel("⏱️ Таймаут ожидания сообщений СК (с):"))
        self.spin_cs_timeout = QSpinBox()
        self.spin_cs_timeout.setRange(30, 600)
        self.spin_cs_timeout.setValue(120)
        self.spin_cs_timeout.setSingleStep(10)
        cs_timeout_layout.addWidget(self.spin_cs_timeout)
        cs_timeout_layout.addWidget(QLabel("(через сколько предупреждать об отсутствии)"))
        cs_timeout_layout.addStretch()
        options_layout.addLayout(cs_timeout_layout)
        
        group_options.setLayout(options_layout)
        layout.addWidget(group_options)
        
        # Статистика в реальном времени
        group_live_stats = QGroupBox("📊 Статистика в реальном времени")
        live_layout = QGridLayout()
        
        live_layout.addWidget(QLabel("⏱️ Время работы:"), 0, 0)
        self.lbl_uptime = QLabel("00:00:00")
        self.lbl_uptime.setFont(QFont("Consolas", 10, QFont.Bold))
        live_layout.addWidget(self.lbl_uptime, 0, 1)
        
        live_layout.addWidget(QLabel("📥 Скорость:"), 0, 2)
        self.lbl_speed = QLabel("0 байт/с")
        self.lbl_speed.setFont(QFont("Consolas", 10, QFont.Bold))
        live_layout.addWidget(self.lbl_speed, 0, 3)
        
        live_layout.addWidget(QLabel("📥 Получено:"), 1, 0)
        self.lbl_bytes_rx = QLabel("0 байт")
        live_layout.addWidget(self.lbl_bytes_rx, 1, 1)
        
        live_layout.addWidget(QLabel("📤 Отправлено:"), 1, 2)
        self.lbl_bytes_tx = QLabel("0 байт")
        live_layout.addWidget(self.lbl_bytes_tx, 1, 3)
        
        live_layout.addWidget(QLabel("✅ Валидных:"), 2, 0)
        self.lbl_valid = QLabel("0")
        live_layout.addWidget(self.lbl_valid, 2, 1)
        
        live_layout.addWidget(QLabel("❌ CRC ошибок:"), 2, 2)
        self.lbl_crc_failed = QLabel("0")
        self.lbl_crc_failed.setStyleSheet("color: red;")
        live_layout.addWidget(self.lbl_crc_failed, 2, 3)
        
        live_layout.addWidget(QLabel("📨 Сообщений:"), 3, 0)
        self.lbl_messages = QLabel("0")
        live_layout.addWidget(self.lbl_messages, 3, 1)
        
        live_layout.addWidget(QLabel("📡 GGA отправлено:"), 3, 2)
        self.lbl_gga = QLabel("0")
        live_layout.addWidget(self.lbl_gga, 3, 3)
        
        group_live_stats.setLayout(live_layout)
        layout.addWidget(group_live_stats)
        
        # Последнее сообщение
        group_last_msg = QGroupBox("📬 Последнее принятое сообщение")
        last_msg_layout = QGridLayout()
        
        last_msg_layout.addWidget(QLabel("ID:"), 0, 0)
        self.lbl_last_id = QLabel("—")
        self.lbl_last_id.setFont(QFont("Consolas", 11, QFont.Bold))
        self.lbl_last_id.setStyleSheet("color: #2196F3;")
        last_msg_layout.addWidget(self.lbl_last_id, 0, 1)
        
        last_msg_layout.addWidget(QLabel("Название:"), 0, 2)
        self.lbl_last_name = QLabel("—")
        self.lbl_last_name.setFont(QFont("Consolas", 10))
        last_msg_layout.addWidget(self.lbl_last_name, 0, 3)
        
        last_msg_layout.addWidget(QLabel("Время:"), 1, 0)
        self.lbl_last_time = QLabel("—")
        last_msg_layout.addWidget(self.lbl_last_time, 1, 1)
        
        last_msg_layout.addWidget(QLabel("Размер:"), 1, 2)
        self.lbl_last_size = QLabel("—")
        last_msg_layout.addWidget(self.lbl_last_size, 1, 3)
        
        group_last_msg.setLayout(last_msg_layout)
        layout.addWidget(group_last_msg)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.btn_connect = QPushButton("▶️ Подключить")
        self.btn_connect.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        self.btn_connect.clicked.connect(self.toggle_connection)
        buttons_layout.addWidget(self.btn_connect)
        
        self.btn_save_report = QPushButton("💾 Сохранить отчёт сейчас")
        self.btn_save_report.clicked.connect(self.save_report_now)
        self.btn_save_report.setEnabled(False)
        buttons_layout.addWidget(self.btn_save_report)
        
        self.btn_save_config = QPushButton("💾 Сохранить конфиг")
        self.btn_save_config.clicked.connect(self.save_config)
        buttons_layout.addWidget(self.btn_save_config)
        
        self.btn_load_config = QPushButton("📂 Загрузить конфиг")
        self.btn_load_config.clicked.connect(self.load_config)
        buttons_layout.addWidget(self.btn_load_config)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        outer_layout = QVBoxLayout(widget)
        outer_layout.addWidget(scroll)
        
        return widget
    
    def create_collection_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Прогресс по категориям
        group_progress = QGroupBox("🎯 Прогресс сбора данных")
        prog_layout = QGridLayout()
        
        prog_layout.addWidget(QLabel("📍 Координаты базы (1005/1006):"), 0, 0)
        self.lbl_base_coords = QLabel("⏳ Ожидание...")
        self.lbl_base_coords.setFont(QFont("Consolas", 10, QFont.Bold))
        prog_layout.addWidget(self.lbl_base_coords, 0, 1)
        
        prog_layout.addWidget(QLabel("📡 Антенна (1007/1008/1033):"), 1, 0)
        self.lbl_antenna = QLabel("⏳ Ожидание...")
        self.lbl_antenna.setFont(QFont("Consolas", 10, QFont.Bold))
        prog_layout.addWidget(self.lbl_antenna, 1, 1)
        
        # ⭐ НОВОЕ: Параметры СК
        prog_layout.addWidget(QLabel("🌍 Параметры СК (1021-1027):"), 2, 0)
        self.lbl_cs_params = QLabel("⏳ Ожидание...")
        self.lbl_cs_params.setFont(QFont("Consolas", 10, QFont.Bold))
        prog_layout.addWidget(self.lbl_cs_params, 2, 1)
        
        prog_layout.addWidget(QLabel("📛 Названия CRS (1300/1302):"), 3, 0)
        self.lbl_crs_names = QLabel("⏳ Ожидание...")
        self.lbl_crs_names.setFont(QFont("Consolas", 10, QFont.Bold))
        prog_layout.addWidget(self.lbl_crs_names, 3, 1)
        
        prog_layout.addWidget(QLabel("🌐 Проприетарные (геоид?):"), 4, 0)
        self.lbl_geoid = QLabel("⏳ Ожидание...")
        self.lbl_geoid.setFont(QFont("Consolas", 10, QFont.Bold))
        prog_layout.addWidget(self.lbl_geoid, 4, 1)
        
        prog_layout.addWidget(QLabel("📊 Всего собрано типов:"), 5, 0)
        self.lbl_total_types = QLabel("0")
        prog_layout.addWidget(self.lbl_total_types, 5, 1)
        
        group_progress.setLayout(prog_layout)
        layout.addWidget(group_progress)
        
        # Список собранных сообщений
        group_collected = QGroupBox("📋 Собранные типы сообщений")
        collected_layout = QVBoxLayout()
        
        self.text_collected = QTextEdit()
        self.text_collected.setReadOnly(True)
        self.text_collected.setFont(QFont("Consolas", 10))
        collected_layout.addWidget(self.text_collected)
        
        group_collected.setLayout(collected_layout)
        layout.addWidget(group_collected)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 Сохранить финальный отчёт")
        btn_save.clicked.connect(self.save_report_now)
        btn_save.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(btn_save)
        
        btn_diag = QPushButton("🔍 Диагностика СК")
        btn_diag.clicked.connect(self.show_cs_diagnostic)
        btn_diag.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
        btn_layout.addWidget(btn_diag)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    # ⭐ НОВОЕ: Вкладка параметров СК
    def create_cs_tab(self):
        """Вкладка с параметрами системы координат"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Статус
        group_status = QGroupBox("📊 Статус сообщений СК")
        status_layout = QVBoxLayout()
        
        self.lbl_cs_status = QLabel("Подключитесь к серверу для получения параметров СК")
        self.lbl_cs_status.setWordWrap(True)
        self.lbl_cs_status.setFont(QFont("Consolas", 10))
        status_layout.addWidget(self.lbl_cs_status)
        
        group_status.setLayout(status_layout)
        layout.addWidget(group_status)
        
        # Таблица с параметрами
        group_params = QGroupBox("🌍 Параметры системы координат")
        params_layout = QVBoxLayout()
        
        self.table_cs = QTableWidget()
        self.table_cs.setColumnCount(4)
        self.table_cs.setHorizontalHeaderLabels(["ID", "Название", "Параметр", "Значение"])
        self.table_cs.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_cs.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        params_layout.addWidget(self.table_cs)
        
        group_params.setLayout(params_layout)
        layout.addWidget(group_params)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_clear = QPushButton("🗑️ Очистить")
        btn_clear.clicked.connect(lambda: self.table_cs.setRowCount(0))
        btn_layout.addWidget(btn_clear)
        
        btn_export = QPushButton("💾 Экспорт в JSON")
        btn_export.clicked.connect(self.export_cs_to_json)
        btn_layout.addWidget(btn_export)
        
        btn_help = QPushButton("ℹ️ Справка по сообщениям")
        btn_help.clicked.connect(self.show_cs_help)
        btn_layout.addWidget(btn_help)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_log)
        
        btn_clear = QPushButton("🗑️ Очистить лог")
        btn_clear.clicked.connect(self.text_log.clear)
        layout.addWidget(btn_clear)
        
        return widget
    
    def create_params_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.table_params = QTableWidget()
        self.table_params.setColumnCount(4)
        self.table_params.setHorizontalHeaderLabels(["ID", "Название", "Параметр", "Значение"])
        self.table_params.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_params.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table_params)
        
        btn_clear = QPushButton("🗑️ Очистить таблицу")
        btn_clear.clicked.connect(lambda: self.table_params.setRowCount(0))
        layout.addWidget(btn_clear)
        
        return widget
    
    def create_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.text_stats = QTextEdit()
        self.text_stats.setReadOnly(True)
        self.text_stats.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_stats)
        
        return widget
    
    def connect_signals(self):
        self.signals.log_message.connect(self.append_log)
        self.signals.rtcm_message.connect(self.add_rtcm_param)
        self.signals.unknown_message.connect(self.log_unknown_message)
        self.signals.status_changed.connect(self.update_status)
        self.signals.stats_updated.connect(self.update_stats)
        self.signals.sourcetable_received.connect(self.on_sourcetable_received)
        self.signals.last_message_updated.connect(self.update_last_message)
        self.signals.collection_progress.connect(self.update_collection_progress)
        self.signals.collection_complete.connect(self.on_collection_complete)
        self.signals.cs_message_received.connect(self.on_cs_message_received)  # ⭐ НОВОЕ
    
    # === SOURCETABLE ===
    
    def fetch_sourcetable(self):
        self.save_config_to_manager()
        self.btn_fetch_sourcetable.setEnabled(False)
        self.btn_fetch_sourcetable.setText("⏳ Загрузка...")
        
        self.sourcetable_worker = SourcetableWorker(self.config_manager.config.copy(), self.signals)
        self.sourcetable_worker.finished.connect(self.on_sourcetable_finished)
        self.sourcetable_worker.start()
    
    def on_sourcetable_finished(self):
        self.btn_fetch_sourcetable.setEnabled(True)
        self.btn_fetch_sourcetable.setText("🔄 Получить список")
    
    def on_sourcetable_received(self, mountpoints: list):
        self.mountpoints_data = mountpoints
        current = self.combo_mountpoint.currentText()
        
        self.combo_mountpoint.clear()
        for mp in mountpoints:
            display = f"{mp['mountpoint']} — {mp['identifier']} ({mp['format']}, {mp['nav_system']})"
            self.combo_mountpoint.addItem(display, mp['mountpoint'])
        
        found = False
        for i in range(self.combo_mountpoint.count()):
            if self.combo_mountpoint.itemData(i) == current:
                self.combo_mountpoint.setCurrentIndex(i)
                found = True
                break
        
        if not found and current:
            self.combo_mountpoint.setEditText(current)
        
        self.append_log(f"📋 Загружено {len(mountpoints)} маунтпоинтов в список", "success")
    
    # === КОНФИГУРАЦИЯ ===
    
    def load_config_to_ui(self):
        cfg = self.config_manager.config
        self.edit_server.setText(cfg["ntrip_server"])
        self.spin_port.setValue(cfg["ntrip_port"])
        self.combo_mountpoint.setEditText(cfg["mountpoint"])
        self.edit_username.setText(cfg["username"])
        self.edit_password.setText(cfg["password"])
        self.spin_lat.setValue(cfg["base_lat"])
        self.spin_lon.setValue(cfg["base_lon"])
        self.spin_alt.setValue(cfg["base_alt"])
        self.spin_gga_interval.setValue(cfg["gga_interval"])
        self.spin_noise.setValue(cfg["noise_std"])
        self.check_save_raw.setChecked(cfg["save_raw_rtcm"])
        self.check_save_params.setChecked(cfg["save_params_json"])
        self.check_log_unknown.setChecked(cfg["log_unknown_messages"])
        self.check_auto_stop.setChecked(cfg.get("auto_stop_on_complete", False))
        self.spin_auto_timeout.setValue(cfg.get("auto_stop_timeout", 300))
        self.spin_cs_timeout.setValue(cfg.get("cs_messages_timeout", 120))
    
    def save_config_to_manager(self):
        mountpoint = self.combo_mountpoint.currentData()
        if not mountpoint:
            mountpoint = self.combo_mountpoint.currentText().split(" — ")[0].strip()
        
        self.config_manager.update({
            "ntrip_server": self.edit_server.text(),
            "ntrip_port": self.spin_port.value(),
            "mountpoint": mountpoint,
            "username": self.edit_username.text(),
            "password": self.edit_password.text(),
            "base_lat": self.spin_lat.value(),
            "base_lon": self.spin_lon.value(),
            "base_alt": self.spin_alt.value(),
            "gga_interval": self.spin_gga_interval.value(),
            "noise_std": self.spin_noise.value(),
            "save_raw_rtcm": self.check_save_raw.isChecked(),
            "save_params_json": self.check_save_params.isChecked(),
            "log_unknown_messages": self.check_log_unknown.isChecked(),
            "auto_stop_on_complete": self.check_auto_stop.isChecked(),
            "auto_stop_timeout": self.spin_auto_timeout.value(),
            "cs_messages_timeout": self.spin_cs_timeout.value(),
        })
    
    def save_config(self):
        self.save_config_to_manager()
        if self.config_manager.save():
            QMessageBox.information(self, "Успех", "Конфигурация сохранена")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить конфигурацию")
    
    def load_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить конфигурацию", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_manager.config_path = Path(file_path)
            if self.config_manager.load():
                self.load_config_to_ui()
                QMessageBox.information(self, "Успех", "Конфигурация загружена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось загрузить конфигурацию")
    
    # === УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЕМ ===
    
    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.btn_connect.setText("▶️ Подключить")
            self.btn_connect.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
            self.btn_save_report.setEnabled(False)
        else:
            self.save_config_to_manager()
            self.config_manager.save()
            
            self.table_params.setRowCount(0)
            self.table_cs.setRowCount(0)
            self.text_collected.clear()
            
            self.worker = NTRIPWorker(self.config_manager.config.copy(), self.signals)
            self.worker.start()
            
            self.btn_connect.setText("⏹️ Отключить")
            self.btn_connect.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
            self.btn_save_report.setEnabled(True)
    
    def save_report_now(self):
        if self.worker and self.worker.isRunning():
            self.worker._save_final_report()
            QMessageBox.information(self, "Успех", "Отчёт сохранён в папку data/")
        else:
            QMessageBox.warning(self, "Внимание", "Подключение не активно")
    
    def on_collection_complete(self, progress):
        self.append_log("🎉 Сбор данных завершён", "success")
        QMessageBox.information(
            self, "Сбор завершён",
            "Все обязательные данные собраны.\nОтчёт сохранён в папку data/"
        )
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.btn_connect.setText("▶️ Подключить")
        self.btn_connect.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        self.btn_save_report.setEnabled(False)
    
    # ⭐ НОВОЕ: Обработка сообщений СК
    def on_cs_message_received(self, msg_id: int, params: dict):
        """Обработка получения сообщения СК"""
        if msg_id not in COORDINATE_SYSTEM_MESSAGES:
            return
        
        cs_info = COORDINATE_SYSTEM_MESSAGES[msg_id]
        
        # Очистка старых строк для этого msg_id
        rows_to_remove = []
        for row in range(self.table_cs.rowCount()):
            item = self.table_cs.item(row, 0)
            if item and item.text() == str(msg_id):
                rows_to_remove.append(row)
        
        for row in reversed(rows_to_remove):
            self.table_cs.removeRow(row)
        
        # Добавление новых параметров
        if not params:
            # Если pyrtcm не разобрал — добавим хотя бы запись
            row = self.table_cs.rowCount()
            self.table_cs.insertRow(row)
            self.table_cs.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_cs.setItem(row, 1, QTableWidgetItem(cs_info["name"]))
            self.table_cs.setItem(row, 2, QTableWidgetItem("(сырые данные)"))
            self.table_cs.setItem(row, 3, QTableWidgetItem("См. финальный отчёт (raw_hex)"))
            return
        
        for key, value in params.items():
            row = self.table_cs.rowCount()
            self.table_cs.insertRow(row)
            self.table_cs.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_cs.setItem(row, 1, QTableWidgetItem(cs_info["name"]))
            
            # Подставляем понятное имя поля
            field_name = cs_info["fields"].get(key, key)
            self.table_cs.setItem(row, 2, QTableWidgetItem(f"{key}: {field_name}"))
            self.table_cs.setItem(row, 3, QTableWidgetItem(str(value)))
        
        # Обновление статуса
        self.update_cs_status()
    
    def update_cs_status(self):
        """Обновление статуса сообщений СК"""
        if not self.worker:
            return
        
        collected_ids = set(self.worker.collected_params.keys())
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = collected_ids & cs_ids
        cs_missing = cs_ids - collected_ids
        
        if not cs_collected:
            self.lbl_cs_status.setText(
                "⏳ Сообщения СК (1021-1027, 1300, 1302) пока не получены.\n"
                "Это нормально — провайдер может слать их редко (раз в 1-10 минут) или только при нахождении в зоне МСК."
            )
            self.lbl_cs_status.setStyleSheet("color: orange;")
        else:
            received_names = [f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})" 
                            for mid in sorted(cs_collected)]
            missing_names = [f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})" 
                           for mid in sorted(cs_missing)]
            
            text = f"✅ Получено: {', '.join(received_names)}\n\n"
            if missing_names:
                text += f"⏳ Ожидается: {', '.join(missing_names)}"
            else:
                text += "🎉 Все сообщения СК получены!"
            
            self.lbl_cs_status.setText(text)
            self.lbl_cs_status.setStyleSheet("color: green;" if not cs_missing else "color: orange;")
    
    def show_cs_diagnostic(self):
        """Диагностика сообщений СК"""
        if not self.worker:
            QMessageBox.information(
                self, "Диагностика",
                "Подключитесь к серверу для диагностики."
            )
            return
        
        collected_ids = set(self.worker.collected_params.keys())
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = collected_ids & cs_ids
        cs_missing = cs_ids - collected_ids
        
        text = "=== ДИАГНОСТИКА СООБЩЕНИЙ СК ===\n\n"
        
        text += f"📍 Координаты ровера:\n"
        text += f"   Широта: {self.config_manager.config['base_lat']:.6f}°\n"
        text += f"   Долгота: {self.config_manager.config['base_lon']:.6f}°\n\n"
        
        text += f"✅ Получено ({len(cs_collected)}):\n"
        for mid in sorted(cs_collected):
            count = self.worker.collected_params[mid]["count"]
            text += f"   • {mid} — {COORDINATE_SYSTEM_MESSAGES[mid]['name']} (получено {count} раз)\n"
        
        text += f"\n⏳ Ожидается ({len(cs_missing)}):\n"
        for mid in sorted(cs_missing):
            text += f"   • {mid} — {COORDINATE_SYSTEM_MESSAGES[mid]['name']}\n"
        
        text += "\n💡 Возможные причины отсутствия:\n"
        text += "   1. Провайдер шлёт их редко (раз в 5-10 минут)\n"
        text += "   2. Координаты вне зоны действия МСК\n"
        text += "   3. Провайдер не передаёт параметры СК через RTCM\n"
        text += "   4. Параметры СК в проприетарных сообщениях\n"
        
        QMessageBox.information(self, "Диагностика СК", text)
    
    def export_cs_to_json(self):
        """Экспорт параметров СК в отдельный JSON"""
        if not self.worker:
            QMessageBox.warning(self, "Внимание", "Нет данных для экспорта")
            return
        
        cs_data = self.worker._extract_coordinate_system()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить параметры СК", 
            f"cs_params_{timestamp}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cs_data, f, indent=2, ensure_ascii=False, default=str)
                QMessageBox.information(self, "Успех", f"Параметры СК сохранены:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")
    
    def show_cs_help(self):
        """Справка по сообщениям СК"""
        text = "=== СООБЩЕНИЯ СИСТЕМЫ КООРДИНАТ (RTCM 3.1+) ===\n\n"
        
        for mid in [1021, 1022, 1023, 1024, 1025, 1026, 1027, 1300, 1302]:
            info = COORDINATE_SYSTEM_MESSAGES[mid]
            text += f"📌 {mid}: {info['name']}\n"
            text += f"   {info['description']}\n\n"
        
        text += "\n💡 Примечание:\n"
        text += "Сообщения 1021-1027 передают параметры перехода из глобальных\n"
        text += "геоцентрических СК (ITRF/WGS84) в локальные (МСК).\n"
        text += "Сообщения 1300/1302 передают названия исходной и целевой СК."
        
        QMessageBox.information(self, "Справка по сообщениям СК", text)
    
    # === ОБНОВЛЕНИЕ UI ===
    
    def append_log(self, message, level):
        color_map = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        color = color_map.get(level, "black")
        self.text_log.append(f'<span style="color:{color};">{message}</span>')
        
        try:
            log_file = LOGS_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except Exception as e:
            print(f"Ошибка записи в лог-файл: {e}")
    
    def add_rtcm_param(self, msg_id, msg_name, params):
        if not params:
            return
        for key, value in params.items():
            row = self.table_params.rowCount()
            self.table_params.insertRow(row)
            self.table_params.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_params.setItem(row, 1, QTableWidgetItem(msg_name))
            self.table_params.setItem(row, 2, QTableWidgetItem(key))
            self.table_params.setItem(row, 3, QTableWidgetItem(str(value)))
        
        if self.table_params.rowCount() > 0:
            self.table_params.scrollToBottom()
    
    def log_unknown_message(self, msg_id, raw_data):
        hex_data = raw_data.hex()
        self.append_log(
            f"⚠️ НЕИЗВЕСТНОЕ ID={msg_id}, {len(raw_data)} байт, "
            f"HEX: {hex_data[:100]}{'...' if len(hex_data) > 100 else ''}",
            "warning"
        )
    
    def update_status(self, status):
        self.status_label.setText(f"Статус: {status}")
    
    def update_stats(self, stats):
        self.lbl_bytes_rx.setText(f"{stats.get('bytes_received', 0):,} байт")
        self.lbl_bytes_tx.setText(f"{stats.get('bytes_sent', 0):,} байт")
        self.lbl_messages.setText(f"{stats.get('messages_parsed', 0):,}")
        self.lbl_valid.setText(f"{stats.get('messages_valid', 0):,}")
        self.lbl_crc_failed.setText(f"{stats.get('messages_crc_failed', 0):,}")
        self.lbl_gga.setText(f"{stats.get('gga_sent', 0):,}")
        
        speed = stats.get('bytes_per_sec', 0)
        if speed > 1024:
            self.lbl_speed.setText(f"{speed/1024:.1f} КБ/с")
        else:
            self.lbl_speed.setText(f"{speed:.0f} байт/с")
        
        text = "=== СТАТИСТИКА ПОДКЛЮЧЕНИЯ ===\n\n"
        text += f"Подключено с: {stats.get('connected_since', 'N/A')}\n"
        text += f"Получено байт: {stats.get('bytes_received', 0):,}\n"
        text += f"Отправлено байт: {stats.get('bytes_sent', 0):,}\n"
        text += f"Скорость: {stats.get('bytes_per_sec', 0):.1f} байт/с\n"
        text += f"Обработано сообщений: {stats.get('messages_parsed', 0):,}\n"
        text += f"Валидных (CRC OK): {stats.get('messages_valid', 0):,}\n"
        text += f"CRC ошибок: {stats.get('messages_crc_failed', 0):,}\n"
        text += f"Неизвестных: {stats.get('unknown_messages', 0):,}\n"
        text += f"Отправлено GGA: {stats.get('gga_sent', 0):,}\n"
        text += f"\n=== ПОСЛЕДНЕЕ СООБЩЕНИЕ ===\n\n"
        text += f"ID: {stats.get('last_message_id', '—')}\n"
        text += f"Название: {stats.get('last_message_name', '—')}\n"
        text += f"Время: {stats.get('last_message_time', '—')}\n"
        
        self.text_stats.setPlainText(text)
    
    def update_last_message(self, msg_info: dict):
        self.lbl_last_id.setText(str(msg_info.get("id", "—")))
        self.lbl_last_name.setText(msg_info.get("name", "—"))
        self.lbl_last_time.setText(msg_info.get("time", "—"))
        self.lbl_last_size.setText(f"{msg_info.get('length', 0)} байт")
    
    def update_collection_progress(self, progress: dict):
        # Координаты базы
        if progress["has_base_coords"]:
            self.lbl_base_coords.setText("✅ Получено")
            self.lbl_base_coords.setStyleSheet("color: green;")
        else:
            self.lbl_base_coords.setText("⏳ Ожидание...")
            self.lbl_base_coords.setStyleSheet("color: orange;")
        
        # Антенна
        if progress["has_antenna"]:
            self.lbl_antenna.setText("✅ Получено")
            self.lbl_antenna.setStyleSheet("color: green;")
        else:
            self.lbl_antenna.setText("⏳ Ожидание...")
            self.lbl_antenna.setStyleSheet("color: orange;")
        
        # ⭐ НОВОЕ: Параметры СК
        cs_collected = progress.get("cs_collected", [])
        if cs_collected:
            self.lbl_cs_params.setText(f"✅ Получено ({len(cs_collected)}): {cs_collected}")
            self.lbl_cs_params.setStyleSheet("color: green;")
        else:
            self.lbl_cs_params.setText("⏳ Ожидание...")
            self.lbl_cs_params.setStyleSheet("color: orange;")
        
        # ⭐ НОВОЕ: Названия CRS
        has_1300 = 1300 in cs_collected
        has_1302 = 1302 in cs_collected
        if has_1300 or has_1302:
            parts = []
            if has_1300: parts.append("source")
            if has_1302: parts.append("target")
            self.lbl_crs_names.setText(f"✅ Получено: {', '.join(parts)}")
            self.lbl_crs_names.setStyleSheet("color: green;")
        else:
            self.lbl_crs_names.setText("⏳ Ожидание (опционально)")
            self.lbl_crs_names.setStyleSheet("color: gray;")
        
        # Геоид
        if progress["has_proprietary"]:
            self.lbl_geoid.setText(f"✅ Получено ({len(progress['proprietary_collected'])} шт)")
            self.lbl_geoid.setStyleSheet("color: green;")
        else:
            self.lbl_geoid.setText("⏳ Ожидание (опционально)")
            self.lbl_geoid.setStyleSheet("color: gray;")
        
        # Всего типов
        self.lbl_total_types.setText(f"{progress['total_collected']}")
        
        # Список собранных
        self.text_collected.clear()
        for mid in progress["collected_ids"]:
            name = KNOWN_RTCM_MESSAGES.get(mid, f"Unknown_{mid}")
            count = self.worker.collected_params[mid]["count"] if self.worker and mid in self.worker.collected_params else 0
            
            is_target = mid in TARGET_MESSAGES
            is_cs = mid in COORDINATE_SYSTEM_MESSAGES
            marker = "🌍" if is_cs else ("🎯" if is_target else "  ")
            
            self.text_collected.append(f"{marker} ID {mid}: {name} (получено: {count} раз)")
    
    def update_uptime(self):
        if self.worker and self.worker.isRunning() and self.worker.stats.get("connected_since"):
            try:
                start = datetime.fromisoformat(self.worker.stats["connected_since"])
                delta = datetime.now() - start
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.lbl_uptime.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            except:
                self.lbl_uptime.setText("—")
        else:
            self.lbl_uptime.setText("00:00:00")
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        if self.sourcetable_worker and self.sourcetable_worker.isRunning():
            self.sourcetable_worker.wait()
        event.accept()


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()