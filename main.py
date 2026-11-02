#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Корневая точка входа нового модульного приложения.

    python main.py

Старый монолитный вариант доступен отдельно: python rtk4.py (legacy).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rtk_cors_client.app import main  # noqa: E402

if __name__ == "__main__":
    main()
