import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import yaml
from loguru import logger

from src.analysis.event_analyzer import EventAnalyzer
from src.analysis.news_collector import NewsCollector
from src.analysis.price_analyzer import PriceAnalyzer
from src.database.init_db import init_database
from src.database.db_manager import DatabaseManager

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
        
        # Анализ изменений цены биткоина
        price_analyzer = PriceAnalyzer(db_manager, threshold_percent=0.1)
        price_analyzer.analyze_price_changes(start_date, end_date)
        
        # Получаем последнее значительное изменение цены
        last_price_change = price_analyzer.get_last_significant_change()
            
        if last_price_change:
            # Сбор новостей и сохранение в базу данных
            collector = NewsCollector(config, db_manager)
            collector.collect_news(start_date, end_date)
            
            # Инициализация анализатора и проведение анализа
            analyzer = EventAnalyzer(
                last_price_change.timestamp,
                last_price_change.percentage_change,
                db_manager
            )
            analyzer.analyze_causes()
        else:
            logger.info("Не обнаружено значительных изменений цены за указанный период")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении анализа: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 