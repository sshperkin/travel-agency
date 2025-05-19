"""Модуль для работы с базой данных турагентства."""
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime, Text, Numeric, CheckConstraint, UniqueConstraint, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from config import DATABASE_URL
from datetime import datetime, date
import contextlib
import enum
import bcrypt

logging.basicConfig(filename='travel_agency.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseError(Exception):
    """Базовый класс для исключений базы данных."""
    pass

class ConnectionError(DatabaseError):
    """Исключение при ошибке подключения к базе данных."""
    pass

class ValidationError(DatabaseError):
    """Исключение при ошибке валидации данных."""
    pass

class DataError(DatabaseError):
    """Исключение при ошибке в данных."""
    pass

class UserRole(enum.Enum):
    MANAGER = "manager"
    ADMIN = "admin"

# Create database engine with connection pool
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600
    )
    
    # Create thread-safe session factory
    Session = scoped_session(sessionmaker(bind=engine))
    
except Exception as e:
    logging.critical(f"Не удалось инициализировать подключение к базе данных: {str(e)}")
    raise ConnectionError(f"Ошибка подключения к базе данных: {str(e)}")

# Create declarative base
Base = declarative_base()

class User(Base):
    """Модель пользователя системы."""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.employee_id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    employee = relationship("Employee", back_populates="user")
    
    def set_password(self, password):
        """Хеширование пароля."""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Проверка пароля."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

@contextlib.contextmanager
def session_scope():
    """Контекстный менеджер для работы с сессией базы данных."""
    session = Session()
    try:
        yield session
        session.commit()
    except IntegrityError as e:
        session.rollback()
        logging.error(f"Ошибка целостности данных: {str(e)}")
        raise DataError(f"Ошибка при сохранении данных: {str(e)}")
    except OperationalError as e:
        session.rollback()
        logging.error(f"Ошибка работы с базой данных: {str(e)}")
        raise ConnectionError(f"Ошибка подключения к базе данных: {str(e)}")
    except SQLAlchemyError as e:
        session.rollback()
        logging.error(f"Ошибка SQLAlchemy: {str(e)}")
        raise DatabaseError(f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        session.rollback()
        logging.error(f"Неожиданная ошибка при работе с базой данных: {str(e)}")
        raise
    finally:
        session.close()

def init_db():
    """Инициализация базы данных."""
    try:
        Base.metadata.create_all(engine)
        logging.info("База данных успешно инициализирована")
    except Exception as e:
        logging.critical(f"Ошибка при инициализации базы данных: {str(e)}")
        raise ConnectionError(f"Не удалось инициализировать базу данных: {str(e)}")

def add_client(session, client_data):
    """Добавление нового клиента."""
    try:
        # Проверка на существующий паспорт
        existing_client = session.query(Client).filter_by(
            passport_number=client_data['passport_number']
        ).first()
        if existing_client:
            raise DataError("Клиент с таким номером паспорта уже существует")

        # Проверка на существующий email
        if client_data.get('email'):
            existing_email = session.query(Client).filter_by(
                email=client_data['email']
            ).first()
            if existing_email:
                raise DataError("Клиент с таким email уже существует")

        client = Client(**client_data)
        session.add(client)
        session.flush()
        return client

    except DataError:
        raise
    except Exception as e:
        logging.error(f"Ошибка при добавлении клиента: {str(e)}")
        raise DatabaseError(f"Не удалось добавить клиента: {str(e)}")

def update_client(session, client_id, client_data):
    """Обновление данных клиента."""
    try:
        client = session.query(Client).get(client_id)
        if not client:
            raise DataError("Клиент не найден")

        # Проверка на существующий паспорт
        if 'passport_number' in client_data:
            existing_client = session.query(Client).filter(
                Client.client_id != client_id,
                Client.passport_number == client_data['passport_number']
            ).first()
            if existing_client:
                raise DataError("Клиент с таким номером паспорта уже существует")

        # Проверка на существующий email
        if client_data.get('email'):
            existing_email = session.query(Client).filter(
                Client.client_id != client_id,
                Client.email == client_data['email']
            ).first()
            if existing_email:
                raise DataError("Клиент с таким email уже существует")

        for key, value in client_data.items():
            setattr(client, key, value)
        
        session.flush()
        return client

    except DataError:
        raise
    except Exception as e:
        logging.error(f"Ошибка при обновлении клиента: {str(e)}")
        raise DatabaseError(f"Не удалось обновить данные клиента: {str(e)}")

def delete_client(session, client_id):
    """Удаление клиента."""
    try:
        client = session.query(Client).get(client_id)
        if not client:
            raise DataError("Клиент не найден")

        # Проверка на существующие бронирования
        bookings = session.query(Booking).filter_by(client_id=client_id).first()
        if bookings:
            raise DataError("Невозможно удалить клиента с существующими бронированиями")

        session.delete(client)
        session.flush()

    except DataError:
        raise
    except Exception as e:
        logging.error(f"Ошибка при удалении клиента: {str(e)}")
        raise DatabaseError(f"Не удалось удалить клиента: {str(e)}")

class Country(Base):
    """Модель страны."""
    __tablename__ = 'countries'
    
    country_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    visa_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    cities = relationship("City", back_populates="country")

class City(Base):
    """Модель города."""
    __tablename__ = 'cities'
    
    city_id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('countries.country_id'))
    name = Column(String(100), nullable=False)
    is_popular = Column(Boolean, default=False)
    
    country = relationship("Country", back_populates="cities")
    hotels = relationship("Hotel", back_populates="city")
    
    __table_args__ = (UniqueConstraint('country_id', 'name'),)

