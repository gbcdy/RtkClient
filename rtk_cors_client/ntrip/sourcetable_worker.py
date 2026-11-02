# -*- coding: utf-8 -*-
"""Фоновое получение SOURCETABLE (QThread-обёртка, логика вне Qt)."""
import socket

from PyQt5.QtCore import QThread

from rtk_cors_client.config.constants import USER_AGENT
from rtk_cors_client.config.sourcetable import SourcetableParser


def fetch_sourcetable(config: dict, log_fn=None) -> list:
    """Синхронно запрашивает SOURCETABLE у NTRIP-сервера.

    Возвращает список маунтпоинтов (dict). Бросает исключения при ошибках сети.
    """
    server = config["ntrip_server"]
    port = config["ntrip_port"]
    login = config["username"]
    password = config["password"]

    def log(msg, level="info"):
        if log_fn:
            log_fn(msg, level)

    log(f"📋 Запрос списка маунтпоинтов с {server}:{port}")

    import base64
    credentials = base64.b64encode(f"{login}:{password}".encode()).decode()

    request = (
        f"GET /sourcetable HTTP/1.1\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
        f"Authorization: Basic {credentials}\r\n"
        f"Accept: */*\r\n"
        f"Host: {server}:{port}\r\n"
        f"Ntrip-Version: Ntrip/2.0\r\n"
        f"Connection: close\r\n\r\n"
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((server, port))
        sock.send(request.encode())

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

    header_end = response.find(b"\r\n\r\n")
    body = response[header_end + 4:].decode('utf-8', errors='ignore')

    mountpoints = SourcetableParser.parse(body)
    log(f"✅ Получено {len(mountpoints)} маунтпоинтов", "success")
    return mountpoints


class SourcetableWorker(QThread):
    """QThread-обёртка над fetch_sourcetable (как в оригинале)."""

    def __init__(self, config: dict, signals):
        super().__init__()
        self.config = config
        self.signals = signals

    def run(self):
        try:
            mountpoints = fetch_sourcetable(
                self.config,
                log_fn=lambda m, l="info": self.signals.log_message.emit(m, l),
            )
            self.signals.sourcetable_received.emit(mountpoints)
        except Exception as e:
            self.signals.log_message.emit(f"❌ Ошибка получения sourcetable: {e}", "error")
