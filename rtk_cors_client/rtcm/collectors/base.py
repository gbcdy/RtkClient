# -*- coding: utf-8 -*-
"""Базовый класс коллектора и реестр коллекторов (паттерн Registry).

Каждый коллектор регистрируется по списку поддерживаемых msg_id;
при получении сообщения находится нужный коллектор и ему передаются данные.
"""
from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Накопление статистики по категории RTCM-сообщений."""

    @abstractmethod
    def supported_messages(self) -> list:
        """Список msg_id, которые обрабатывает коллектор."""

    @abstractmethod
    def collect(self, msg_id: int, params: dict, raw: bytes) -> None:
        """Обработка одного сообщения."""

    @abstractmethod
    def get_status(self) -> dict:
        """Текущее состояние (что собрано, счётчики)."""

    @abstractmethod
    def export(self) -> dict:
        """Итоговые данные для отчёта."""

    def reset(self):
        """Очистка накопленных данных (по умолчанию — ничего)."""


class CollectorRegistry:
    """Реестр коллекторов: маршрутизация сообщений по msg_id."""

    def __init__(self):
        self._collectors = []
        self._by_msg_id = {}

    def register(self, collector: BaseCollector) -> None:
        self._collectors.append(collector)
        for msg_id in collector.supported_messages():
            self._by_msg_id[msg_id] = collector

    def collectors(self) -> list:
        return list(self._collectors)

    def get(self, msg_id: int):
        """Возвращает коллектор для msg_id или None."""
        return self._by_msg_id.get(msg_id)

    def dispatch(self, msg_id: int, params: dict, raw: bytes) -> bool:
        """Передаёт сообщение подходящему коллектору. True — если найден."""
        collector = self._by_msg_id.get(msg_id)
        if collector is None:
            return False
        collector.collect(msg_id, params, raw)
        return True

    def export_all(self) -> dict:
        """Данные всех коллекторов: {имя_коллектора: export()}."""
        return {type(c).__name__: c.export() for c in self._collectors}

    def status_all(self) -> dict:
        return {type(c).__name__: c.get_status() for c in self._collectors}

    def reset_all(self) -> None:
        for c in self._collectors:
            c.reset()
