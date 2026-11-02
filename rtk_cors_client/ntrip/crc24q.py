# -*- coding: utf-8 -*-
"""CRC24Q — табличный расчёт CRC-24Q для RTCM (полином 0x1864CFB)."""


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
