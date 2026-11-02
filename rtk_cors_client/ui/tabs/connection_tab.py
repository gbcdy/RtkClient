# -*- coding: utf-8 -*-
"""Вкладка «Подключение»: сервер, маунтпоинт, учётные данные, кнопки."""
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from rtk_cors_client.ui.base_tab import BaseTab


class ConnectionTab(BaseTab):
    """Управление подключением NTRIP + форма конфигурации (без сбора/СК)."""

    def create_widget(self) -> QWidget:
        widget = QWidget()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)

        # --- NTRIP Сервер ---
        group_server = QGroupBox("NTRIP Сервер")
        server_layout = QGridLayout()

        server_layout.addWidget(QLabel("Сервер:"), 0, 0)
        self.edit_server = QLineEdit()
        server_layout.addWidget(self.edit_server, 0, 1)

        server_layout.addWidget(QLabel("Порт:"), 0, 2)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(2101)
        server_layout.addWidget(self.spin_port, 0, 3)

        server_layout.addWidget(QLabel("Маунтпоинт:"), 1, 0)
        self.combo_mountpoint = QComboBox()
        self.combo_mountpoint.setEditable(True)
        self.combo_mountpoint.setMinimumWidth(200)
        server_layout.addWidget(self.combo_mountpoint, 1, 1)

        self.btn_fetch_sourcetable = QPushButton("🔄 Получить список")
        self.btn_fetch_sourcetable.clicked.connect(self.fetch_sourcetable)
        server_layout.addWidget(self.btn_fetch_sourcetable, 1, 2, 1, 2)

        server_layout.addWidget(QLabel("Логин:"), 2, 0)
        self.edit_username = QLineEdit()
        server_layout.addWidget(self.edit_username, 2, 1)

        server_layout.addWidget(QLabel("Пароль:"), 2, 2)
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        server_layout.addWidget(self.edit_password, 2, 3)

        group_server.setLayout(server_layout)
        layout.addWidget(group_server)

        # --- Координаты базы ---
        group_base = QGroupBox("Координаты базы (для GGA)")
        base_layout = QGridLayout()

        base_layout.addWidget(QLabel("Широта:"), 0, 0)
        self.spin_lat = QDoubleSpinBox()
        self.spin_lat.setRange(-90, 90)
        self.spin_lat.setDecimals(7)
        self.spin_lat.setValue(55.7558)
        base_layout.addWidget(self.spin_lat, 0, 1)

        base_layout.addWidget(QLabel("Долгота:"), 0, 2)
        self.spin_lon = QDoubleSpinBox()
        self.spin_lon.setRange(-180, 180)
        self.spin_lon.setDecimals(7)
        self.spin_lon.setValue(37.6173)
        base_layout.addWidget(self.spin_lon, 0, 3)

        base_layout.addWidget(QLabel("Высота (м):"), 1, 0)
        self.spin_alt = QDoubleSpinBox()
        self.spin_alt.setRange(-500, 10000)
        self.spin_alt.setDecimals(2)
        self.spin_alt.setValue(150.0)
        base_layout.addWidget(self.spin_alt, 1, 1)

        base_layout.addWidget(QLabel("Интервал GGA (с):"), 1, 2)
        self.spin_gga_interval = QSpinBox()
        self.spin_gga_interval.setRange(1, 60)
        self.spin_gga_interval.setValue(2)
        base_layout.addWidget(self.spin_gga_interval, 1, 3)

        base_layout.addWidget(QLabel("Шум координат (°):"), 2, 0)
        self.spin_noise = QDoubleSpinBox()
        self.spin_noise.setRange(0, 0.001)
        self.spin_noise.setDecimals(7)
        self.spin_noise.setValue(0.00001)
        self.spin_noise.setSingleStep(0.00001)
        base_layout.addWidget(self.spin_noise, 2, 1)

        group_base.setLayout(base_layout)
        layout.addWidget(group_base)

        # --- Управление подключением ---
        group_conn = QGroupBox("Управление")
        conn_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.btn_connect = QPushButton("▶️ Подключить")
        self.btn_connect.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
        )
        self.btn_connect.clicked.connect(self.toggle_connection)
        btn_row.addWidget(self.btn_connect)

        self.btn_save_report = QPushButton("💾 Сохранить отчёт")
        self.btn_save_report.setEnabled(False)
        self.btn_save_report.clicked.connect(self.save_report_now)
        btn_row.addWidget(self.btn_save_report)

        conn_layout.addLayout(btn_row)

        row2 = QHBoxLayout()
        btn_save_cfg = QPushButton("💾 Сохранить конфигурацию")
        btn_save_cfg.clicked.connect(self.save_config)
        row2.addWidget(btn_save_cfg)

        btn_load_cfg = QPushButton("📂 Загрузить конфигурацию")
        btn_load_cfg.clicked.connect(self.load_config_dialog)
        row2.addWidget(btn_load_cfg)

        conn_layout.addLayout(row2)
        group_conn.setLayout(conn_layout)
        layout.addWidget(group_conn)

        # --- Настройки сохранения ---
        group_save = QGroupBox("Настройки сохранения")
        save_layout = QVBoxLayout()

        self.check_save_raw = QCheckBox("Сохранять сырой RTCM поток (.rtcm)")
        save_layout.addWidget(self.check_save_raw)

        self.check_save_params = QCheckBox("Автосохранение параметров при отключении (.json)")
        save_layout.addWidget(self.check_save_params)

        self.check_log_unknown = QCheckBox("Логировать неизвестные проприетарные сообщения")
        save_layout.addWidget(self.check_log_unknown)

        self.check_auto_stop = QCheckBox(
            "⚡ Автоостановка после сбора всех целевых сообщений (1005/1006 + 1007/1008/1033)"
        )
        save_layout.addWidget(self.check_auto_stop)

        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Таймаут ожидания редких сообщений (сек):"))
        self.spin_auto_timeout = QSpinBox()
        self.spin_auto_timeout.setRange(60, 3600)
        self.spin_auto_timeout.setValue(300)
        timeout_row.addWidget(self.spin_auto_timeout)
        save_layout.addLayout(timeout_row)

        cs_row = QHBoxLayout()
        cs_row.addWidget(QLabel("Предупреждать об отсутствии СК через (сек):"))
        self.spin_cs_timeout = QSpinBox()
        self.spin_cs_timeout.setRange(30, 600)
        self.spin_cs_timeout.setValue(120)
        cs_row.addWidget(self.spin_cs_timeout)
        save_layout.addLayout(cs_row)

        group_save.setLayout(save_layout)
        layout.addWidget(group_save)

        layout.addStretch()
        scroll.setWidget(scroll_widget)

        outer = QVBoxLayout(widget)
        outer.addWidget(scroll)

        self.load_config_to_ui()
        return widget

    # ------------------------------------------------------------------
    # Сигналы вкладки -> главному окну через signals (логирование)
    # ------------------------------------------------------------------
    def connect_signals(self):
        self.signals.sourcetable_received.connect(self.on_sourcetable_received)
        self.signals.status_changed.connect(self._on_status_changed)

    def _on_status_changed(self, status: str):
        if status == "Подключено":
            self.on_connected()
        elif status in ("Отключено", "Ошибка подключения"):
            self.on_disconnected()

    def on_connected(self):
        self.btn_connect.setText("⏹️ Отключить")
        self.btn_connect.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }"
        )
        self.btn_save_report.setEnabled(True)

    def on_disconnected(self):
        self.btn_connect.setText("▶️ Подключить")
        self.btn_connect.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }"
        )
        self.btn_save_report.setEnabled(False)

    # ------------------------------------------------------------------
    # Конфигурация <-> UI
    # ------------------------------------------------------------------
    def load_config_to_ui(self):
        cfg = self.config_manager.config
        self.edit_server.setText(cfg["ntrip_server"])
        self.spin_port.setValue(cfg["ntrip_port"])
        self.combo_mountpoint.setEditText(cfg["mountpoint"])
        self.edit_username.setText(cfg["username"])
        self.edit_password.setText(cfg["password"])
        self.spin_lat.setValue(cfg["base_lat"])
        self.spin_lon.setValue(cfg["base_lon"])
        self.spin_alt.setValue(cfg["base_alt"])
        self.spin_gga_interval.setValue(cfg["gga_interval"])
        self.spin_noise.setValue(cfg["noise_std"])
        self.check_save_raw.setChecked(cfg["save_raw_rtcm"])
        self.check_save_params.setChecked(cfg["save_params_json"])
        self.check_log_unknown.setChecked(cfg["log_unknown_messages"])
        self.check_auto_stop.setChecked(cfg.get("auto_stop_on_complete", False))
        self.spin_auto_timeout.setValue(cfg.get("auto_stop_timeout", 300))
        self.spin_cs_timeout.setValue(cfg.get("cs_messages_timeout", 120))

    def save_config_to_manager(self):
        mountpoint = self.combo_mountpoint.currentData()
        if not mountpoint:
            mountpoint = self.combo_mountpoint.currentText().split(" — ")[0].strip()

        self.config_manager.update({
            "ntrip_server": self.edit_server.text(),
            "ntrip_port": self.spin_port.value(),
            "mountpoint": mountpoint,
            "username": self.edit_username.text(),
            "password": self.edit_password.text(),
            "base_lat": self.spin_lat.value(),
            "base_lon": self.spin_lon.value(),
            "base_alt": self.spin_alt.value(),
            "gga_interval": self.spin_gga_interval.value(),
            "noise_std": self.spin_noise.value(),
            "save_raw_rtcm": self.check_save_raw.isChecked(),
            "save_params_json": self.check_save_params.isChecked(),
            "log_unknown_messages": self.check_log_unknown.isChecked(),
            "auto_stop_on_complete": self.check_auto_stop.isChecked(),
            "auto_stop_timeout": self.spin_auto_timeout.value(),
            "cs_messages_timeout": self.spin_cs_timeout.value(),
        })

    def save_config(self):
        self.save_config_to_manager()
        if self.config_manager.save():
            QMessageBox.information(self, "Успех", "Конфигурация сохранена")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить конфигурацию")

    def load_config_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить конфигурацию", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_manager.config_path = __import__("pathlib").Path(file_path)
            if self.config_manager.load():
                self.load_config_to_ui()
                QMessageBox.information(self, "Успех", "Конфигурация загружена")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось загрузить конфигурацию")

    # ------------------------------------------------------------------
    # Действия (делегирование главному окну, если оно назначено)
    # ------------------------------------------------------------------
    def toggle_connection(self):
        if self.main_window is not None:
            self.main_window.toggle_connection()

    def save_report_now(self):
        if self.main_window is not None:
            self.main_window.save_report_now()

    def fetch_sourcetable(self):
        if self.main_window is not None:
            self.main_window.fetch_sourcetable()

    def on_sourcetable_received(self, mountpoints: list):
        current = self.combo_mountpoint.currentText()
        self.combo_mountpoint.clear()
        for mp in mountpoints:
            display = f"{mp['mountpoint']} — {mp['identifier']} ({mp['format']}, {mp['nav_system']})"
            self.combo_mountpoint.addItem(display, mp['mountpoint'])

        found = False
        for i in range(self.combo_mountpoint.count()):
            if self.combo_mountpoint.itemData(i) == current:
                self.combo_mountpoint.setCurrentIndex(i)
                found = True
                break

        if not found and current:
            self.combo_mountpoint.setEditText(current)

        self.signals.log_message.emit(
            f"📋 Загружено {len(mountpoints)} маунтпоинтов в список", "success"
        )

    def reset(self):
        pass
