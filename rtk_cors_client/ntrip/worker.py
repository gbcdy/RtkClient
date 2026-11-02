# -*- coding: utf-8 -*-
"""Qt-воркеры: тонкая обёртка QThread над SessionManager (без бизнес-логики).

Логика «что делать» живёт в session/; здесь только запуск в потоке
и мост коллбэков в сигналы NTRIPSignals.
"""
from PyQt5.QtCore import QThread

from rtk_cors_client.session.manager import SessionManager


class WorkerThread(QThread):
    """Запускает произвольную функцию в отдельном QThread."""

    def __init__(self, fn, signals=None):
        super().__init__()
        self._fn = fn
        self.signals = signals

    def run(self):
        try:
            self._fn()
        except Exception as e:
            if self.signals is not None:
                self.signals.log_message.emit(f"❌ Ошибка воркера: {e}", "error")


class CallbackBridge:
    """Мост: методы SessionManager.callbacks -> Qt-сигналы NTRIPSignals."""

    def __init__(self, signals):
        self.signals = signals

    def log_message(self, message, level="info"):
        self.signals.log_message.emit(message, level)

    def rtcm_message(self, msg_id, msg_name, params):
        self.signals.rtcm_message.emit(msg_id, msg_name, params)

    def unknown_message(self, msg_id, raw_data):
        self.signals.unknown_message.emit(msg_id, raw_data)

    def status_changed(self, status):
        self.signals.status_changed.emit(status)

    def stats_updated(self, stats):
        self.signals.stats_updated.emit(stats)

    def last_message_updated(self, msg_info):
        self.signals.last_message_updated.emit(msg_info)

    def collection_progress(self, progress):
        self.signals.collection_progress.emit(progress)

    def collection_complete(self, progress):
        self.signals.collection_complete.emit(progress)

    def cs_message_received(self, msg_id, params):
        self.signals.cs_message_received.emit(msg_id, params)


class NTRIPWorker(WorkerThread):
    """QThread-обёртка над SessionManager — сохраняет интерфейс оригинала."""

    def __init__(self, config: dict, signals):
        self.signals = signals
        self.manager = SessionManager(
            config=config,
            callbacks=CallbackBridge(signals),
        )
        super().__init__(fn=self.manager.run, signals=signals)

    # --- Совместимость с UI-кодом оригинала -------------------------
    @property
    def stats(self) -> dict:
        return self.manager.stats

    @property
    def registry(self):
        return self.manager.registry

    @property
    def collected_params(self) -> dict:
        """Плоский view всех коллекторов: {msg_id: {"params", "count", ...}}."""
        merged = {}
        for collector in self.registry.collectors():
            for mid, entry in getattr(collector, "messages", {}).items():
                merged[mid] = entry
        return merged

    def stop(self):
        self.manager.stop()

    def _save_final_report(self):
        """Совместимость с MainWindow.save_report_now()."""
        return self.manager.coordinator.save_final_report(self.manager.stats.copy())

    def _extract_coordinate_system(self) -> dict:
        """Совместимость с MainWindow.export_cs_to_json()."""
        cs_collector = self.registry.get(1021)
        return cs_collector.export() if cs_collector else {}
