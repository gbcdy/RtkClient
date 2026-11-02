# -*- coding: utf-8 -*-
"""Коллектор базовой станции: сообщения 1005/1006 (ARP в ECEF).

Логика перенесена из NTRIPWorker._extract_base_station() монолитного rtk4.py.
"""
from rtk_cors_client.converters.coordinates import ecef_to_wgs84

from .base import BaseCollector


class BaseStationCollector(BaseCollector):
    """Накапливает координаты базы (1005 — ARP, 1006 — ARP + высота антенны)."""

    def supported_messages(self) -> list:
        return [1005, 1006]

    def __init__(self):
        self.messages = {}  # {msg_id: {"params": {...}, "count": n}}

    def collect(self, msg_id: int, params: dict, raw: bytes) -> None:
        entry = self.messages.setdefault(msg_id, {"params": {}, "count": 0})
        entry["params"] = params
        entry["count"] += 1

    def get_status(self) -> dict:
        return {
            "received": sorted(self.messages.keys()),
            "has_base_coords": bool(self.messages),
        }

    def export(self) -> dict:
        """Формирует секцию отчёта base_station (как в оригинале)."""
        result = {}

        for mid in (1005, 1006):
            if mid not in self.messages:
                continue
            p = self.messages[mid]["params"]
            section = {
                "reference_station_id": p.get("DF003"),
                "ecef_x_m": p.get("DF025"),
                "ecef_y_m": p.get("DF026"),
                "ecef_z_m": p.get("DF027"),
            }
            if mid == 1006:
                section["antenna_height_m"] = p.get("DF141")
            result[f"msg_{mid}"] = section

            try:
                x = float(p.get("DF025", 0)) / 10000.0
                y = float(p.get("DF026", 0)) / 10000.0
                z = float(p.get("DF027", 0)) / 10000.0
                lat, lon, alt = ecef_to_wgs84(x, y, z)
                result["wgs84"] = {"lat": lat, "lon": lon, "alt": alt}
            except Exception as e:
                result["wgs84_error"] = str(e)

        return result

    def reset(self):
        self.messages = {}
