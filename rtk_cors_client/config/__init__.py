# -*- coding: utf-8 -*-
"""Конфигурация: константы, настройки, парсер sourcetable."""
from .constants import (  # noqa: F401
    CONFIG_FILE,
    COORDINATE_SYSTEM_MESSAGES,
    DATA_DIR_NAME,
    DEFAULT_CONFIG,
    KNOWN_RTCM_MESSAGES,
    LOGS_DIR_NAME,
    PROPRIETARY_RANGE,
    PROPRIETARY_TARGETS,
    TARGET_MESSAGES,
    USER_AGENT,
)
from .settings import ConfigManager  # noqa: F401
from .sourcetable import SourcetableParser  # noqa: F401
