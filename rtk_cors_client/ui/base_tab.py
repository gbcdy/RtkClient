# -*- coding: utf-8 -*-
"""Базовый класс вкладки GUI.

Контракт для всех вкладок (см. architecture.md, раздел 7):
  * __init__(signals, config_manager, parent) — получает только сигналы
    и конфиг, прямых обращений к воркеру нет;
  * create_widget() -> QWidget — конструирование содержимого;
  * connect_signals() — подписка на NTRIPSignals внутри себя;
  * on_connected()/on_disconnected() — реакция на смену статуса;
  * reset() — очистка данных (при новом подключении).
"""
from PyQt5.QtWidgets import QWidget


class BaseTab(QWidget):
    #: Главное окно назначается MainWindow при создании вкладки
    #: (делегирование действий: подключение, отчёт, sourcetable).
    main_window = None

    def __init__(self, signals, config_manager, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.config_manager = config_manager
        self._widget = None

    # ------------------------------------------------------------------
    def create_widget(self) -> QWidget:
        """Должен вернуть заполненный QWidget. Переопределяется в потомке."""
        raise NotImplementedError

    def connect_signals(self):
        """Подписка на сигналы. По умолчанию — ничего."""

    def on_connected(self):
        """Вызывается при успешном подключении."""

    def on_disconnected(self):
        """Вызывается при отключении."""

    def reset(self):
        """Очистка накопленного отображения."""

    def build(self) -> "BaseTab":
        """Фабричный вызов: создать содержимое и подключить сигналы."""
        layout_content = self.create_widget()
        if layout_content is not None and layout_content.parent() is None:
            from PyQt5.QtWidgets import QVBoxLayout
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(layout_content)
        self.connect_signals()
        return self
