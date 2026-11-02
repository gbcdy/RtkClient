# -*- coding: utf-8 -*-
"""Генерация NMEA GGA-предложений (ручная, без pynmea2).

Логика перенесена из NTRIPWorker.generate_gga() монолитного rtk4.py.
"""
import time

import numpy as np


def generate_gga(lat: float, lon: float, alt: float,
                 noise_std: float = 0.0) -> str:
    """Формирует NMEA $GPGGA с опциональным гауссовым шумом координат."""
    curr_lat = lat + np.random.normal(0, noise_std) if noise_std else lat
    curr_lon = lon + np.random.normal(0, noise_std) if noise_std else lon

    lat_deg = int(abs(curr_lat))
    lat_min = (abs(curr_lat) - lat_deg) * 60
    lon_deg = int(abs(curr_lon))
    lon_min = (abs(curr_lon) - lon_deg) * 60

    lat_dir = 'N' if curr_lat >= 0 else 'S'
    lon_dir = 'E' if curr_lon >= 0 else 'W'

    timestamp = time.strftime('%H%M%S.00', time.gmtime())

    body = (
        f"GPGGA,{timestamp},"
        f"{lat_deg:02d}{lat_min:07.4f},{lat_dir},"
        f"{lon_deg:03d}{lon_min:07.4f},{lon_dir},"
        f"4,12,0.8,{alt:.1f},M,0.0,M,,"
    )

    checksum = 0
    for char in body:
        checksum ^= ord(char)

    return f"${body}*{checksum:02X}\r\n"
