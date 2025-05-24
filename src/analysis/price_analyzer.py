from datetime import datetime, timedelta
import ccxt
from loguru import logger
from typing import Optional, Tuple

from src.models.database import PriceChange
from src.database.db_manager import DatabaseManager

class PriceAnalyzer:
    def __init__(self, db_manager: DatabaseManager, threshold_percent: float = 5.0):
        """
        Инициализация анализатора цены
        
        Args:
            db_manager: Менеджер базы данных
            threshold_percent: Пороговое значение изменения цены в процентах
        """
        self.db_manager = db_manager
        self.threshold_percent = threshold_percent
        self.exchange = ccxt.binance()
        
    def get_bitcoin_price(self, timestamp: datetime) -> Optional[float]:
        """
        Получение цены биткоина на определенный момент времени
        
        Args:
            timestamp: Временная метка
            
        Returns:
            Цена биткоина или None в случае ошибки
        """
        try:
            # Конвертируем datetime в timestamp в миллисекундах
            timestamp_ms = int(timestamp.timestamp() * 1000)
            
            # Получаем OHLCV данные за день
            ohlcv = self.exchange.fetch_ohlcv(
                symbol='BTC/USDT',
                timeframe='1d',
                since=timestamp_ms,
                limit=1
            )
            
            if ohlcv and len(ohlcv) > 0:
                return float(ohlcv[0][4])  # Возвращаем цену закрытия
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении цены биткоина: {str(e)}")
            return None
            
    def analyze_price_changes(self, start_date: datetime, end_date: datetime) -> None:
        """
        Анализ изменений цены биткоина за указанный период
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
        """
        current_time = start_date
        
        while current_time <= end_date:
            # Получаем цены для текущего дня и предыдущего
            current_price = self.get_bitcoin_price(current_time)
            previous_time = current_time - timedelta(days=1)
            previous_price = self.get_bitcoin_price(previous_time)
            
            if current_price and previous_price:
                # Рассчитываем процентное изменение
                price_change_percent = ((current_price - previous_price) / previous_price) * 100
                
                # Если изменение превышает пороговое значение, сохраняем в базу
                if abs(price_change_percent) >= self.threshold_percent:
                    self._save_price_change(current_time, previous_price, current_price, price_change_percent)
            
            current_time += timedelta(days=1)

    def get_last_significant_change(self) -> Optional[PriceChange]:
        """
        Получение последнего значительного изменения цены
        
        Returns:
            Последнее значительное изменение цены или None, если изменений нет
        """
        try:
            return self.db_manager.session.query(PriceChange)\
                .order_by(PriceChange.timestamp.desc())\
                .first()
        except Exception as e:
            logger.error(f"Ошибка при получении последнего изменения цены: {str(e)}")
            return None

    def _save_price_change(self, timestamp: datetime, price_before: float, 
                          price_after: float, percentage_change: float) -> None:
        """
        Сохранение изменения цены в базу данных
        
        Args:
            timestamp: Временная метка изменения
            price_before: Цена до изменения
            price_after: Цена после изменения
            percentage_change: Процентное изменение
        """
        price_change = PriceChange(
            timestamp=timestamp,
            price_before=price_before,
            price_after=price_after,
            percentage_change=percentage_change
        )
        
        try:
            self.db_manager.session.add(price_change)
            self.db_manager.session.commit()
            logger.info(
                f"Обнаружено значительное изменение цены: {percentage_change:.2f}% "
                f"в {timestamp.strftime('%Y-%m-%d')}"
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении изменения цены: {str(e)}")
            self.db_manager.session.rollback()