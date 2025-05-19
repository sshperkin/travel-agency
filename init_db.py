from database import Base, engine
from add_sample_data import add_sample_data

def init_database():
    # Создаем все таблицы
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    # Добавляем тестовые данные
    add_sample_data()

if __name__ == '__main__':
    init_database()
    print("База данных успешно инициализирована!") 