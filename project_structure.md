# Структура проекта

```
market_analysis/
├── config/
│   └── config.yaml           # Конфигурационный файл
├── data/
│   └── sample_data/          # Примеры данных для тестирования
├── src/
│   ├── __init__.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── price_analyzer.py # Анализ изменений цены
│   │   └── event_analyzer.py # Анализ событий
│   ├── models/
│   │   ├── __init__.py
│   │   └── price_event.py    # Модели данных
│   └── utils/
│       ├── __init__.py
│       └── logger.py         # Логирование
├── tests/
│   └── __init__.py
├── requirements.txt          # Зависимости проекта
└── README.md                # Документация
``` 