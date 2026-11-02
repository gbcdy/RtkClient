# -*- coding: utf-8 -*-
"""Вкладка «Параметры системы»: таблица всех разобранных RTCM-параметров.

Перенесено из MainWindow.create_params_tab() / add_rtcm_param() /
log_unknown_message() монолитного rtk4.py.
"""
from PyQt5.QtWidgets import (
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rtk_cors_client.ui.base_tab import BaseTab


class ParamsTab(BaseTab):
    """Построчный вывод каждого параметра каждого принятого сообщения."""

    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.table_params = QTableWidget()
        self.table_params.setColumnCount(4)
        self.table_params.setHorizontalHeaderLabels(
            ["ID", "Название", "Параметр", "Значение"]
        )
        self.table_params.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_params.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table_params)

        btn_clear = QPushButton("🗑️ Очистить таблицу")
        btn_clear.clicked.connect(lambda: self.table_params.setRowCount(0))
        layout.addWidget(btn_clear)

        return widget

    def connect_signals(self):
        self.signals.rtcm_message.connect(self.add_rtcm_param)
        self.signals.unknown_message.connect(self.log_unknown_message)

    # ------------------------------------------------------------------
    def add_rtcm_param(self, msg_id: int, msg_name: str, params: dict):
        """Добавляет строку на каждый параметр разобранного сообщения."""
        if not params:
            return
        for key, value in params.items():
            row = self.table_params.rowCount()
            self.table_params.insertRow(row)
            self.table_params.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_params.setItem(row, 1, QTableWidgetItem(msg_name))
            self.table_params.setItem(row, 2, QTableWidgetItem(key))
            self.table_params.setItem(row, 3, QTableWidgetItem(str(value)))

        if self.table_params.rowCount() > 0:
            self.table_params.scrollToBottom()

    def log_unknown_message(self, msg_id: int, raw_data: bytes):
        """Неизвестное сообщение — одна строка с HEX-дампом."""
        hex_data = raw_data.hex()
        preview = hex_data[:100] + ("..." if len(hex_data) > 100 else "")
        row = self.table_params.rowCount()
        self.table_params.insertRow(row)
        self.table_params.setItem(row, 0, QTableWidgetItem(str(msg_id)))
        self.table_params.setItem(row, 1, QTableWidgetItem("⚠️ НЕИЗВЕСТНОЕ"))
        self.table_params.setItem(row, 2, QTableWidgetItem(f"{len(raw_data)} байт"))
        self.table_params.setItem(row, 3, QTableWidgetItem(preview))
        self.signals.log_message.emit(
            f"⚠️ НЕИЗВЕСТНОЕ ID={msg_id}, {len(raw_data)} байт, HEX: {preview}",
            "warning",
        )

    def reset(self):
        self.table_params.setRowCount(0)
