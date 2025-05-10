import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import yaml
from loguru import logger

from src.analysis.event_analyzer import EventAnalyzer
from src.analysis.news_collector import NewsCollector
from src.database.init_db import init_database
from src.database.db_manager import DatabaseManager

def collect_news_for_period(start_date: datetime, end_date: datetime, config: dict) -> pd.DataFrame:
    """
    Сбор новостей за указанный период
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        config: Конфигурация приложения
        
    Returns:
        pd.DataFrame: DataFrame с новостями
    """
    try:
        collector = NewsCollector(config)
        events = collector.collect_news(start_date, end_date)
        
        if not events:
            logger.warning(f"Не удалось собрать новости за период {start_date} - {end_date}")
            return pd.DataFrame()
        
        # Преобразуем события в DataFrame
        events_data = pd.DataFrame({
            'timestamp': [event.timestamp for event in events],
            'event_type': [event.event_type for event in events],
            'source': [event.source for event in events],
            'description': [event.description for event in events],
            'sentiment_score': [event.sentiment_score for event in events]
        })
        
        logger.info(f"Успешно собрано {len(events_data)} новостей")
        return events_data
        
    except Exception as e:
        logger.error(f"Ошибка при сборе новостей: {str(e)}")
        return pd.DataFrame()

def main():
    # Загружаем конфигурацию
    try:
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Ошибка при чтении конфигурации: {str(e)}")
        return
    
    # Инициализация базы данных
    engine, Session = init_database()
    session = Session()
    db_manager = DatabaseManager(session)
    
    try:
        # Используем текущую дату и последние 7 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Для примера берем изменение цены за последние 24 часа
        price_change_date = end_date
        price_change_percent = 5.0  # Примерное изменение цены
        
        logger.info(f"Собираем новости за период с {start_date} по {end_date}")
        events_data = collect_news_for_period(start_date, end_date, config)
        
        # Инициализация анализатора
        analyzer = EventAnalyzer(events_data, price_change_date, price_change_percent, db_manager)
        
        # Поиск релевантных событий
        events = analyzer.find_relevant_events(window_hours=24)
        
        # Анализ причин изменения цены
        causes = analyzer.analyze_causes(events)
        
        # Вывод результатов
        print(f"\nАнализ причин изменения цены биткоина {price_change_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"Изменение цены: {price_change_percent:+.1f}%")
        print("\nВозможные причины (отсортированы по влиянию):")
        
        for cause in causes:
            print(f"\nСобытие: {cause.event.description}")
            print(f"Тип: {cause.event.event_type}")
            print(f"Источник: {cause.event.source}")
            print(f"Время: {cause.event.timestamp.strftime('%Y-%m-%d %H:%M')}")
            print(f"Влияние: {cause.impact_score:.2f}")
            print(f"Уверенность: {cause.confidence_level:.2f}")
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении анализа: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 