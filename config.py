"""Конфигурационный файл для информационной системы турагентства."""
# Database configuration
DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'travel_agency'
DB_USER = 'postgres'
DB_PASSWORD = 'Savva131105'

# Database URL
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Export paths
CSV_EXPORT_PATH = 'clients_export.csv'
CSV_IMPORT_PATH = 'clients_import.csv'
REPORT_PATH = 'bookings_report.xlsx'