# RTK CORS Client — Архитектура проекта

## 1. Общее описание

RTK CORS Client — десктопное приложение на Python/PyQt5 для подключения к NTRIP-кастерам,
получения RTCM 3.x потока, парсинга параметров системы координат и сохранения данных
в форматы различных производителей GNSS-оборудования.

**Версия архитектуры:** 2.0
**Дата:** 2026-11-02
**Статус:** Рефакторинг из монолитного скрипта

## 2. Цели архитектуры

- Разделить монолитный скрипт (~2500 строк) на независимые модули
- Обеспечить расширяемость парсеров RTCM-сообщений
- Поддержать множественные форматы экспорта (JSON + форматы производителей)
- Облегчить тестирование отдельных компонентов
- Сохранить обратную совместимость с текущей конфигурацией

## 3. Слои архитектуры
┌─────────────────────────────────────────────────────────┐
│ UI Layer (PyQt5) │
│ MainWindow → Tabs → Widgets │
├─────────────────────────────────────────────────────────┤
│ Application Layer (Coordinators) │
│ SessionManager, CollectionCoordinator │
├─────────────────────────────────────────────────────────┤
│ Domain Layer │
│ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│ │ NTRIP │ │ RTCM │ │ Exporters │ │
│ │ Client │ │ Parsers │ │ (JSON, Vendor) │ │
│ │ │ │+Collect. │ │ │ │
│ └──────────┘ └──────────┘ └────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Infrastructure Layer │
│ Config, Logging, CRC24Q, Converters, NMEA │
└─────────────────────────────────────────────────────────┘
## 4. Модули и их ответственность

### 4.1. `config/` — Конфигурация
- `constants.py` — все словари RTCM-сообщений (KNOWN_RTCM_MESSAGES,
  COORDINATE_SYSTEM_MESSAGES, PROPRIETARY_TARGETS, TARGET_MESSAGES)
- `settings.py` — ConfigManager, DEFAULT_CONFIG, загрузка/сохранение JSON
- `sourcetable.py` — SourcetableParser (парсинг NTRIP SOURCETABLE)

### 4.2. `ntrip/` — Сетевой слой
- `client.py` — NTRIPWorker: только TCP-соединение, отправка GGA,
  приём байтов. НЕ содержит парсинг RTCM.
- `chunked.py` — ChunkedTransferDecoder для NTRIP v2
- `crc24q.py` — CRC24Q (табличный, полином 0x1864CFB)
- `signals.py` — NTRIPSignals (Qt-сигналы для связи с UI)

### 4.3. `rtcm/` — Парсинг и сбор данных
- `parser.py` — RTCMFrameParser: поиск синхронизации 0xD3, проверка CRC,
  извлечение msg_id. Возвращает сырые фреймы.
- `messages.py` — RTCMMessageDecoder: обёртка над pyrtcm, fallback-парсинг
- `cs_messages.py` — специализированная обработка 1021-1027, 1300, 1302
- `collectors/` — накопление статистики по категориям:
  - `base.py` — BaseCollector (абстрактный класс)
  - `base_station.py` — 1005/1006 (координаты базы)
  - `antenna.py` — 1007/1008/1033 (антенна/приёмник)
  - `coordinate_system.py` — 1021-1027, 1300/1302 (СК)
  - `proprietary.py` — проприетарные сообщения (4001-4095)

**Паттерн Registry:** каждый коллектор регистрируется по списку msg_id.
Парсер при получении сообщения находит нужный коллектор и передаёт данные.

### 4.4. `converters/` — Преобразования координат
- `coordinates.py` — ECEF ↔ WGS84, геодезические преобразования

### 4.5. `exporters/` — Экспорт данных
- `base.py` — BaseExporter (абстрактный класс)
- `json_report.py` — финальный JSON-отчёт (текущая логика)
- `raw_rtcm.py` — сырой RTCM-поток
- `vendor/` — форматы производителей:
  - `trimble.py` — Trimble .dat (T00/T01/T02)
  - `septentrio.py` — Septentrio .sbf
  - `leica.py` — Leica .id/.obs
  - `novatel.py` — NovAtel .spn

### 4.6. `ui/` — Интерфейс
- `main_window.py` — только каркас, регистрация вкладок
- `tabs/` — каждая вкладка в отдельном файле
- `widgets/` — переиспользуемые виджеты (LiveStats, LastMessage)

