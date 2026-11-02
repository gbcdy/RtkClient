# -*- coding: utf-8 -*-
"""Вкладка «Лог событий»: цветной лог + запись в файл logs/session_YYYYMMDD.log.

Перенесено из MainWindow.create_log_tab() / append_log() монолитного rtk4.py.
"""
from datetime import datetime

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rtk_cors_client.ui.base_tab import BaseTab
from rtk_cors_client.utils.logging import format_log_message, write_log_line


class LogTab(BaseTab):
    """Отображение журнала событий подключения/сбора."""

    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_log)

        btn_clear = QPushButton("🗑️ Очистить лог")
        btn_clear.clicked.connect(self.text_log.clear)
        layout.addWidget(btn_clear)

        return widget

    def connect_signals(self):
        self.signals.log_message.connect(self.append_log)

    # ------------------------------------------------------------------
    def append_log(self, message: str, level: str = "info"):
        """Добавить строку в GUI-лог (с цветом) и в файл суточного лога."""
        self.text_log.append(format_log_message(message, level))
        write_log_line(message)

    def reset(self):
        pass  # лог сохраняем между сессиями — очистка только кнопкой
