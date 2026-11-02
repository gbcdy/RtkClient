# -*- coding: utf-8 -*-
"""Менеджер конфигурации (загрузка/сохранение JSON)."""
import json
from pathlib import Path

from .constants import CONFIG_FILE, DEFAULT_CONFIG


class ConfigManager:
    """Чтение/запись конфигурации приложения в JSON-файле."""

    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = Path(config_path)
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                return True
            except Exception as e:
                print(f"Ошибка загрузки конфига: {e}")
                return False
        return False

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфига: {e}")
            return False

    def update(self, data: dict):
        self.config.update(data)

    def get(self, key, default=None):
        return self.config.get(key, default)
