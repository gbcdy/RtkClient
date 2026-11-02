# -*- coding: utf-8 -*-
"""Коллектор антенны/приёмника: сообщения 1007/1008/1033.

Логика перенесена из NTRIPWorker._extract_antenna() монолитного rtk4.py.
"""
from .base import BaseCollector


class AntennaCollector(BaseCollector):
    """Накапливает описания антенны и приёмника."""

    def supported_messages(self) -> list:
        return [1007, 1008, 1033]

    def __init__(self):
        self.messages = {}  # {msg_id: {"params": {...}, "count": n}}

    def collect(self, msg_id: int, params: dict, raw: bytes) -> None:
        entry = self.messages.setdefault(msg_id, {"params": {}, "count": 0})
        entry["params"] = params
        entry["count"] += 1

    def get_status(self) -> dict:
        return {
            "received": sorted(self.messages.keys()),
            "has_antenna": bool(self.messages),
        }

    def export(self) -> dict:
        """Формирует секцию отчёта antenna (как в оригинале)."""
        result = {}

        if 1007 in self.messages:
            p = self.messages[1007]["params"]
            result["msg_1007"] = {
                "antenna_descriptor": p.get("DF143"),
                "antenna_setup_id": p.get("DF144"),
            }

        if 1008 in self.messages:
            p = self.messages[1008]["params"]
            result["msg_1008"] = {
                "antenna_descriptor": p.get("DF143"),
                "antenna_serial": p.get("DF004"),
                "antenna_setup_id": p.get("DF144"),
            }

        if 1033 in self.messages:
            p = self.messages[1033]["params"]
            result["msg_1033"] = {
                "receiver_descriptor": p.get("DF029"),
                "receiver_serial": p.get("DF030"),
                "receiver_fw": p.get("DF232"),
                "antenna_descriptor": p.get("DF143"),
                "antenna_serial": p.get("DF004"),
                "antenna_setup_id": p.get("DF144"),
            }

        return result

    def reset(self):
        self.messages = {}
