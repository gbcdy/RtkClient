# -*- coding: utf-8 -*-
"""Файловое логирование сессий.

Логика записи session_YYYYMMDD.log перенесена из MainWindow.append_log()
монолитного rtk4.py.
"""
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("logs")


def write_log_line(message: str, logs_dir: Path = LOGS_DIR) -> None:
    """Дописывает строку в суточный лог-файл (best-effort)."""
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"session_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except Exception as e:
        print(f"Ошибка записи в лог-файл: {e}")


def format_log_message(message: str, level: str = "info") -> str:
    """Возвращает HTML-размеченную строку для QTextEdit по уровню."""
    color_map = {
        "info": "black",
        "success": "green",
        "warning": "orange",
        "error": "red",
    }
    color = color_map.get(level, "black")
    return f'<span style="color:{color};">{message}</span>'
