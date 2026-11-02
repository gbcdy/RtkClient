# -*- coding: utf-8 -*-
"""MainWindow — сборка главного окна из независимых вкладок.

Архитектура (см. architecture.md):
  * окно создаёт ConfigManager, NTRIPSignals и вкладки из реестра MAIN_TABS;
  * бизнес-логика приёма — в session.SessionManager (через ntrip.NTRIPWorker);
  * вкладки общаются с сетевым слоем ТОЛЬКО через signals;
  * действия вкладок (подключение/отчёт/sourcetable) делегируются сюда.

Добавление новой вкладки: файл в ui/tabs/ + строка в ui.MAIN_TABS.
"""
import importlib

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget, QWidget

from rtk_cors_client.config.settings import ConfigManager
from rtk_cors_client.ntrip.signals import NTRIPSignals
from rtk_cors_client.ntrip.sourcetable_worker import SourcetableWorker
from rtk_cors_client.ntrip.worker import NTRIPWorker
from rtk_cors_client.ui import MAIN_TABS
from rtk_cors_client.ui.tabs.stats_tab import LiveStatsPanel

TAB_TITLES = {
    "connection": "🔌 Подключение",
    "collection": "🎯 Сбор данных",
    "cs": "🌍 Система координат",
    "log": "📋 Лог событий",
    "params": "📊 Параметры системы",
    "stats": "📈 Статистика",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTK CORS Client — v4.0 (модульная архитектура)")
        self.setMinimumSize(1200, 850)

        # Ядро приложения (не Qt) — доступно вкладкам через main_window
        self.config_manager = ConfigManager()
        self.signals = NTRIPSignals()
        self.worker = None
        self.sourcetable_worker = None
        self.mountpoints_data = []

        self._build_ui()
        self._connect_window_signals()

        # Таймер uptime (как в оригинале)
        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(lambda: self.live_stats.tick(self.worker))
        self.uptime_timer.start(1000)

    # ------------------------------------------------------------------
    # Сборка UI из реестра вкладок
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tab_widgets = {}  # key -> экземпляр BaseTab

        for key, class_name, module_path in MAIN_TABS:
            module = importlib.import_module(module_path)
            tab_cls = getattr(module, class_name)
            tab = tab_cls(self.signals, self.config_manager)
            tab.main_window = self
            tab.build()
            self.tab_widgets[key] = tab
            self.tabs.addTab(tab, TAB_TITLES.get(key, key))

        layout.addWidget(self.tabs)

        # Панель live-статистики под вкладками (перенесена из connection-tab оригинала)
        self.live_stats = LiveStatsPanel(self.signals)
        layout.addWidget(self.live_stats)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Статус: Отключено")
        self.status_bar.addWidget(self.status_label)

    def _connect_window_signals(self):
        """Сигналы, относящиеся к самому окну (статус, завершение сбора)."""
        self.signals.status_changed.connect(self.update_status)
        self.signals.collection_complete.connect(self.on_collection_complete)

    # ------------------------------------------------------------------
    # Доступ к «общим» виджетам вкладок (конфиг, таблицы для очистки)
    # ------------------------------------------------------------------
    @property
    def connection_tab(self):
        return self.tab_widgets["connection"]

    @property
    def cs_tab(self):
        return self.tab_widgets["cs"]

    @property
    def collection_tab(self):
        return self.tab_widgets["collection"]

    @property
    def log_tab(self):
        return self.tab_widgets["log"]

    @property
    def params_tab(self):
        return self.tab_widgets["params"]

    @property
    def stats_tab(self):
        return self.tab_widgets["stats"]

    # ------------------------------------------------------------------
    # Действия, делегируемые вкладками
    # ------------------------------------------------------------------
    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.worker = None
            self.connection_tab.on_disconnected()
            return

        self.connection_tab.save_config_to_manager()
        self.config_manager.save()

        # Очистка отображений перед новой сессией
        for tab in self.tab_widgets.values():
            tab.reset()

        self.worker = NTRIPWorker(self.config_manager.config.copy(), self.signals)
        self.worker.start()

    def save_report_now(self):
        if self.worker and self.worker.isRunning():
            path = self.worker._save_final_report()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Успех", f"Отчёт сохранён:\n{path}")
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Внимание", "Подключение не активно")

    def fetch_sourcetable(self):
        self.connection_tab.save_config_to_manager()
        self.connection_tab.btn_fetch_sourcetable.setEnabled(False)
        self.connection_tab.btn_fetch_sourcetable.setText("⏳ Загрузка...")

        self.sourcetable_worker = SourcetableWorker(
            self.config_manager.config.copy(), self.signals
        )
        self.sourcetable_worker.finished.connect(self._on_sourcetable_finished)
        self.sourcetable_worker.start()

    def _on_sourcetable_finished(self):
        btn = self.connection_tab.btn_fetch_sourcetable
        btn.setEnabled(True)
        btn.setText("🔄 Получить список")

    # ------------------------------------------------------------------
    # Реакция на сигналы (окно)
    # ------------------------------------------------------------------
    def update_status(self, status: str):
        self.status_label.setText(f"Статус: {status}")

    def on_collection_complete(self, progress):
        self.signals.log_message.emit("🎉 Сбор данных завершён", "success")
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Сбор завершён",
            "Все обязательные данные собраны.\nОтчёт сохранён в папку data/",
        )
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        self.worker = None
        self.connection_tab.on_disconnected()

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        if self.sourcetable_worker and self.sourcetable_worker.isRunning():
            self.sourcetable_worker.wait()
        event.accept()
