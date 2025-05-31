from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from dataclasses import dataclass
import cryptocompare
import requests
import pandas as pd

from ..models.price_event import Event
from ..database.db_manager import DatabaseManager

# Константы для типов событий
EVENT_TYPES = {
    'NEWS': 'news',
    'REGULATION': 'regulation',
    'MARKET': 'market',
    'TECHNICAL': 'technical'
}

@dataclass
class NewsSource:
    """Конфигурация источника новостей"""
    name: str
    api_key: Optional[str] = None
    enabled: bool = True

class NewsCollector:
    """Класс для сбора новостей из различных источников"""
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        """
        Инициализация сборщика новостей
        
        Args:
            config: Конфигурация с настройками источников и API ключами
            db_manager: Менеджер базы данных для сохранения событий
        """
        self.config = config
        self.db_manager = db_manager
        self.sources: List[NewsSource] = []
        self._init_sources()
        
    def _init_sources(self) -> None:
        """Инициализация источников новостей из конфигурации"""
        sources_config = self.config.get('news_collector', {}).get('sources', {})
        
        for source_name, source_config in sources_config.items():
            if source_config.get('enabled', True):
                self.sources.append(
                    NewsSource(
                        name=source_name,
                        api_key=source_config.get('api_key'),
                        enabled=True
                    )
                )
        
        logger.info(f"Initialized {len(self.sources)} news sources")
    
    def collect_news(self, start_date: datetime, end_date: datetime) -> None:
        """
        Сбор новостей за указанный период и сохранение их в базу данных
        
        Args:
            start_date: Начальная дата периода
            end_date: Конечная дата периода
        """
        logger.info(f"Начало сбора новостей за период {start_date} - {end_date}")
        total_events = 0
        
        for source in self.sources:
            try:
                logger.debug(f"Сбор новостей из источника {source.name}")
                source_events = self._collect_from_source(source, start_date, end_date)
                
                # Сохраняем каждое событие в базу данных
                for event in source_events:
                    try:
                        self.db_manager.save_event(event)
                        total_events += 1
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении события в БД: {str(e)}")
                        continue
                        
                logger.info(f"Собрано и сохранено {len(source_events)} новостей из {source.name}")
            except Exception as e:
                logger.error(f"Ошибка при сборе новостей из {source.name}: {str(e)}")
        
        if total_events == 0:
            logger.warning(f"Не удалось собрать новости за период {start_date} - {end_date}")
        else:
            logger.info(f"Всего собрано и сохранено {total_events} новостей из всех источников")
    
    def _collect_from_source(self, source: NewsSource, 
                           start_date: datetime, 
                           end_date: datetime) -> List[Event]:
        """
        Сбор новостей из конкретного источника
        
        Args:
            source: Источник новостей
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            
        Returns:
            List[Event]: Список событий из источника
        """
        if source.name == 'cryptocompare':
            return self._collect_from_cryptocompare(source, start_date, end_date)
        return []
    
    def _collect_from_cryptocompare(self, source: NewsSource,
                                  start_date: datetime,
                                  end_date: datetime) -> List[Event]:
        """
        Сбор новостей из CryptoCompare только с первой страницы (без пагинации)
        """
        #TODO реализовать сбор всех новостей за указанный период
        try:
            # Проверяем валидность дат
            if end_date < start_date:
                logger.error(f"Invalid date range: end_date {end_date} is before start_date {start_date}")
                return []

            events = []
            url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&page=0"
            response = requests.get(url)
            response.raise_for_status()
            news_data = response.json()

            if not isinstance(news_data, dict):
                raise Exception(f"Invalid response format: {type(news_data)}")

            if 'Data' not in news_data:
                raise Exception(f"Missing 'Data' field in response: {news_data}")

            for item in news_data['Data']:
                try:
                    news_time = datetime.fromtimestamp(item['published_on'])
                    if start_date <= news_time <= end_date:
                        event = Event(
                            timestamp=news_time,
                            event_type=EVENT_TYPES['NEWS'],
                            source='cryptocompare',
                            description=item['title'],
                            sentiment_score=None
                        )
                        events.append(event)
                        logger.debug(f"Added news: {item['title']} ({news_time})")
                    else:
                        logger.debug(f"Skipped news outside period: {item['title']} ({news_time})")
                except KeyError as e:
                    logger.warning(f"Missing required field in news item: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing news item: {e}")
                    continue

            logger.info(f"Collected {len(events)} news from CryptoCompare for period {start_date} to {end_date}")
            return events

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while collecting news from CryptoCompare: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error collecting news from CryptoCompare: {str(e)}")
            return [] 