class Hotel(Base):
    """Модель отеля."""
    __tablename__ = 'hotels'
    
    hotel_id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey('cities.city_id'))
    name = Column(String(100), nullable=False)
    stars = Column(Integer)
    beach_line = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    city = relationship("City", back_populates="hotels")
    tours = relationship("TourHotel", back_populates="hotel")
    
    __table_args__ = (CheckConstraint('stars BETWEEN 1 AND 5'),)

class TourType(Base):
    """Модель типа тура."""
    __tablename__ = 'tour_types'
    
    type_id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    
    tours = relationship("Tour", back_populates="tour_type")

class Tour(Base):
    """Модель тура."""
    __tablename__ = 'tours'
    
    tour_id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey('tour_types.type_id'))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    base_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tour_type = relationship("TourType", back_populates="tours")
    hotels = relationship("TourHotel", back_populates="tour")
    bookings = relationship("Booking", back_populates="tour")
    reviews = relationship("Review", back_populates="tour")
    
    __table_args__ = (CheckConstraint('base_price > 0'),)

class TourHotel(Base):
    """Модель связи тур-отель."""
    __tablename__ = 'tour_hotels'
    
    tour_id = Column(Integer, ForeignKey('tours.tour_id'), primary_key=True)
    hotel_id = Column(Integer, ForeignKey('hotels.hotel_id'), primary_key=True)
    nights = Column(Integer, nullable=False)
    
    tour = relationship("Tour", back_populates="hotels")
    hotel = relationship("Hotel", back_populates="tours")
    
    __table_args__ = (CheckConstraint('nights > 0'),)

class Client(Base):
    """Модель клиента."""
    __tablename__ = 'clients'
    
    client_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    name_latin = Column(String(100))
    passport_number = Column(String(20), unique=True, nullable=False)
    passport_expiry = Column(Date, nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), unique=True)
    registration_date = Column(Date, default=datetime.utcnow)
    
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="client", cascade="all, delete-orphan")

class Employee(Base):
    """Модель сотрудника."""
    __tablename__ = 'employees'
    
    employee_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    position = Column(String(50), nullable=False)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    
    bookings = relationship("Booking", back_populates="employee")
    user = relationship("User", back_populates="employee")
    
    __table_args__ = (CheckConstraint('salary > 0'),)

class Booking(Base):
    """Модель бронирования."""
    __tablename__ = 'bookings'
    
    booking_id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.client_id'))
    tour_id = Column(Integer, ForeignKey('tours.tour_id'))
    employee_id = Column(Integer, ForeignKey('employees.employee_id'))
    booking_date = Column(DateTime, default=datetime.utcnow)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)
    is_paid = Column(Boolean, default=False)
    has_prepayment = Column(Boolean, default=False)
    
    client = relationship("Client", back_populates="bookings")
    tour = relationship("Tour", back_populates="bookings")
    employee = relationship("Employee", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('return_date > departure_date'),
        CheckConstraint("status IN ('confirmed', 'paid', 'cancelled', 'completed')")
    )

