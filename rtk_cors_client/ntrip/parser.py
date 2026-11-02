# -*- coding: utf-8 -*-
"""Фасоль обратной совместимости: RTCM-парсер живёт в rtcm.parser.

Модуль оставлен, чтобы старый код (`from ntrip.parser import ...`)
не ломался при переносе. Новый код должен импортировать
``rtk_cors_client.rtcm.parser`` напрямую.
"""
from rtk_cors_client.ntrip.crc24q import CRC24Q  # noqa: F401
from rtk_cors_client.rtcm.parser import (  # noqa: F401
    MAX_PAYLOAD,
    SYNC_BYTE,
    RTCMFrame,
    RTCMFrameParser,
)
