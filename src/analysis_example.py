import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from src.analysis.event_analyzer import EventAnalyzer
from src.database.init_db import init_database
from src.database.db_manager import DatabaseManager

def main():
    # Инициализация базы данных
    engine, Session = init_database()
    session = Session()
    db_manager = DatabaseManager(session)
    
    try:
        # Известное изменение цены 4 ноября 2024 года
        price_change_date = datetime(2024, 11, 4, 12, 0)  # Предположим, что изменение произошло в полдень
        price_change_percent = 15.0  # Предположим, что цена выросла на 15%
        
        # Пример данных о событиях
        events_data = pd.DataFrame({
            'timestamp': [
                datetime(2024, 11, 4, 10, 0),  # Запуск нового ETF
                datetime(2024, 11, 4, 14, 0),  # Крупная покупка
                datetime(2024, 11, 4, 18, 0),  # Новости о регулировании
                datetime(2024, 11, 3, 20, 0),  # Предыдущие новости о ETF
                datetime(2024, 11, 4, 9, 0)    # Ранние новости о рынке
            ],
            'event_type': ['ETF', 'TRADE', 'REGULATION', 'ETF', 'MARKET'],
            'source': ['Bloomberg', 'Binance', 'Reuters', 'CNBC', 'CoinDesk'],
            'description': [
                'Запуск нового Bitcoin ETF',
                'Крупная покупка биткоина на сумму $500M',
                'Новые правила регулирования криптовалют',
                'Подготовка к запуску Bitcoin ETF',
                'Рост интереса институциональных инвесторов'
            ],
            'sentiment_score': [0.8, 0.6, -0.3, 0.7, 0.5]
        })
        
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
            
    finally:
        session.close()

if __name__ == "__main__":
    main() 