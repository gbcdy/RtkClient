# -*- coding: utf-8 -*-
"""Коллекторы RTCM и фабрика реестра по умолчанию."""
from .antenna import AntennaCollector
from .base import BaseCollector, CollectorRegistry
from .base_station import BaseStationCollector
from .coordinate_system import CoordinateSystemCollector
from .proprietary import ProprietaryCollector


def create_default_registry() -> CollectorRegistry:
    """Создаёт реестр со всеми встроенными коллекторами."""
    registry = CollectorRegistry()
    registry.register(BaseStationCollector())
    registry.register(AntennaCollector())
    registry.register(CoordinateSystemCollector())
    registry.register(ProprietaryCollector())
    return registry


__all__ = [
    "BaseCollector",
    "CollectorRegistry",
    "BaseStationCollector",
    "AntennaCollector",
    "CoordinateSystemCollector",
    "ProprietaryCollector",
    "create_default_registry",
]
