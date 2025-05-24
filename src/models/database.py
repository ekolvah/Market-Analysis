from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class PriceChange(Base):
    """Модель для хранения изменений цены биткоина"""
    __tablename__ = 'price_changes'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price_before = Column(Float, nullable=False)
    price_after = Column(Float, nullable=False)
    percentage_change = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    # Связь с корреляциями
    correlations = relationship("EventPriceCorrelation", back_populates="price_change")

    def __repr__(self):
        return f"<PriceChange(id={self.id}, timestamp={self.timestamp}, change={self.percentage_change}%)>"


class Event(Base):
    """Модель для хранения информации о событиях"""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=True)

    # Связь с корреляциями
    correlations = relationship("EventPriceCorrelation", back_populates="event")

    def __repr__(self):
        return f"<Event(id={self.id}, type={self.event_type}, timestamp={self.timestamp})>"


class EventPriceCorrelation(Base):
    """Модель для хранения корреляций между событиями и изменениями цены"""
    __tablename__ = 'event_price_correlations'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    price_change_id = Column(Integer, ForeignKey('price_changes.id'), nullable=False)
    impact_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими таблицами
    event = relationship("Event", back_populates="correlations")
    price_change = relationship("PriceChange", back_populates="correlations")

    def __repr__(self):
        return f"<EventPriceCorrelation(id={self.id}, impact={self.impact_score})>" 