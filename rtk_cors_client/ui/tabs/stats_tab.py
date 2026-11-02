# -*- coding: utf-8 -*-
"""Вкладка «Статистика» + панель live-статистики соединения.

Перенесено из MainWindow.create_stats_tab() / update_stats() /
update_last_message() / update_uptime() монолитного rtk4.py.

StatsTab содержит текстовый отчёт; виджет LiveStatsPanel (uptime, скорость,
байты, последнее сообщение) используется главным окном над вкладками.
"""
from datetime import datetime

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rtk_cors_client.ui.base_tab import BaseTab


def format_stats_text(stats: dict) -> str:
    """Текстовое представление статистики (без Qt — тестируется офлайн)."""
    text = "=== СТАТИСТИКА ПОДКЛЮЧЕНИЯ ===\n\n"
    text += f"Подключено с: {stats.get('connected_since', 'N/A')}\n"
    text += f"Получено байт: {stats.get('bytes_received', 0):,}\n"
    text += f"Отправлено байт: {stats.get('bytes_sent', 0):,}\n"
    text += f"Скорость: {stats.get('bytes_per_sec', 0):.1f} байт/с\n"
    text += f"Обработано сообщений: {stats.get('messages_parsed', 0):,}\n"
    text += f"Валидных (CRC OK): {stats.get('messages_valid', 0):,}\n"
    text += f"CRC ошибок: {stats.get('messages_crc_failed', 0):,}\n"
    text += f"Неизвестных: {stats.get('unknown_messages', 0):,}\n"
    text += f"Отправлено GGA: {stats.get('gga_sent', 0):,}\n"
    text += "\n=== ПОСЛЕДНЕЕ СООБЩЕНИЕ ===\n\n"
    text += f"ID: {stats.get('last_message_id', '—')}\n"
    text += f"Название: {stats.get('last_message_name', '—')}\n"
    text += f"Время: {stats.get('last_message_time', '—')}\n"
    return text


def format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec > 1024:
        return f"{bytes_per_sec / 1024:.1f} КБ/с"
    return f"{bytes_per_sec:.0f} байт/с"


def format_uptime(connected_since_iso: str) -> str:
    """HH:MM:SS с момента подключения ('00:00:00' если не подключены)."""
    if not connected_since_iso:
        return "00:00:00"
    try:
        start = datetime.fromisoformat(connected_since_iso)
        delta = datetime.now() - start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception:
        return "—"


