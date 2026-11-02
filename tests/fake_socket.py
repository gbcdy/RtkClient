# -*- coding: utf-8 -*-
"""Фейковый сокет для офлайн-тестирования SessionManager без сети."""


class FakeSocket:
    """Эмулирует TCP-сокет NTRIP-сервера.

    Args:
        responses: список байтов, которые «сервер» отдаёт по recv()
                   (по одному блоку на вызов; после исчерпания — b'' = закрытие).
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.sent = []          # всё, что отправил клиент (запрос, GGA...)
        self.closed = False
        self._connect_target = None

    # --- API сокета -----------------------------------------------------
    def settimeout(self, t):
        pass

    def connect(self, addr):
        self._connect_target = addr

    def send(self, data):
        self.sent.append(data)
        return len(data)

    sendall = send

    def recv(self, bufsize):
        if not self._responses:
            raise OSError("10038 not a socket")  # соединение «закрыто»
        return self._responses.pop(0)

    def close(self):
        self.closed = True

    # --- помощник -------------------------------------------------------
    def sent_text(self) -> str:
        return b"".join(self.sent).decode("utf-8", errors="ignore")
