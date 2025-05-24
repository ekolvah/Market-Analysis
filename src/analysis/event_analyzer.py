from datetime import datetime, timedelta
from typing import List
import pandas as pd
from src.models.price_event import Event, PriceEventCorrelation
from src.database.db_manager import DatabaseManager
from sqlalchemy.orm import Session
from src.models.database import PriceChange
from loguru import logger

class EventAnalyzer:
    """Класс для анализа причин изменения цены биткоина"""
    
    def __init__(self, events_data: pd.DataFrame, price_change_date: datetime, 
                 price_change_percent: float, db_manager: DatabaseManager):
        """
        Инициализация анализатора событий
        
        Args:
            events_data: DataFrame с данными о событиях
            price_change_date: Дата изменения цены
            price_change_percent: Процентное изменение цены
            db_manager: Менеджер базы данных
        """
        self.events_data = events_data
        self.price_change_date = price_change_date
        self.price_change_percent = price_change_percent
        self.db_manager = db_manager
        
    def find_relevant_events(self, window_hours: int = 24) -> List[Event]:
        """
        Поиск событий, которые могли повлиять на изменение цены
        
        Args:
            window_hours: Временное окно в часах для поиска событий
            
        Returns:
            Список релевантных событий
        """
        start_time = self.price_change_date - timedelta(hours=window_hours)
        end_time = self.price_change_date + timedelta(hours=window_hours)
        
        # Фильтруем события по временному окну
        mask = (self.events_data['timestamp'] >= start_time) & (self.events_data['timestamp'] <= end_time)
        relevant_events = self.events_data[mask].copy()
        
        # Преобразуем в список объектов Event
        events = []
        for _, row in relevant_events.iterrows():
            event = Event(
                timestamp=row['timestamp'],
                event_type=row['event_type'],
                source=row['source'],
                description=row['description'],
                sentiment_score=row.get('sentiment_score')
            )
            events.append(event)
            
        return events
    
    def analyze_causes(self, events: List[Event]) -> List[PriceEventCorrelation]:
        """
        Анализ причин изменения цены
        
        Args:
            events: Список событий для анализа
            
        Returns:
            Список возможных причин с оценкой их влияния
        """
        causes = []
        
        for event in events:
            # Оценка влияния события на основе:
            # 1. Временной близости к изменению цены
            time_diff = abs((self.price_change_date - event.timestamp).total_seconds() / 3600)  # в часах
            time_factor = 1.0 / (1.0 + time_diff)  # чем ближе по времени, тем выше влияние
            
            # 2. Направления изменения цены и настроения события
            sentiment_factor = 1.0
            if event.sentiment_score is not None:
                # Если изменение цены положительное и настроение положительное (или наоборот)
                if (self.price_change_percent > 0 and event.sentiment_score > 0) or \
                   (self.price_change_percent < 0 and event.sentiment_score < 0):
                    sentiment_factor = abs(event.sentiment_score)
                else:
                    sentiment_factor = 0.5  # Снижаем влияние, если направление не совпадает
            
            # 3. Типа события (можно добавить веса для разных типов событий)
            event_type_factor = 1.0
            if event.event_type == 'ETF':
                event_type_factor = 1.5  # ETF события обычно имеют большее влияние
            elif event.event_type == 'REGULATION':
                event_type_factor = 1.2  # Регуляторные события также важны
            
            # Итоговая оценка влияния события (нормализованная от 0 до 1)
            # Учитывает временную близость, соответствие настроения и важность типа события
            impact_score = min(1.0, time_factor * sentiment_factor * event_type_factor)
            
            cause = PriceEventCorrelation(
                event=event,
                impact_score=impact_score
            )
            causes.append(cause)
        
        # Сортируем по убыванию влияния
        causes.sort(key=lambda x: x.impact_score, reverse=True)
        
        # Сохраняем результаты в базу данных
        try:
            # Создаем объект PriceChange для сохранения
            price_change = PriceChange(
                timestamp=self.price_change_date,
                price_before=0.0,  # Эти значения нужно получать из реальных данных
                price_after=0.0,   # Эти значения нужно получать из реальных данных
                percentage_change=self.price_change_percent
            )
            
            # Сохраняем результаты
            self.db_manager.save_analysis_results(price_change, causes)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов анализа: {str(e)}")
            # Продолжаем выполнение, даже если сохранение не удалось
        
        return causes 