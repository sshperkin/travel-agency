"""Модуль для формирования отчетов и импорта/экспорта данных."""
import pandas as pd
import csv
import os
import logging
from sqlalchemy import text
from config import CSV_EXPORT_PATH, CSV_IMPORT_PATH, REPORT_PATH
from database import Session, Client, Tour, Booking

logging.basicConfig(filename='travel_agency.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def export_clients():
    """Экспорт клиентов в CSV."""
    try:
        session = Session()
        clients = session.query(Client).all()
        data = [{
            'client_id': c.client_id,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'email': c.email,
            'phone': c.phone,
            'passport_number': c.passport_number,
            'passport_expiry': c.passport_expiry.strftime('%Y-%m-%d'),
            'name_latin': c.name_latin,
            'birth_date': c.birth_date.strftime('%Y-%m-%d'),
            'gender': c.gender
        } for c in clients]
        df = pd.DataFrame(data)
        df.to_csv(CSV_EXPORT_PATH, index=False)
        logging.info(f"Клиенты экспортированы в {CSV_EXPORT_PATH}")
    except Exception as e:
        logging.error(f"Ошибка экспорта клиентов: {str(e)}")
        raise
    finally:
        session.close()

def import_clients():
    """Импорт клиентов из CSV."""
    try:
        if not os.path.exists(CSV_IMPORT_PATH):
            raise FileNotFoundError(f"Файл {CSV_IMPORT_PATH} не найден")
        
        session = Session()
        df = pd.read_csv(CSV_IMPORT_PATH)
        for _, row in df.iterrows():
            client = Client(
                first_name=row['first_name'],
                last_name=row['last_name'],
                email=row.get('email'),
                phone=row.get('phone'),
                passport_number=row['passport_number'],
                passport_expiry=pd.to_datetime(row['passport_expiry']).date(),
                name_latin=row['name_latin'],
                birth_date=pd.to_datetime(row['birth_date']).date(),
                gender=row['gender']
            )
            session.add(client)
        session.commit()
        logging.info(f"Клиенты импортированы из {CSV_IMPORT_PATH}")
    except Exception as e:
        session.rollback()
        logging.error(f"Ошибка импорта клиентов: {str(e)}")
        raise
    finally:
        session.close()

def generate_bookings_report():
    """Формирование отчета по бронированиям в Excel."""
    try:
        session = Session()
        bookings = session.query(
            Booking.booking_id,
            Client.first_name,
            Client.last_name,
            Tour.title.label('tour_name'),
            Booking.booking_date,
            Booking.departure_date,
            Booking.return_date,
            Booking.total_price,
            Booking.status
        ).join(Client).join(Tour).all()
        
        data = [{
            'booking_id': b.booking_id,
            'client_name': f"{b.first_name} {b.last_name}",
            'tour_name': b.tour_name,
            'booking_date': b.booking_date.strftime('%Y-%m-%d'),
            'departure_date': b.departure_date.strftime('%Y-%m-%d'),
            'return_date': b.return_date.strftime('%Y-%m-%d'),
            'total_price': b.total_price,
            'status': b.status
        } for b in bookings]
        
        df = pd.DataFrame(data)
        df.to_excel(REPORT_PATH, index=False)
        logging.info(f"Отчет сформирован в {REPORT_PATH}")
    except Exception as e:
        logging.error(f"Ошибка формирования отчета: {str(e)}")
        raise
    finally:
        session.close()