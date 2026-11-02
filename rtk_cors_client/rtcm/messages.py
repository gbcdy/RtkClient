# -*- coding: utf-8 -*-
"""Декодирование RTCM-сообщений (обёртка над pyrtcm + fallback).

Логика извлечения параметров и сериализации значений перенесена
из NTRIPWorker.parse_rtcm_buffer() / _serialize_value() монолитного rtk4.py.
"""
from pyrtcm import RTCMReader


def serialize_value(value):
    """Приводит произвольное значение к JSON-сериализуемому виду."""
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    return str(value)


class RTCMMessageDecoder:
    """Парсит валидированный RTCM-кадр через pyrtcm.

    Если pyrtcm не поддерживает сообщение (например 1300/1302),
    parse() бросает исключение — вызывающий код может использовать
    raw_hex как fallback (см. rtcm/cs_messages.py).
    """

    @staticmethod
    def extract_message_id(frame: bytes) -> int:
        """ID сообщения из байтов 3-4 кадра (12 бит)."""
        if len(frame) < 5:
            return 0
        return (frame[3] << 4) | (frame[4] >> 4)

    @staticmethod
    def parse(frame: bytes) -> dict:
        """Возвращает словарь параметров сообщения (DF-поля)."""
        parsed = RTCMReader.parse(frame)
        params = {}
        if hasattr(parsed, '__dict__'):
            for key, value in parsed.__dict__.items():
                if not key.startswith('_'):
                    params[key] = serialize_value(value)
        return params
