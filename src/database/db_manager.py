from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from src.models.database import PriceChange, Event, EventPriceCorrelation
from src.models.price_event import Event as EventModel, PriceEventCorrelation as PriceEventCorrelationModel

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save_price_change(self, timestamp: datetime, price_before: float, 
                         price_after: float, percentage_change: float, 
                         volume: Optional[float] = None) -> PriceChange:
        """Сохранение изменения цены"""
        try:
            price_change = PriceChange(
                timestamp=timestamp,
                price_before=price_before,
                price_after=price_after,
                percentage_change=percentage_change,
                volume=volume
            )
            self.session.add(price_change)
            self.session.commit()
            logger.info(f"Сохранено изменение цены: {percentage_change:+.2f}%")
            return price_change
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка при сохранении изменения цены: {str(e)}")
            raise
    
    def save_event(self, event: EventModel) -> Event:
        """Сохранение события"""
        try:
            db_event = Event(
                timestamp=event.timestamp,
                event_type=event.event_type,
                source=event.source,
                description=event.description,
                sentiment_score=event.sentiment_score
            )
            self.session.add(db_event)
            self.session.commit()
            logger.info(f"Сохранено событие: {event.event_type} от {event.source}")
            return db_event
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка при сохранении события: {str(e)}")
            raise
    
    def save_correlation(self, correlation: PriceEventCorrelationModel, 
                        db_event: Event, db_price_change: PriceChange) -> EventPriceCorrelation:
        """Сохранение корреляции между событием и изменением цены"""
        try:
            db_correlation = EventPriceCorrelation(
                event_id=db_event.id,
                price_change_id=db_price_change.id,
                impact_score=correlation.impact_score,
                confidence_level=correlation.confidence_level
            )
            self.session.add(db_correlation)
            self.session.commit()
            logger.info(f"Сохранена корреляция: impact={correlation.impact_score:.2f}, confidence={correlation.confidence_level:.2f}")
            return db_correlation
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка при сохранении корреляции: {str(e)}")
            raise
    
    def get_price_change_by_unique(self, timestamp: datetime, percentage_change: float) -> Optional[PriceChange]:
        """Поиск изменения цены по дате и проценту изменения (для примера этого достаточно)"""
        return self.session.query(PriceChange).filter_by(
            timestamp=timestamp,
            percentage_change=percentage_change
        ).first()

    def get_event_by_unique(self, event: EventModel) -> Optional[Event]:
        """Поиск события по уникальным полям (timestamp, event_type, source, description)"""
        return self.session.query(Event).filter_by(
            timestamp=event.timestamp,
            event_type=event.event_type,
            source=event.source,
            description=event.description
        ).first()

    def get_correlation_by_unique(self, event_id: int, price_change_id: int) -> Optional[EventPriceCorrelation]:
        """Поиск корреляции по связке event_id + price_change_id"""
        return self.session.query(EventPriceCorrelation).filter_by(
            event_id=event_id,
            price_change_id=price_change_id
        ).first()

    def save_analysis_results(self, price_change: PriceChange, 
                            correlations: List[PriceEventCorrelationModel]) -> None:
        """Сохранение всех результатов анализа без дублирования"""
        try:
            # Проверяем, есть ли уже такое изменение цены
            db_price_change = self.get_price_change_by_unique(
                timestamp=price_change.timestamp,
                percentage_change=price_change.percentage_change
            )
            if not db_price_change:
                db_price_change = self.save_price_change(
                    timestamp=price_change.timestamp,
                    price_before=price_change.price_before,
                    price_after=price_change.price_after,
                    percentage_change=price_change.percentage_change,
                    volume=price_change.volume
                )

            for correlation in correlations:
                # Проверяем, есть ли уже такое событие
                db_event = self.get_event_by_unique(correlation.event)
                if not db_event:
                    db_event = self.save_event(correlation.event)
                # Проверяем, есть ли уже такая корреляция
                db_correlation = self.get_correlation_by_unique(db_event.id, db_price_change.id)
                if not db_correlation:
                    self.save_correlation(correlation, db_event, db_price_change)

            logger.info("Все результаты анализа успешно сохранены (без дублирования)")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка при сохранении результатов анализа: {str(e)}")
            raise
    
    def get_price_changes(self, start_date: datetime, end_date: datetime) -> List[PriceChange]:
        """Получение изменений цены за период"""
        return self.session.query(PriceChange)\
            .filter(PriceChange.timestamp.between(start_date, end_date))\
            .order_by(PriceChange.timestamp.desc())\
            .all()
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """Получение событий за период"""
        return self.session.query(Event)\
            .filter(Event.timestamp.between(start_date, end_date))\
            .order_by(Event.timestamp.desc())\
            .all()
    
    def get_correlations(self, price_change_id: int) -> List[EventPriceCorrelation]:
        """Получение корреляций для конкретного изменения цены"""
        return self.session.query(EventPriceCorrelation)\
            .filter(EventPriceCorrelation.price_change_id == price_change_id)\
            .order_by(EventPriceCorrelation.impact_score.desc())\
            .all() 