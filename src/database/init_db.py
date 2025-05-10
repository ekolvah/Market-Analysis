import os
import sys
from pathlib import Path
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.models.database import Base

def load_config():
    """Загрузка конфигурации из файла"""
    config_path = project_root / 'config' / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def init_database():
    """Инициализация базы данных"""
    try:
        # Загружаем конфигурацию
        config = load_config()
        db_path = project_root / config['database']['path']
        
        # Создаем директорию для базы данных, если она не существует
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Формируем URL для подключения к SQLite
        database_url = f"sqlite:///{db_path}"
        
        # Создаем движок SQLAlchemy
        engine = create_engine(
            database_url,
            echo=False  # Отключаем вывод SQL-запросов
        )
        
        # Создаем все таблицы
        logger.info("Создание таблиц в базе данных...")
        Base.metadata.create_all(engine)
        logger.info("Таблицы успешно созданы")
        
        # Создаем фабрику сессий
        Session = sessionmaker(bind=engine)
        
        return engine, Session
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
        raise

def main():
    """Основная функция для запуска инициализации"""
    try:
        engine, Session = init_database()
        logger.info("База данных успешно инициализирована")
        
        # Проверяем подключение
        with Session() as session:
            session.execute("SELECT 1")
            logger.info("Подключение к базе данных успешно проверено")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 