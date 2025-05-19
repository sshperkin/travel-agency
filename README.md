# Travel Agency Management System

Система управления туристическим агентством, разработанная на Python с использованием PyQt5 для графического интерфейса и PostgreSQL для хранения данных.

## Функциональность

- Управление клиентами
- Управление турами
- Управление бронированиями
- Управление сотрудниками
- Система авторизации и регистрации
- Генерация отчетов
- Фильтрация и поиск данных

## Технологии

- Python 3.x
- PyQt5
- SQLAlchemy
- PostgreSQL
- bcrypt (для хеширования паролей)

## Установка

1. Клонируйте репозиторий:
```bash
git clone [URL репозитория]
cd travel-agency
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
# или
.venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл конфигурации `config.py` с настройками базы данных:
```python
DATABASE_URL = "postgresql://username:password@localhost:5432/travel_agency"
```

5. Инициализируйте базу данных:
```bash
python init_db.py
```

## Запуск

```bash
python main.py
```

## Структура проекта

- `main.py` - точка входа в приложение
- `gui.py` - графический интерфейс
- `database.py` - модели и работа с базой данных
- `config.py` - конфигурация приложения
- `init_db.py` - инициализация базы данных
- `reports.py` - генерация отчетов

## Лицензия

MIT 