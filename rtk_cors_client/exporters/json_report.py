# -*- coding: utf-8 -*-
"""Экспорт финального JSON-отчёта.

Формат отчёта соответствует монолитному rtk4.py (_save_final_report).
"""
import json
from pathlib import Path

from .base import BaseExporter


class JsonReportExporter(BaseExporter):
    name = "json"
    extension = ".json"

    def __init__(self, indent: int = 2):
        self.indent = indent

    def export(self, data: dict, output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=self.indent, ensure_ascii=False, default=str)
        return output_path
