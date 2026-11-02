# -*- coding: utf-8 -*-
"""Коллектор проприетарных сообщений (диапазон 4001-4095).

Логика перенесена из NTRIPWorker.parse_rtcm_buffer() (обработка unknown)
и _extract_geoid_and_cs() монолитного rtk4.py.
"""
from rtk_cors_client.config.constants import PROPRIETARY_TARGETS

from .base import BaseCollector


class ProprietaryCollector(BaseCollector):
    """Накапливает известные целевые проприетарные сообщения и HEX-дампы неизвестных."""

    MAX_HEX_SAMPLES = 5

    def supported_messages(self) -> list:
        return sorted(PROPRIETARY_TARGETS.keys())

    def __init__(self):
        self.messages = {}          # {msg_id: {"params": {...}, "count": n}}
        self.unknown = {}           # {msg_id: {"count": n, "hex_samples": [...]}}

    def collect(self, msg_id: int, params: dict, raw: bytes) -> None:
        entry = self.messages.setdefault(msg_id, {"params": {}, "count": 0})
        entry["params"] = params
        entry["count"] += 1

    def collect_unknown(self, msg_id: int, raw: bytes) -> None:
        """Неизвестное проприетарное сообщение — сохраняем HEX-образцы."""
        if msg_id not in self.unknown:
            self.unknown[msg_id] = {"count": 0, "hex_samples": []}
        self.unknown[msg_id]["count"] += 1
        if len(self.unknown[msg_id]["hex_samples"]) < self.MAX_HEX_SAMPLES:
            self.unknown[msg_id]["hex_samples"].append(raw.hex())

    def get_status(self) -> dict:
        return {
            "has_proprietary": bool(self.messages),
            "proprietary_collected": sorted(self.messages.keys()),
            "unknown_count": len(self.unknown),
        }

    def export(self) -> dict:
        """Формирует секцию отчёта geoid_and_cs (как в оригинале)."""
        result = {}

        for msg_id in PROPRIETARY_TARGETS:
            if msg_id in self.messages:
                result[f"msg_{msg_id}"] = {
                    "name": PROPRIETARY_TARGETS[msg_id],
                    "params": self.messages[msg_id]["params"],
                    "count": self.messages[msg_id]["count"],
                }

        for msg_id, data in self.unknown.items():
            result[f"unknown_{msg_id}"] = {
                "name": f"Unknown proprietary {msg_id}",
                "count": data["count"],
                "hex_samples": data["hex_samples"],
                "note": "Требует анализа. Возможно содержит параметры СК/геоида/коррекции",
            }

        return result

    def reset(self):
        self.messages = {}
        self.unknown = {}
