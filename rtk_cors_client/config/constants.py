# -*- coding: utf-8 -*-
"""Константы приложения и словари RTCM-сообщений.

Вынесено из монолитного rtk4.py (секция «КОНСТАНТЫ»).
"""

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
    "auto_stop_timeout": 300,   # сек — ожидание редких сообщений
    "cs_messages_timeout": 120, # через сколько сек предупреждать об отсутствии СК
}

CONFIG_FILE = "config.json"
LOGS_DIR_NAME = "logs"
DATA_DIR_NAME = "data"

USER_AGENT = "NTRIP Trimble Access/23.10"

# ============================================================================
# СООБЩЕНИЯ СИСТЕМЫ КООРДИНАТ (1021-1027, 1300, 1302)
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
    # Сообщения СК
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
    # Сообщения СК
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
