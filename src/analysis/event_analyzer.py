from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from src.models.price_event import Event, PriceEventCorrelation
from src.database.db_manager import DatabaseManager
from sqlalchemy.orm import Session
from src.models.database import PriceChange
from loguru import logger
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class EventAnalyzer:
    """Класс для анализа причин изменения цены биткоина"""
    
    def __init__(self, price_change_date: datetime, 
                 price_change_percent: float, db_manager: DatabaseManager):
        """
        Инициализация анализатора событий
        
        Args:
            price_change_date: Дата изменения цены
            price_change_percent: Процентное изменение цены
            db_manager: Менеджер базы данных
        """
        self.price_change_date = price_change_date
        self.price_change_percent = price_change_percent
        self.db_manager = db_manager
        
    def find_relevant_events(self, window_hours: Optional[int] = None) -> List[Event]:
        """
        Поиск событий из базы данных, которые могли повлиять на изменение цены
        
        Args:
            window_hours: Временное окно в часах для поиска событий. Если None, 
                         возвращаются все события из базы данных
            
        Returns:
            Список релевантных событий
        """
        if window_hours is None:
            # Получаем все события из базы данных
            events = self.db_manager.get_all_events()
            if not events:
                logger.info("В базе данных нет событий")
                return []
            logger.info(f"Получены все события из базы данных, всего: {len(events)}")
            return events
            
        start_time = self.price_change_date - timedelta(hours=window_hours)
        end_time = self.price_change_date 
        
        # Получаем события из базы данных за указанный период
        events = self.db_manager.get_events_in_period(start_time, end_time)
        
        if not events:
            logger.info(f"Не найдено событий в период {start_time} - {end_time}")
            return []
            
        logger.info(f"Найдено {len(events)} релевантных событий за период {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}")
        return events
    
    def analyze_sentiments(self, events: List[Event]) -> List[Event]:
        """Анализирует тональность для каждого события, если не задана."""
        analyzer = SentimentIntensityAnalyzer()
        result = []
        for event in events:
            if event.sentiment_score is None:
                sentiment_score = analyzer.polarity_scores(event.description)['compound']
                event = Event(
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    source=event.source,
                    description=event.description,
                    sentiment_score=sentiment_score
                )
            result.append(event)
        return result

    def analyze_influences(self, events: List[Event]) -> List[PriceEventCorrelation]:
        """Рассчитывает влияние каждого события на изменение цены."""
        causes = []
        for event in events:
            # 1. Временная близость
            time_diff = abs((self.price_change_date - event.timestamp).total_seconds() / 3600)
            time_factor = 1.0 / (1.0 + time_diff)
            # 2. Соответствие настроения и направления изменения цены
            sentiment_factor = 1.0
            if event.sentiment_score is not None:
                if (self.price_change_percent > 0 and event.sentiment_score > 0) or \
                   (self.price_change_percent < 0 and event.sentiment_score < 0):
                    sentiment_factor = abs(event.sentiment_score)
                else:
                    sentiment_factor = 0.5
            # 3. Тип события
            event_type_factor = 1.0
            if event.event_type == 'ETF':
                event_type_factor = 1.5
            elif event.event_type == 'REGULATION':
                event_type_factor = 1.2
            # Итоговая оценка влияния
            impact_score = min(1.0, time_factor * sentiment_factor * event_type_factor)
            cause = PriceEventCorrelation(
                event=event,
                impact_score=impact_score
            )
            causes.append(cause)
        causes.sort(key=lambda x: x.impact_score, reverse=True)
        return causes

    def save_analysis_results(self, price_change: PriceChange, correlations: List[PriceEventCorrelation]) -> None:
        """Сохраняет результаты анализа в базу данных."""
        try:
            self.db_manager.save_analysis_results(price_change, correlations)
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов анализа: {str(e)}")

    def analyze_causes(self, window_hours: Optional[int] = None) -> None:
        """
        Полный анализ: поиск релевантных событий, анализ тональности и влияния, сохранение и вывод результатов.
        
        Args:
            window_hours: Временное окно в часах для поиска событий. Если None, 
                         анализируются все события из базы данных
        """
        # 1. Поиск релевантных событий
        events = self.find_relevant_events(window_hours=window_hours)
        if not events:
            logger.info("Релевантные события не найдены.")
            return
            
        # 2. Анализ тональности
        events_with_sentiment = self.analyze_sentiments(events)
        
        # 3. Анализ влияния
        correlations = self.analyze_influences(events_with_sentiment)
        
        # 4. Сохранение результатов
        price_change = PriceChange(
            timestamp=self.price_change_date,
            price_before=0.0,  # TODO: получить из данных
            price_after=0.0,   # TODO: получить из данных
            percentage_change=self.price_change_percent
        )
        self.save_analysis_results(price_change, correlations)
        
        # 5. Вывод результатов
        logger.info(f"\nАнализ причин изменения цены биткоина {self.price_change_date.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Изменение цены: {self.price_change_percent:+.1f}%")
        logger.info("\nВозможные причины (отсортированы по влиянию):")
        for cause in correlations:
            cause.log_details() 