# -*- coding: utf-8 -*-
"""Базовый класс экспортера (паттерн Strategy для форматов вывода)."""
from abc import ABC, abstractmethod
from pathlib import Path


class BaseExporter(ABC):
    """Экспортирует накопленные данные в файл формата ``exporter.name``."""

    #: Короткое имя формата ("json", "raw_rtcm", "trimble_dat", ...)
    name: str = ""

    #: Расширение файла без точки (".json")
    extension: str = ""

    @abstractmethod
    def export(self, data: dict, output_path: Path) -> None:
        """Записывает ``data`` в ``output_path``.

        Бросает исключение при ошибке записи — вызывающий код логирует её.
        """

    def default_filename(self, prefix: str, timestamp: str) -> str:
        ext = self.extension or ""
        return f"{prefix}_{timestamp}{ext}"
