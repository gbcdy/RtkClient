# -*- coding: utf-8 -*-
"""Парсер кадров RTCM 3.x: синхронизация 0xD3, длина, проверка CRC24Q.

Логика перенесена из NTRIPWorker.parse_rtcm_buffer() монолитного rtk4.py.
Модуль не зависит от PyQt5 и может тестироваться автономно.
"""
from dataclasses import dataclass

from rtk_cors_client.ntrip.crc24q import CRC24Q

SYNC_BYTE = 0xD3
MAX_PAYLOAD = 1023


@dataclass
class RTCMFrame:
    """Валидированный RTCM-кадр."""
    data: bytes
    msg_id: int
    payload_length: int


class RTCMFrameParser:
    """Извлекает валидные кадры RTCM из потока байтов.

    Используется сетевым слоем: в буфер добавляются принятые байты,
    get_frames() возвращает список кадров с корректной CRC.
    """

    def __init__(self):
        self.buffer = bytearray()
        self.crc_failed = 0

    def feed(self, data: bytes) -> None:
        self.buffer.extend(data)

    def get_frames(self, max_iterations: int = 10000) -> list:
        frames = []
        iterations = 0

        while len(self.buffer) >= 3 and iterations < max_iterations:
            iterations += 1

            if self.buffer[0] != SYNC_BYTE:
                self.buffer.pop(0)
                continue

            length = ((self.buffer[1] & 0x03) << 8) | self.buffer[2]

            if length > MAX_PAYLOAD:
                self.buffer.pop(0)
                continue

            frame_len = 3 + length + 3
            if len(self.buffer) < frame_len:
                break

            frame = bytes(self.buffer[:frame_len])

            payload_with_header = frame[:-3]
            received_crc = (frame[-3] << 16) | (frame[-2] << 8) | frame[-1]
            computed_crc = CRC24Q.calculate(payload_with_header)

            if received_crc != computed_crc:
                self.crc_failed += 1
                self.buffer.pop(0)
                continue

            msg_id = 0
            if len(frame) >= 5:
                msg_id = (frame[3] << 4) | (frame[4] >> 4)

            frames.append(RTCMFrame(data=frame, msg_id=msg_id, payload_length=length))
            del self.buffer[:frame_len]

        return frames

    def reset(self):
        self.buffer = bytearray()
        self.crc_failed = 0

    def feed_and_parse(self, data: bytes) -> list:
        """feed() + get_frames() одним вызовом."""
        self.feed(data)
        return self.get_frames()
