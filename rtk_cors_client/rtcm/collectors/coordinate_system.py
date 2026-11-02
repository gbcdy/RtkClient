# -*- coding: utf-8 -*-
"""Коллектор системы координат: сообщения 1021-1027, 1300/1302.

Логика перенесена из NTRIPWorker._extract_coordinate_system()
и _handle_cs_message() монолитного rtk4.py.
"""
import time

from rtk_cors_client.config.constants import COORDINATE_SYSTEM_MESSAGES

from .base import BaseCollector


class CoordinateSystemCollector(BaseCollector):
    """Накапливает параметры СК: преобразования, сетки, проекции, названия CRS."""

    def supported_messages(self) -> list:
        return sorted(COORDINATE_SYSTEM_MESSAGES.keys())

    def __init__(self):
        self.messages = {}      # {msg_id: {"params": {...}, "count": n, "raw_hex": str}}
        self.first_seen = {}    # {msg_id: timestamp}

    def collect(self, msg_id: int, params: dict, raw: bytes) -> None:
        now = time.time()
        if msg_id not in self.first_seen:
            self.first_seen[msg_id] = now

        entry = self.messages.setdefault(
            msg_id, {"params": {}, "count": 0, "raw_hex": ""}
        )
        if params:
            entry["params"] = params
        entry["count"] += 1
        # Сохраняем сырые данные (fallback, если pyrtcm не разобрал 1300/1302)
        entry["raw_hex"] = raw.hex()

    def get_status(self) -> dict:
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        collected = set(self.messages.keys())
        return {
            "has_cs": bool(collected),
            "cs_collected": sorted(collected),
            "cs_missing": sorted(cs_ids - collected),
        }

    def export(self) -> dict:
        """Формирует секцию отчёта coordinate_system (как в оригинале)."""
        result = {
            "received": [],
            "missing": [],
            "transforms": {},
            "grids": {},
            "projections": {},
            "crs_names": {},
        }

        # Преобразования (1021, 1022)
        for mid in [1021, 1022]:
            if mid in self.messages:
                p = self.messages[mid]["params"]
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
            if mid in self.messages:
                p = self.messages[mid]["params"]
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
            if mid in self.messages:
                p = self.messages[mid]["params"]
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
            if mid in self.messages:
                p = self.messages[mid]["params"]
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

    def status_section(self) -> dict:
        """Секция cs_messages_status для финального отчёта."""
        return {
            str(mid): {
                "name": COORDINATE_SYSTEM_MESSAGES[mid]["name"],
                "received": mid in self.messages,
                "first_seen": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(self.first_seen[mid])
                ) if mid in self.first_seen else None,
            }
            for mid in COORDINATE_SYSTEM_MESSAGES.keys()
        }

    def reset(self):
        self.messages = {}
        self.first_seen = {}
