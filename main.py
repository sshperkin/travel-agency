"""Основной модуль для запуска приложения."""
from gui import TravelAgencyApp
from PyQt5.QtWidgets import QApplication, QMessageBox
import sys
import logging
from database import init_db, ConnectionError, DatabaseError

# Настройка логирования
logging.basicConfig(
    filename='travel_agency.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Добавляем вывод логов в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

def show_error_message(title, message):
    """Показать сообщение об ошибке."""
    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle(title)
    error_box.setText(message)
    error_box.exec_()

def main():
    """Основная функция запуска приложения."""
    try:
        # Инициализация базы данных
        try:
            init_db()
        except ConnectionError as e:
            logging.critical(f"Критическая ошибка при инициализации базы данных: {str(e)}")
            show_error_message("Ошибка базы данных", 
                             "Не удалось подключиться к базе данных. Проверьте настройки подключения.")
            return 1
        except DatabaseError as e:
            logging.error(f"Ошибка при инициализации базы данных: {str(e)}")
            show_error_message("Ошибка базы данных", 
                             "Произошла ошибка при инициализации базы данных.")
            return 1

        # Запуск приложения
        app = QApplication(sys.argv)
        window = TravelAgencyApp()
        window.show()
        
        logging.info("Приложение успешно запущено")
        return app.exec_()

    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске приложения: {str(e)}")
        show_error_message("Критическая ошибка", 
                         f"Произошла непредвиденная ошибка при запуске приложения: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())