rtk_cors_client/
├── main.py                         # Точка входа
├── config/
│   ├── __init__.py
│   ├── constants.py                # Константы, словари RTCM
│   ├── settings.py                 # ConfigManager, DEFAULT_CONFIG
│   └── sourcetable.py              # SourcetableParser
├── ntrip/
│   ├── __init__.py
│   ├── client.py                   # NTRIPWorker (только сеть)
│   ├── chunked.py                  # Chunked encoding decoder
│   ├── crc24q.py                   # CRC24Q
│   └── signals.py                  # NTRIPSignals
├── rtcm/
│   ├── __init__.py
│   ├── parser.py                   # Парсинг RTCM-фреймов
│   ├── messages.py                 # Словари сообщений
│   ├── cs_messages.py              # Обработка 1021-1027, 1300, 1302
│   └── collectors/                 # Накопление статистики
│       ├── __init__.py
│       ├── base.py                 # Базовый класс коллектора
│       ├── base_station.py         # 1005/1006
│       ├── antenna.py              # 1007/1008/1033
│       ├── coordinate_system.py    # 1021-1027, 1300/1302
│       └── proprietary.py          # Проприетарные сообщения
├── converters/
│   ├── __init__.py
│   └── coordinates.py              # ECEF → WGS84
├── exporters/
│   ├── __init__.py
│   ├── base.py                     # Базовый экспортер
│   ├── json_report.py              # Финальный JSON-отчёт
│   ├── raw_rtcm.py                 # Сырой RTCM
│   └── vendor/                     # Форматы производителей
│       ├── __init__.py
│       ├── trimble.py              # .dat / T00/T01/T02
│       ├── septentrio.py           # .sbf
│       ├── leica.py                # .id / .obs
│       └── novatel.py              # .spn
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # MainWindow (только каркас)
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── connection_tab.py
│   │   ├── collection_tab.py
│   │   ├── cs_tab.py
│   │   ├── log_tab.py
│   │   ├── params_tab.py
│   │   └── stats_tab.py
│   └── widgets/
│       ├── __init__.py
│       ├── live_stats_widget.py
│       └── last_message_widget.py
└── utils/
    ├── __init__.py
    ├── nmea.py                     # Генерация NMEA GGA
    └── logging.py                  # Файловое логирование