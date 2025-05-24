from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from loguru import logger

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

    def log_details(self) -> None:
        """Логирование детальной информации о причине изменения цены"""
        logger.info(f"\nСобытие: {self.event.description}")
        logger.info(f"Тип: {self.event.event_type}")
        logger.info(f"Источник: {self.event.source}")
        logger.info(f"Время: {self.event.timestamp.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Влияние: {self.impact_score:.2f}")
        logger.info(f"Уверенность: {self.confidence_level:.2f}") 