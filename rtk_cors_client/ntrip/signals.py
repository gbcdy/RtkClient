# -*- coding: utf-8 -*-
"""Qt-сигналы сетевого слоя NTRIP (общий контракт «сеть ↔ UI»)."""
from PyQt5.QtCore import QObject, pyqtSignal


class NTRIPSignals(QObject):
    log_message = pyqtSignal(str, str)
    rtcm_message = pyqtSignal(int, str, dict)
    unknown_message = pyqtSignal(int, bytes)
    status_changed = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    sourcetable_received = pyqtSignal(list)
    last_message_updated = pyqtSignal(dict)
    collection_progress = pyqtSignal(dict)
    collection_complete = pyqtSignal(dict)
    cs_message_received = pyqtSignal(int, dict)  # получено сообщение СК
