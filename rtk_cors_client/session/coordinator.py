# -*- coding: utf-8 -*-
"""Координатор сбора данных: прогресс, автоостановка, финальный отчёт.

Слои приложения (см. architecture.md):
  UI -> CollectionCoordinator -> NTRIPWorker -> парсеры RTCM.

Логика перенесена из NTRIPWorker._update_collection_progress(),
_check_cs_timeout() и _save_final_report() монолитного rtk4.py.
"""
from datetime import datetime
from pathlib import Path

from rtk_cors_client.config.constants import (
    COORDINATE_SYSTEM_MESSAGES,
    DATA_DIR_NAME,
    PROPRIETARY_TARGETS,
    TARGET_MESSAGES,
)
from rtk_cors_client.exporters.json_report import JsonReportExporter


class CollectionCoordinator:
    """Управляет процессом сбора целевых сообщений и формированием отчёта.

    Args:
        config: словарь конфигурации.
        registry: CollectorRegistry со встроенными коллекторами.
        log_fn: вызываемый объект log(message, level).
        emit_progress / emit_complete / request_stop: коллбэки в Qt-слой.
    """

    CS_DIAGNOSTIC_HINTS = (
        "💡 Возможные причины:",
        "   1. Провайдер шлёт их редко (раз в 5-10 минут)",
        "   2. Координаты ровера вне зоны действия МСК",
        "   3. Провайдер не передаёт параметры СК через RTCM",
        "   4. Параметры СК зашиты в проприетарных сообщениях",
        "💡 Рекомендация: увеличить таймаут или проверить координаты",
    )

    def __init__(self, config: dict, registry, log_fn=None,
                 emit_progress=None, emit_complete=None,
                 request_stop=None, data_dir: Path = None):
        self.config = config
        self.registry = registry
        self.log = log_fn or (lambda msg, level="info": None)
        self.emit_progress = emit_progress or (lambda p: None)
        self.emit_complete = emit_complete or (lambda p: None)
        self.request_stop = request_stop or (lambda: None)
        self.data_dir = Path(data_dir) if data_dir else Path(DATA_DIR_NAME)

        self.cs_warning_shown = False
        self.report_saved = False

    # ------------------------------------------------------------------
    # Прогресс
    # ------------------------------------------------------------------
    def collected_ids(self) -> set:
        ids = set()
        for collector in self.registry.collectors():
            ids.update(collector.messages.keys())
        return ids

    def compute_progress(self) -> dict:
        collected_ids = self.collected_ids()
        target_ids = set(TARGET_MESSAGES.keys())
        proprietary_collected = sorted(
            mid for mid in collected_ids if mid in PROPRIETARY_TARGETS
        )

        has_base_coords = bool(collected_ids & {1005, 1006})
        has_antenna = bool(collected_ids & {1007, 1008, 1033})
        has_proprietary = len(proprietary_collected) > 0

        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = sorted(list(collected_ids & cs_ids))
        has_cs = len(cs_collected) > 0

        return {
            "has_base_coords": has_base_coords,
            "has_antenna": has_antenna,
            "has_proprietary": has_proprietary,
            "has_cs": has_cs,
            "cs_collected": cs_collected,
            "collected_ids": sorted(list(collected_ids)),
            "target_ids": sorted(list(target_ids)),
            "proprietary_collected": proprietary_collected,
            "total_collected": len(collected_ids),
            "is_complete": has_base_coords and has_antenna,
        }

    def on_message(self, msg_id: int) -> dict:
        """Вызывается после dispatch в реестр: emits progress, проверяет автоостановку."""
        progress = self.compute_progress()
        self.emit_progress(progress)

        if self.config.get("auto_stop_on_complete") and progress["is_complete"]:
            self.log("✅ Все обязательные данные собраны. Автоостановка...", "success")
            self.save_final_report()
            self.emit_complete(progress)
            self.request_stop()

        return progress

    # ------------------------------------------------------------------
    # Диагностика отсутствия сообщений СК
    # ------------------------------------------------------------------
    def check_cs_timeout(self, connected_since_iso: str) -> None:
        """Предупреждение, если за cs_messages_timeout не получено ни одного СК-сообщения."""
        if self.cs_warning_shown:
            return

        cs_timeout = self.config.get("cs_messages_timeout", 120)
        if not connected_since_iso:
            return

        try:
            start = datetime.fromisoformat(connected_since_iso)
            elapsed = (datetime.now() - start).total_seconds()
        except Exception:
            return

        if elapsed <= cs_timeout:
            return

        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        missing_cs = cs_ids - self.collected_ids()

        if missing_cs:
            self.cs_warning_shown = True
            missing_names = [
                f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})"
                for mid in sorted(missing_cs)
            ]

            self.log(f"⚠️ ВНИМАНИЕ: Сообщения СК не получены за {cs_timeout}с!", "warning")
            self.log(f"⚠️ Отсутствуют: {', '.join(missing_names)}", "warning")
            for hint in self.CS_DIAGNOSTIC_HINTS:
                self.log(hint, "warning")

    # ------------------------------------------------------------------
    # Финальный отчёт
    # ------------------------------------------------------------------
    def build_report(self, stats: dict) -> dict:
        exports = self.registry.export_all()
        cs_collector = self.registry.get(1021)  # CoordinateSystemCollector

        report = {
            "report_time": datetime.now().isoformat(),
            "config": self.config,
            "stats": stats,
            "base_station": exports.get("BaseStationCollector", {}),
            "antenna": exports.get("AntennaCollector", {}),
            "system_parameters": self._extract_system_parameters(),
            "coordinate_system": exports.get("CoordinateSystemCollector", {}),
            "geoid_and_cs": exports.get("ProprietaryCollector", {}),
            "all_collected_messages": self._all_collected_messages(),
            "unknown_proprietary": self._unknown_proprietary(),
            "cs_messages_status": (
                cs_collector.status_section() if cs_collector else {}
            ),
        }
        return report

    def _extract_system_parameters(self) -> dict:
        """Системные параметры: 1013 / 1230 (как в оригинале)."""
        result = {}
        all_msgs = self._all_collected_messages()
        for mid in (1013, 1230):
            key = str(mid)
            if key in all_msgs:
                result[f"msg_{mid}"] = all_msgs[key].get("params", {})
        return result

    def _all_collected_messages(self) -> dict:
        result = {}
        for collector in self.registry.collectors():
            for mid, entry in getattr(collector, "messages", {}).items():
                result[str(mid)] = {
                    "params": entry.get("params", {}),
                    "count": entry.get("count", 0),
                    "last_time": datetime.now().isoformat(),
                }
                if "raw_hex" in entry and entry["raw_hex"]:
                    result[str(mid)]["raw_hex"] = entry["raw_hex"]
        return result

    def _unknown_proprietary(self) -> dict:
        result = {}
        for collector in self.registry.collectors():
            unknown = getattr(collector, "unknown", None)
            if unknown:
                for mid, data in unknown.items():
                    result[str(mid)] = dict(data)
        return result

    def save_final_report(self, stats: dict = None) -> Path:
        """Сохраняет final_report_<timestamp>.json в data_dir."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.data_dir / f"final_report_{timestamp}.json"

        report = self.build_report(stats or {})
        try:
            JsonReportExporter().export(report, report_path)
            self.report_saved = True
            self.log(f"💾 Финальный отчёт сохранён: {report_path}", "success")
        except Exception as e:
            self.log(f"❌ Ошибка сохранения отчёта: {e}", "error")
        return report_path