class LiveStatsPanel(QWidget):
    """Панель live-статистики: uptime, скорость, байты, последнее сообщение."""

    def __init__(self, signals, parent=None):
        super().__init__(parent)
        self.signals = signals

        outer = QVBoxLayout(self)

        group_live = QGroupBox("📊 Статистика в реальном времени")
        live = QGridLayout()
        bold = QFont("Consolas", 10, QFont.Bold)

        live.addWidget(QLabel("⏱️ Время работы:"), 0, 0)
        self.lbl_uptime = QLabel("00:00:00")
        self.lbl_uptime.setFont(bold)
        live.addWidget(self.lbl_uptime, 0, 1)

        live.addWidget(QLabel("📥 Скорость:"), 0, 2)
        self.lbl_speed = QLabel("0 байт/с")
        self.lbl_speed.setFont(bold)
        live.addWidget(self.lbl_speed, 0, 3)

        live.addWidget(QLabel("📥 Получено:"), 1, 0)
        self.lbl_bytes_rx = QLabel("0 байт")
        live.addWidget(self.lbl_bytes_rx, 1, 1)

        live.addWidget(QLabel("📤 Отправлено:"), 1, 2)
        self.lbl_bytes_tx = QLabel("0 байт")
        live.addWidget(self.lbl_bytes_tx, 1, 3)

        live.addWidget(QLabel("✅ Валидных:"), 2, 0)
        self.lbl_valid = QLabel("0")
        live.addWidget(self.lbl_valid, 2, 1)

        live.addWidget(QLabel("❌ CRC ошибок:"), 2, 2)
        self.lbl_crc_failed = QLabel("0")
        self.lbl_crc_failed.setStyleSheet("color: red;")
        live.addWidget(self.lbl_crc_failed, 2, 3)

        live.addWidget(QLabel("📨 Сообщений:"), 3, 0)
        self.lbl_messages = QLabel("0")
        live.addWidget(self.lbl_messages, 3, 1)

        live.addWidget(QLabel("📡 GGA отправлено:"), 3, 2)
        self.lbl_gga = QLabel("0")
        live.addWidget(self.lbl_gga, 3, 3)

        group_live.setLayout(live)
        outer.addWidget(group_live)

        group_last = QGroupBox("📬 Последнее принятое сообщение")
        last = QGridLayout()

        last.addWidget(QLabel("ID:"), 0, 0)
        self.lbl_last_id = QLabel("—")
        self.lbl_last_id.setFont(QFont("Consolas", 11, QFont.Bold))
        self.lbl_last_id.setStyleSheet("color: #2196F3;")
        last.addWidget(self.lbl_last_id, 0, 1)

        last.addWidget(QLabel("Название:"), 0, 2)
        self.lbl_last_name = QLabel("—")
        self.lbl_last_name.setFont(QFont("Consolas", 10))
        last.addWidget(self.lbl_last_name, 0, 3)

        last.addWidget(QLabel("Время:"), 1, 0)
        self.lbl_last_time = QLabel("—")
        last.addWidget(self.lbl_last_time, 1, 1)

        last.addWidget(QLabel("Размер:"), 1, 2)
        self.lbl_last_size = QLabel("—")
        last.addWidget(self.lbl_last_size, 1, 3)

        group_last.setLayout(last)
        outer.addWidget(group_last)

        # Подписка
        self.signals.stats_updated.connect(self.update_stats)
        self.signals.last_message_updated.connect(self.update_last_message)

    # ------------------------------------------------------------------
    def update_stats(self, stats: dict):
        self.lbl_bytes_rx.setText(f"{stats.get('bytes_received', 0):,} байт")
        self.lbl_bytes_tx.setText(f"{stats.get('bytes_sent', 0):,} байт")
        self.lbl_messages.setText(f"{stats.get('messages_parsed', 0):,}")
        self.lbl_valid.setText(f"{stats.get('messages_valid', 0):,}")
        self.lbl_crc_failed.setText(f"{stats.get('messages_crc_failed', 0):,}")
        self.lbl_gga.setText(f"{stats.get('gga_sent', 0):,}")
        self.lbl_speed.setText(format_speed(stats.get("bytes_per_sec", 0)))

    def update_last_message(self, msg_info: dict):
        self.lbl_last_id.setText(str(msg_info.get("id", "—")))
        self.lbl_last_name.setText(msg_info.get("name", "—"))
        self.lbl_last_time.setText(msg_info.get("time", "—"))
        self.lbl_last_size.setText(f"{msg_info.get('length', 0)} байт")

    def tick(self, worker):
        """Обновление uptime (вызывается таймером главного окна раз в секунду)."""
        if worker is not None and getattr(worker, "isRunning", lambda: False)():
            self.lbl_uptime.setText(
                format_uptime(worker.stats.get("connected_since"))
            )
        else:
            self.lbl_uptime.setText("00:00:00")


class StatsTab(BaseTab):
    """Развёрнутый текстовый отчёт статистики подключения."""

    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.text_stats = QTextEdit()
        self.text_stats.setReadOnly(True)
        self.text_stats.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_stats)

        return widget

    def connect_signals(self):
        self.signals.stats_updated.connect(self.update_stats)

    def update_stats(self, stats: dict):
        self.text_stats.setPlainText(format_stats_text(stats))

    def reset(self):
        self.text_stats.clear()
