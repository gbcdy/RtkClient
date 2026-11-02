# -*- coding: utf-8 -*-
"""Геодезические преобразования координат.

Логика перенесена из NTRIPWorker._ecef_to_wgs84() монолитного rtk4.py.
"""
import numpy as np

# Параметры эллипсоида WGS84
WGS84_A = 6378137.0               # большая полуось, м
WGS84_F = 1 / 298.257223563       # сжатие
WGS84_B = WGS84_A * (1 - WGS84_F) # малая полуось, м


def ecef_to_wgs84(x: float, y: float, z: float):
    """Перевод геоцентрических координат ECEF (м) в широту/долготу/высоту WGS84.

    Возвращает кортеж (lat_deg, lon_deg, alt_m).
    """
    a = WGS84_A
    f = WGS84_F
    b = WGS84_B
    e2 = (a**2 - b**2) / a**2
    ep2 = (a**2 - b**2) / b**2

    p = np.sqrt(x**2 + y**2)
    theta = np.arctan2(z * a, p * b)

    lon = np.arctan2(y, x)
    lat = np.arctan2(
        z + ep2 * b * np.sin(theta)**3,
        p - e2 * a * np.cos(theta)**3
    )
    N = a / np.sqrt(1 - e2 * np.sin(lat)**2)
    alt = p / np.cos(lat) - N

    return np.degrees(lat), np.degrees(lon), alt
