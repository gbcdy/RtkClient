# -*- coding: utf-8 -*-
"""Экспорт сырого RTCM-потока в файл .rtcm.

Потокобезопасный: worker пишет принятые байты через write_bytes(),
закрытие — через close(). Соответствует поведению f_raw из rtk4.py.
"""
from pathlib import Path

from .base import BaseExporter


class RawRTCMExporter(BaseExporter):
    name = "raw_rtcm"
    extension = ".rtcm"

    def __init__(self):
        self._fh = None
        self.path = None

    def open(self, output_path: Path) -> None:
        self.path = Path(output_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "wb")

    def write_bytes(self, data: bytes) -> None:
        if self._fh is not None:
            self._fh.write(data)
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
                self._fh.close()
            finally:
                self._fh = None

    # BaseExporter API — экспорт готовыми данными (для совместимости)
    def export(self, data: dict, output_path: Path) -> Path:
        raw = data.get("raw_bytes", b"") if isinstance(data, dict) else b""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(raw)
        return output_path
