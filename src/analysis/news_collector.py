from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from dataclasses import dataclass
import cryptocompare
import requests
import pandas as pd

from ..models.price_event import Event

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
    
    def __init__(self, config: Dict):
        """
        Инициализация сборщика новостей
        
        Args:
            config: Конфигурация с настройками источников и API ключами
        """
        self.config = config
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
    
    def collect_news(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Сбор новостей за указанный период
        
        Args:
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            
        Returns:
            List[Event]: Список событий
        """
        logger.info(f"Начало сбора новостей за период {start_date} - {end_date}")
        events = []
        
        for source in self.sources:
            try:
                logger.debug(f"Сбор новостей из источника {source.name}")
                source_events = self._collect_from_source(source, start_date, end_date)
                events.extend(source_events)
                logger.info(f"Собрано {len(source_events)} новостей из {source.name}")
            except Exception as e:
                logger.error(f"Ошибка при сборе новостей из {source.name}: {str(e)}")
        
        if not events:
            logger.warning(f"Не удалось собрать новости за период {start_date} - {end_date}")
            return []
            
        logger.info(f"Всего собрано {len(events)} новостей из всех источников")
        return events
    
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
        Сбор новостей из CryptoCompare
        
        Args:
            source: Источник новостей
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            
        Returns:
            List[Event]: Список событий из CryptoCompare
        """
        try:
            # Проверяем валидность дат
            if end_date < start_date:
                logger.error(f"Invalid date range: end_date {end_date} is before start_date {start_date}")
                return []
                
            # Получаем новости через API
            url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
            response = requests.get(url)
            response.raise_for_status()
            news_data = response.json()
            
            if not isinstance(news_data, dict):
                raise Exception(f"Invalid response format: {type(news_data)}")
            
            if 'Data' not in news_data:
                raise Exception(f"Missing 'Data' field in response: {news_data}")
            
            events = []
            logger.info(f"Processing news from {start_date} to {end_date}")
            
            for item in news_data['Data']:
                try:
                    # Преобразуем timestamp из Unix в datetime
                    news_time = datetime.fromtimestamp(item['published_on'])
                    
                    # Проверяем, что новость входит в нужный период
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