# -*- coding: utf-8 -*-
"""Вкладка «Система координат»: таблица параметров СК (1021-1027, 1300/1302).

Перенесено из MainWindow.create_cs_tab() / on_cs_message_received() /
update_cs_status() / show_cs_diagnostic() / export_cs_to_json() /
show_cs_help() монолитного rtk4.py.
"""
import json
from datetime import datetime
from pathlib import Path

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)

from rtk_cors_client.config.constants import COORDINATE_SYSTEM_MESSAGES
from rtk_cors_client.ui.base_tab import BaseTab


class CoordinateSystemTab(BaseTab):
    """Отображение и экспорт параметров системы координат из RTCM-сообщений."""

    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # --- Статус ---
        group_status = QGroupBox("📊 Статус сообщений СК")
        status_layout = QVBoxLayout()
        self.lbl_cs_status = QLabel(
            "Подключитесь к серверу для получения параметров СК"
        )
        self.lbl_cs_status.setWordWrap(True)
        self.lbl_cs_status.setFont(QFont("Consolas", 10))
        status_layout.addWidget(self.lbl_cs_status)
        group_status.setLayout(status_layout)
        layout.addWidget(group_status)

        # --- Таблица параметров ---
        group_params = QGroupBox("🌍 Параметры системы координат")
        params_layout = QVBoxLayout()
        self.table_cs = QTableWidget()
        self.table_cs.setColumnCount(4)
        self.table_cs.setHorizontalHeaderLabels(
            ["ID", "Название", "Параметр", "Значение"]
        )
        self.table_cs.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_cs.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        params_layout.addWidget(self.table_cs)
        group_params.setLayout(params_layout)
        layout.addWidget(group_params)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()

        btn_clear = QPushButton("🗑️ Очистить")
        btn_clear.clicked.connect(lambda: self.table_cs.setRowCount(0))
        btn_layout.addWidget(btn_clear)

        btn_export = QPushButton("💾 Экспорт в JSON")
        btn_export.clicked.connect(self.export_cs_to_json)
        btn_layout.addWidget(btn_export)

        btn_help = QPushButton("ℹ️ Справка по сообщениям")
        btn_help.clicked.connect(self.show_cs_help)
        btn_layout.addWidget(btn_help)

        layout.addLayout(btn_layout)
        return widget

    def connect_signals(self):
        self.signals.cs_message_received.connect(self.on_cs_message_received)
        # Обновляем статус по мере поступления любых данных
        self.signals.collection_progress.connect(lambda _p: self.update_cs_status())

    # ------------------------------------------------------------------
    def on_cs_message_received(self, msg_id: int, params: dict):
        """Заполнение таблицы параметрами полученного сообщения СК."""
        if msg_id not in COORDINATE_SYSTEM_MESSAGES:
            return

        cs_info = COORDINATE_SYSTEM_MESSAGES[msg_id]

        # Очистка старых строк для этого msg_id
        rows_to_remove = []
        for row in range(self.table_cs.rowCount()):
            item = self.table_cs.item(row, 0)
            if item and item.text() == str(msg_id):
                rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self.table_cs.removeRow(row)

        if not params:
            # pyrtcm не разобрал — добавляем запись о сырых данных
            row = self.table_cs.rowCount()
            self.table_cs.insertRow(row)
            self.table_cs.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_cs.setItem(row, 1, QTableWidgetItem(cs_info["name"]))
            self.table_cs.setItem(row, 2, QTableWidgetItem("(сырые данные)"))
            self.table_cs.setItem(
                row, 3, QTableWidgetItem("См. финальный отчёт (raw_hex)")
            )
            self.update_cs_status()
            return

        for key, value in params.items():
            row = self.table_cs.rowCount()
            self.table_cs.insertRow(row)
            self.table_cs.setItem(row, 0, QTableWidgetItem(str(msg_id)))
            self.table_cs.setItem(row, 1, QTableWidgetItem(cs_info["name"]))
            field_name = cs_info["fields"].get(key, key)
            self.table_cs.setItem(row, 2, QTableWidgetItem(f"{key}: {field_name}"))
            self.table_cs.setItem(row, 3, QTableWidgetItem(str(value)))

        self.update_cs_status()

    # ------------------------------------------------------------------
    def _collected_ids(self) -> set:
        worker = getattr(self.main_window, "worker", None) if self.main_window else None
        if worker is None:
            return set()
        return set(worker.collected_params.keys())

    def update_cs_status(self):
        """Текстовый статус: какие СК-сообщения получены, какие ожидаются."""
        collected_ids = self._collected_ids()
        if not collected_ids and self.main_window is not None \
                and getattr(self.main_window, "worker", None) is None:
            return

        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = collected_ids & cs_ids
        cs_missing = cs_ids - collected_ids

        if not cs_collected:
            self.lbl_cs_status.setText(
                "⏳ Сообщения СК (1021-1027, 1300, 1302) пока не получены.\n"
                "Это нормально — провайдер может слать их редко (раз в 1-10 минут) "
                "или только при нахождении в зоне МСК."
            )
            self.lbl_cs_status.setStyleSheet("color: orange;")
        else:
            received_names = [
                f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})"
                for mid in sorted(cs_collected)
            ]
            missing_names = [
                f"{mid} ({COORDINATE_SYSTEM_MESSAGES[mid]['name']})"
                for mid in sorted(cs_missing)
            ]
            text = f"✅ Получено: {', '.join(received_names)}\n\n"
            if missing_names:
                text += f"⏳ Ожидается: {', '.join(missing_names)}"
            else:
                text += "🎉 Все сообщения СК получены!"
            self.lbl_cs_status.setText(text)
            self.lbl_cs_status.setStyleSheet(
                "color: green;" if not cs_missing else "color: orange;"
            )

    # ------------------------------------------------------------------
    def show_cs_diagnostic(self):
        """Диагностика отсутствия сообщений СК (кнопка на вкладке сбора)."""
        if self.main_window is None or self.main_window.worker is None:
            QMessageBox.information(
                self, "Диагностика", "Подключитесь к серверу для диагностики."
            )
            return

        worker = self.main_window.worker
        collected_ids = set(worker.collected_params.keys())
        cs_ids = set(COORDINATE_SYSTEM_MESSAGES.keys())
        cs_collected = collected_ids & cs_ids
        cs_missing = cs_ids - collected_ids

        cfg = self.config_manager.config
        text = "=== ДИАГНОСТИКА СООБЩЕНИЙ СК ===\n\n"
        text += "📍 Координаты ровера:\n"
        text += f"   Широта: {cfg['base_lat']:.6f}°\n"
        text += f"   Долгота: {cfg['base_lon']:.6f}°\n\n"

        text += f"✅ Получено ({len(cs_collected)}):\n"
        for mid in sorted(cs_collected):
            count = worker.collected_params[mid]["count"]
            text += (
                f"   • {mid} — {COORDINATE_SYSTEM_MESSAGES[mid]['name']} "
                f"(получено {count} раз)\n"
            )

        text += f"\n⏳ Ожидается ({len(cs_missing)}):\n"
        for mid in sorted(cs_missing):
            text += f"   • {mid} — {COORDINATE_SYSTEM_MESSAGES[mid]['name']}\n"

        text += "\n💡 Возможные причины отсутствия:\n"
        text += "   1. Провайдер шлёт их редко (раз в 5-10 минут)\n"
        text += "   2. Координаты вне зоны действия МСК\n"
        text += "   3. Провайдер не передаёт параметры СК через RTCM\n"
        text += "   4. Параметры СК в проприетарных сообщениях\n"

        QMessageBox.information(self, "Диагностика СК", text)

    def export_cs_to_json(self):
        """Экспорт параметров СК в отдельный JSON-файл."""
        if self.main_window is None or self.main_window.worker is None:
            QMessageBox.warning(self, "Внимание", "Нет данных для экспорта")
            return

        cs_data = self.main_window.worker._extract_coordinate_system()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить параметры СК",
            f"cs_params_{timestamp}.json",
            "JSON Files (*.json)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(cs_data, f, indent=2, ensure_ascii=False, default=str)
                QMessageBox.information(
                    self, "Успех", f"Параметры СК сохранены:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось сохранить:\n{e}"
                )

    def show_cs_help(self):
        """Справка по сообщениям СК."""
        text = "=== СООБЩЕНИЯ СИСТЕМЫ КООРДИНАТ (RTCM 3.1+) ===\n\n"
        for mid in [1021, 1022, 1023, 1024, 1025, 1026, 1027, 1300, 1302]:
            info = COORDINATE_SYSTEM_MESSAGES[mid]
            text += f"📌 {mid}: {info['name']}\n"
            text += f"   {info['description']}\n\n"
        text += "\n💡 Примечание:\n"
        text += ("Сообщения 1021-1027 передают параметры перехода из глобальных\n"
                 "геоцентрических СК (ITRF/WGS84) в локальные (МСК).\n"
                 "Сообщения 1300/1302 передают названия исходной и целевой СК.")
        QMessageBox.information(self, "Справка по сообщениям СК", text)

    def reset(self):
        self.table_cs.setRowCount(0)
        self.lbl_cs_status.setText(
            "Подключитесь к серверу для получения параметров СК"
        )
        self.lbl_cs_status.setStyleSheet("")


def build_help_text() -> str:
    """Текст справки (доступен без GUI — для тестов/консольных утилит)."""
    lines = []
    for mid in [1021, 1022, 1023, 1024, 1025, 1026, 1027, 1300, 1302]:
        info = COORDINATE_SYSTEM_MESSAGES[mid]
        lines.append(f"{mid}: {info['name']} — {info['description']}")
    return "\n".join(lines)