### 4.7. `utils/` — Утилиты
- `nmea.py` — генерация NMEA GGA (ручная, без pynmea2)
- `logging.py` — файловое логирование

## 5. Потоки данных
TCP Socket
│
▼
NTRIPWorker (ntrip/client.py)
│ raw bytes
▼
ChunkedTransferDecoder (если NTRIP v2 chunked)
│ clean RTCM bytes
▼
RTCMFrameParser (rtcm/parser.py)
│ validated frames (CRC OK)
▼
RTCMMessageDecoder (rtcm/messages.py)
│ parsed messages
▼
CollectorRegistry → BaseCollector (rtcm/collectors/)
│ accumulated data
▼
Exporters (exporters/)
│ files
▼
Disk (data/, logs/)

## 6. Ключевые классы и интерфейсы

### BaseCollector
python
class BaseCollector(ABC):
@abstractmethod
def supported_messages(self) -> list[int]: ...
@abstractmethod
def collect(self, msg_id: int, params: dict, raw: bytes) -> None: ...

@abstractmethod
def get_status(self) -> dict: ...

@abstractmethod
def export(self) -> dict: ...

### BaseExporter
```python
class BaseExporter(ABC):
    @abstractmethod
    def export(self, data: dict, output_path: Path) -> None: .

7. Зависимости
Обязательные:
Python 3.10+
PyQt5 (UI)
numpy (математика, шум)
pyrtcm (парсинг RTCM)
Опциональные (для будущих доработок):
pynmea2 (альтернативный NMEA-парсер)
geographiclib (точные геодезические преобразования)
pyproj (проекции СК)
8. План рефакторинга (итерации)
Итерация 1 — Выделение базовых модулей
Создать структуру каталогов
Вынести config/ (constants, settings, sourcetable)
Вынести ntrip/crc24q.py, ntrip/chunked.py, ntrip/signals.py
Вынести utils/nmea.py, utils/logging.py
Вынести converters/coordinates.py
Проверить работоспособность
Итерация 2 — Разделение NTRIPWorker
Создать rtcm/parser.py (RTCMFrameParser)
Создать rtcm/messages.py (RTCMMessageDecoder)
Вынести сетевую часть в ntrip/client.py
Связать через сигналы
Итерация 3 — Коллекторы
Создать BaseCollector и CollectorRegistry
Реализовать коллекторы по категориям
Перенести методы _extract_* в соответствующие коллекторы
Обновить UI для работы с коллекторами
Итерация 4 — Разделение UI
Вынести каждую вкладку в отдельный файл
Создать переиспользуемые виджеты
Обновить MainWindow
Итерация 5 — Экспорт в форматы производителей
Реализовать BaseExporter
Реализовать JSON и raw RTCM экспортеры
Добавить заглушки для vendor-форматов
9. Текущие известные проблемы
Сообщения 1021-1027 не приходят — возможно, провайдер шлёт их редко
или только при нахождении в зоне МСК. Требуется диагностика.
Проприетарные сообщения 3376, 3539, 3582 — возможно, это
перепакованные сообщения СК. Требуется анализ HEX-дампов.
pyrtcm не поддерживает 1300/1302 — нужен fallback-парсер.
10. Будущие доработки
10.1. Парсинг форматов сообщений
Расширить поддержку проприетарных сообщений (4001-4095)
Реализовать собственный парсер для 1300/1302
Добавить валидацию полей по спецификациям RTCM 3.2/3.3
10.2. Накопление статистики
Статистика по времени прихода каждого типа сообщений
Гистограммы интервалов
Детектор аномалий (пропуски, дубликаты)
Экспорт статистики в CSV/Excel
10.3. Форматы производителей
Trimble .dat (T00 — base position, T01 — observations, T02 — ephemeris)
Septentrio .sbf (SBF blocks)
Leica .id/.obs
NovAtel .spn
RINEX 3.x (навигационные и наблюдательные файлы)
10.4. Доработки интерфейса
Карта с позицией ровера (folium / QtLocation)
График качества решения (Fixed/Float/Single)
Визуализация параметров СК (таблицы, графики невязок)
Темная тема
Мультиязычность (RU/EN)
10.5. Дополнительные возможности
Постобработка через RTKLIB (интеграция)
Автоматический выбор маунтпоинта по координатам
Поддержка нескольких одновременных подключений
Экспорт в GeoJSON / KML

