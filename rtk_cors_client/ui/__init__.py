# -*- coding: utf-8 -*-
"""Слой представления: вкладки, виджеты, главное окно.

Каждая вкладка — самостоятельный модуль в ui/tabs/ с классом BaseTab:
добавление новой вкладки = новый файл + одна строка в MAIN_TABS ниже.
"""
from .base_tab import BaseTab  # noqa: F401

#: Порядок и состав вкладок главного окна (для доработки — свой класс + строка здесь)
MAIN_TABS = [
    ("connection", "ConnectionTab", "rtk_cors_client.ui.tabs.connection_tab"),
    ("collection", "CollectionTab", "rtk_cors_client.ui.tabs.collection_tab"),
    ("cs", "CoordinateSystemTab", "rtk_cors_client.ui.tabs.cs_tab"),
    ("log", "LogTab", "rtk_cors_client.ui.tabs.log_tab"),
    ("params", "ParamsTab", "rtk_cors_client.ui.tabs.params_tab"),
    ("stats", "StatsTab", "rtk_cors_client.ui.tabs.stats_tab"),
]
