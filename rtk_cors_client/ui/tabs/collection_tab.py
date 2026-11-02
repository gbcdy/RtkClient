# -*- coding: utf-8 -*-
"""Вкладка «Сбор данных»: прогресс сбора целевых RTCM-сообщений."""
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rtk_cors_client.config.constants import (
    COORDINATE_SYSTEM_MESSAGES,
    KNOWN_RTCM_MESSAGES,
    TARGET_MESSAGES,
)
from rtk_cors_client.ui.base_tab import BaseTab


class CollectionTab(BaseTab):
    """Индикаторы прогресса сбора и список собранных сообщений."""

    def create_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # --- Прогресс сбора ---
        group_progress = QGroupBox("📊 Прогресс сбора данных")
        progress_layout = QGridLayout()

        row = 0
        progress_layout.addWidget(QLabel("<b>Координаты базы (1005/1006):</b>"), row, 0)
        self.lbl_base_coords = QLabel("⏳ Ожидание...")
        self.lbl_base_coords.setStyleSheet("color: orange;")
        progress_layout.addWidget(self.lbl_base_coords, row, 1)

        row += 1
        progress_layout.addWidget(QLabel("<b>Антенна (1007/1008/1033):</b>"), row, 0)
        self.lbl_antenna = QLabel("⏳ Ожидание...")
        self.lbl_antenna.setStyleSheet("color: orange;")
        progress_layout.addWidget(self.lbl_antenna, row, 1)

        row += 1
        progress_layout.addWidget(QLabel("<b>⭐ Система координат (1021-1027):</b>"), row, 0)
        self.lbl_cs_params = QLabel("⏳ Ожидание...")
        self.lbl_cs_params.setStyleSheet("color: orange;")
        progress_layout.addWidget(self.lbl_cs_params, row, 1)

        row += 1
        progress_layout.addWidget(QLabel("<b>Названия СК (1300/1302):</b>"), row, 0)
        self.lbl_crs_names = QLabel("⏳ Ожидание (опционально)")
        self.lbl_crs_names.setStyleSheet("color: gray;")
        progress_layout.addWidget(self.lbl_crs_names, row, 1)

        row += 1
        progress_layout.addWidget(QLabel("<b>Геоид/проприетарные:</b>"), row, 0)
        self.lbl_geoid = QLabel("⏳ Ожидание (опционально)")
        self.lbl_geoid.setStyleSheet("color: gray;")
        progress_layout.addWidget(self.lbl_geoid, row, 1)

        row += 1
        progress_layout.addWidget(QLabel("<b>Всего типов собрано:</b>"), row, 0)
        self.lbl_total_types = QLabel("0")
        self.lbl_total_types.setStyleSheet("font-weight: bold; color: blue;")
        progress_layout.addWidget(self.lbl_total_types, row, 1)

        group_progress.setLayout(progress_layout)
        layout.addWidget(group_progress)

        # --- Список собранных ---
        group_list = QGroupBox("📋 Собранные сообщения")
        list_layout = QVBoxLayout()
        self.text_collected = QTextEdit()
        self.text_collected.setReadOnly(True)
        self.text_collected.setFont(QFont("Consolas", 9))
        list_layout.addWidget(self.text_collected)
        group_list.setLayout(list_layout)
        layout.addWidget(group_list)

        return widget

    def connect_signals(self):
        self.signals.collection_progress.connect(self.update_progress)
        self.signals.collection_complete.connect(self._on_complete)

    def _on_complete(self, progress: dict):
        self.append_note("✅ Сбор завершён — все обязательные данные получены.")

    def append_note(self, text: str):
        self.text_collected.append(text)

    def update_progress(self, progress: dict):
        # Координаты базы
        if progress["has_base_coords"]:
            self.lbl_base_coords.setText("✅ Получено")
            self.lbl_base_coords.setStyleSheet("color: green;")
        else:
            self.lbl_base_coords.setText("⏳ Ожидание...")
            self.lbl_base_coords.setStyleSheet("color: orange;")

        # Антенна
        if progress["has_antenna"]:
            self.lbl_antenna.setText("✅ Получено")
            self.lbl_antenna.setStyleSheet("color: green;")
        else:
            self.lbl_antenna.setText("⏳ Ожидание...")
            self.lbl_antenna.setStyleSheet("color: orange;")

        # Параметры СК
        cs_collected = progress.get("cs_collected", [])
        if cs_collected:
            self.lbl_cs_params.setText(f"✅ Получено ({len(cs_collected)}): {cs_collected}")
            self.lbl_cs_params.setStyleSheet("color: green;")
        else:
            self.lbl_cs_params.setText("⏳ Ожидание...")
            self.lbl_cs_params.setStyleSheet("color: orange;")

        # Названия CRS
        has_1300 = 1300 in cs_collected
        has_1302 = 1302 in cs_collected
        if has_1300 or has_1302:
            parts = []
            if has_1300:
                parts.append("source")
            if has_1302:
                parts.append("target")
            self.lbl_crs_names.setText(f"✅ Получено: {', '.join(parts)}")
            self.lbl_crs_names.setStyleSheet("color: green;")
        else:
            self.lbl_crs_names.setText("⏳ Ожидание (опционально)")
            self.lbl_crs_names.setStyleSheet("color: gray;")

        # Геоид / проприетарные
        if progress["has_proprietary"]:
            self.lbl_geoid.setText(
                f"✅ Получено ({len(progress['proprietary_collected'])} шт)"
            )
            self.lbl_geoid.setStyleSheet("color: green;")
        else:
            self.lbl_geoid.setText("⏳ Ожидание (опционально)")
            self.lbl_geoid.setStyleSheet("color: gray;")

        # Всего типов
        self.lbl_total_types.setText(f"{progress['total_collected']}")

        # Список собранных (маркеры: 🌍 — СК, 🎯 — целевое)
        counts = {}
        if self.main_window is not None:
            worker = self.main_window.worker
            if worker is not None:
                for mid, entry in worker.collected_params.items():
                    counts[mid] = entry.get("count", 0)

        self.text_collected.clear()
        for mid in progress["collected_ids"]:
            name = KNOWN_RTCM_MESSAGES.get(mid, f"Unknown_{mid}")
            count = counts.get(mid, 0)
            is_target = mid in TARGET_MESSAGES
            is_cs = mid in COORDINATE_SYSTEM_MESSAGES
            marker = "🌍" if is_cs else ("🎯" if is_target else "  ")
            self.text_collected.append(f"{marker} ID {mid}: {name} (получено: {count} раз)")

    def reset(self):
        self.text_collected.clear()
        for lbl in (self.lbl_base_coords, self.lbl_antenna, self.lbl_cs_params):
            lbl.setText("⏳ Ожидание...")
            lbl.setStyleSheet("color: orange;")
        self.lbl_crs_names.setText("⏳ Ожидание (опционально)")
        self.lbl_crs_names.setStyleSheet("color: gray;")
        self.lbl_geoid.setText("⏳ Ожидание (опционально)")
        self.lbl_geoid.setStyleSheet("color: gray;")
        self.lbl_total_types.setText("0")