class Payment(Base):
    """Модель платежа."""
    __tablename__ = 'payments'
    
    payment_id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.booking_id'))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    method = Column(String(20), nullable=False)
    transaction_id = Column(String(100), unique=True)
    
    booking = relationship("Booking", back_populates="payments")
    
    __table_args__ = (CheckConstraint('amount > 0'),)

class Review(Base):
    """Модель отзыва."""
    __tablename__ = 'reviews'
    
    review_id = Column(Integer, primary_key=True)
    tour_id = Column(Integer, ForeignKey('tours.tour_id'))
    client_id = Column(Integer, ForeignKey('clients.client_id'))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    review_date = Column(Date, default=datetime.utcnow)
    
    tour = relationship("Tour", back_populates="reviews")
    client = relationship("Client", back_populates="reviews")
    
    __table_args__ = (
        CheckConstraint('rating BETWEEN 1 AND 5'),
        UniqueConstraint('tour_id', 'client_id')
    )

class Transport(Base):
    """Модель транспортного средства."""
    __tablename__ = 'transports'
    
    transport_id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)
    company = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    registration_number = Column(String(50), unique=True)
    
    __table_args__ = (CheckConstraint('capacity > 0'),)

def add_tour(destination, start_date, end_date, price, meal_type, comment, tour_operator):
    """Добавление тура в базу данных."""
    try:
        session = Session()
        tour = Tour(
            destination=destination,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            price=float(price),
            meal_type=meal_type,
            comment=comment,
            tour_operator=tour_operator
        )
        session.add(tour)
        session.commit()
        logging.info(f"Добавлен тур: {destination}")
        return tour.tour_id
    except Exception as e:
        session.rollback()
        logging.error(f"Ошибка добавления тура: {str(e)}")
        raise
    finally:
        session.close()

def load_tours():
    """Загрузка списка туров."""
    try:
        session = Session()
        tours = session.query(Tour).all()
        return [(t.tour_id, t.destination, t.start_date.strftime('%Y-%m-%d'),
                t.end_date.strftime('%Y-%m-%d'), t.price, t.meal_type,
                t.comment, t.tour_operator) for t in tours]
    except Exception as e:
        logging.error(f"Ошибка загрузки туров: {str(e)}")
        raise
    finally:
        session.close()

def add_booking(client_id, tour_id, booking_date, status, is_paid=False, has_prepayment=False):
    """Добавление бронирования в базу данных."""
    try:
        with session_scope() as session:
            booking = Booking(
                client_id=client_id,
                tour_id=tour_id,
                booking_date=datetime.strptime(booking_date, '%Y-%m-%d').date(),
                status=status,
                is_paid=is_paid,
                has_prepayment=has_prepayment
            )
            session.add(booking)
            session.flush()
            logging.info(f"Добавлено бронирование: клиент {client_id}, тур {tour_id}")
            return booking.booking_id
    except Exception as e:
        logging.error(f"Ошибка добавления бронирования: {str(e)}")
        raise DatabaseError(f"Не удалось добавить бронирование: {str(e)}")

def load_bookings():
    """Загрузка списка бронирований."""
    try:
        session = Session()
        bookings = session.query(Booking).all()
        return [(b.booking_id, b.client_id, b.tour_id,
                b.booking_date.strftime('%Y-%m-%d'), b.status,
                b.is_paid, b.has_prepayment, b.manager_name)
                for b in bookings]
    except Exception as e:
        logging.error(f"Ошибка загрузки бронирований: {str(e)}")
        raise
    finally:
        session.close()

def create_user(session, username, password, role, employee_id=None):
    """Создание нового пользователя."""
    user = User(username=username, role=role, employee_id=employee_id)
    user.set_password(password)
    session.add(user)
    session.commit()
    return user

def get_user_by_username(session, username):
    """Получение пользователя по имени."""
    return session.query(User).filter_by(username=username).first()

def authenticate_user(session, username, password):
    """Аутентификация пользователя."""
    user = get_user_by_username(session, username)
    if user and user.check_password(password) and user.is_active:
        return user
    return None