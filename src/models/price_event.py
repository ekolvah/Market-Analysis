from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Event:
    """Модель для хранения информации о событии"""
    timestamp: datetime
    event_type: str
    source: str
    description: str
    sentiment_score: Optional[float] = None

@dataclass
class PriceEventCorrelation:
    """Модель для хранения корреляции между событием и изменением цены"""
    event: Event
    impact_score: float
    confidence_level: float 