# -*- coding: utf-8 -*-
"""Декодер chunked transfer encoding (NTRIP v2)."""
import logging

logger = logging.getLogger(__name__)


class ChunkedTransferDecoder:
    """Извлекает полезную нагрузку из HTTP chunked-потока.

    Логика перенесена из NTRIPWorker.process_chunked_data() монолитного rtk4.py.
    """

    def __init__(self, on_terminal_chunk=None):
        self.buffer = bytearray()
        # Колбэк вызывается при получении терминального chunk (0),
        # например для записи в лог.
        self._on_terminal_chunk = on_terminal_chunk

    def feed(self, data: bytes) -> bytes:
        """Добавляет данные в буфер и возвращает все полностью принятые chunks."""
        self.buffer.extend(data)
        extracted = bytearray()

        while True:
            crlf_pos = self.buffer.find(b"\r\n")
            if crlf_pos == -1:
                break

            size_str = self.buffer[:crlf_pos].decode('ascii', errors='ignore').strip()

            if ';' in size_str:
                size_str = size_str.split(';')[0].strip()

            try:
                chunk_size = int(size_str, 16)
            except ValueError:
                self.buffer = self.buffer[crlf_pos + 2:]
                continue

            if chunk_size == 0:
                if self._on_terminal_chunk:
                    self._on_terminal_chunk()
                else:
                    logger.info("Сервер отправил терминальный chunk (0)")
                break

            data_start = crlf_pos + 2
            data_end = data_start + chunk_size
            total_needed = data_end + 2

            if len(self.buffer) < total_needed:
                break

            extracted.extend(self.buffer[data_start:data_end])
            self.buffer = self.buffer[total_needed:]

        return bytes(extracted)

    def reset(self):
        self.buffer = bytearray()
