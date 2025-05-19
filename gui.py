"""Модуль для создания графического интерфейса."""
import re
from config import DATABASE_URL, CSV_EXPORT_PATH, CSV_IMPORT_PATH, REPORT_PATH
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QMessageBox, QMenu, QAction, QComboBox,
                             QCheckBox, QDateEdit, QSpinBox, QTextEdit, QGridLayout, QDialog,
                             QGroupBox, QInputDialog)
from PyQt5.QtCore import Qt, QDate
from datetime import datetime, date
import logging
from database import (Session, Country, City, Hotel, TourType, Tour, TourHotel, 
                     Client, Employee, Booking, Payment, Review, Transport, init_db, session_scope,
                     authenticate_user, create_user, get_user_by_username, UserRole)
from reports import export_clients, import_clients, generate_bookings_report

logging.basicConfig(filename='travel_agency.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    pass

class LoginDialog(QDialog):
    """Диалог входа в систему."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Вход в систему")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Форма входа
        form_layout = QGridLayout()
        
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        
        form_layout.addWidget(QLabel("Имя пользователя:"), 0, 0)
        form_layout.addWidget(self.username, 0, 1)
        form_layout.addWidget(QLabel("Пароль:"), 1, 0)
        form_layout.addWidget(self.password, 1, 1)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        login_button = QPushButton("Войти")
        login_button.clicked.connect(self.try_login)
        register_button = QPushButton("Регистрация")
        register_button.clicked.connect(self.show_register_dialog)
        
        buttons_layout.addWidget(login_button)
        buttons_layout.addWidget(register_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def try_login(self):
        """Попытка входа в систему."""
        username = self.username.text().strip()
        password = self.password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
            
        try:
            session = Session()
            user = authenticate_user(session, username, password)
            if user:
                self.parent.current_user = user
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Неверное имя пользователя или пароль")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()
            
    def show_register_dialog(self):
        """Показать диалог регистрации."""
        dialog = RegisterDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.username.setText(dialog.username.text())
            self.password.clear()

class RegisterDialog(QDialog):
    """Диалог регистрации нового пользователя."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Регистрация")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Форма регистрации
        form_layout = QGridLayout()
        
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.role = QComboBox()
        self.role.addItems(["Менеджер", "Руководитель"])
        
        form_layout.addWidget(QLabel("Имя пользователя:"), 0, 0)
        form_layout.addWidget(self.username, 0, 1)
        form_layout.addWidget(QLabel("Пароль:"), 1, 0)
        form_layout.addWidget(self.password, 1, 1)
        form_layout.addWidget(QLabel("Подтвердите пароль:"), 2, 0)
        form_layout.addWidget(self.confirm_password, 2, 1)
        form_layout.addWidget(QLabel("Роль:"), 3, 0)
        form_layout.addWidget(self.role, 3, 1)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        register_button = QPushButton("Зарегистрироваться")
        register_button.clicked.connect(self.try_register)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(register_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def try_register(self):
        """Попытка регистрации нового пользователя."""
        username = self.username.text().strip()
        password = self.password.text()
        confirm_password = self.confirm_password.text()
        role = UserRole.ADMIN if self.role.currentText() == "Руководитель" else UserRole.MANAGER
        
        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return
            
        try:
            session = Session()
            # Проверяем, не существует ли уже пользователь с таким именем
            if get_user_by_username(session, username):
                QMessageBox.warning(self, "Ошибка", "Пользователь с таким именем уже существует")
                return
                
            # Создаем нового пользователя
            create_user(session, username, password, role)
            QMessageBox.information(self, "Успех", "Регистрация успешно завершена")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

class TravelAgencyApp(QMainWindow):
    """Главный класс приложения турагентства."""
    
    def __init__(self):
        """Инициализация приложения с настройкой GUI и базы данных."""
        super().__init__()
        self.setWindowTitle("Турагентство")
        self.setGeometry(100, 100, 1400, 800)
        
        # Инициализация атрибутов поиска
        self.booking_search_client = None
        self.booking_search_tour = None
        self.booking_search_manager = None
        self.booking_search_status = None
        self.booking_search_date_from = None
        self.booking_search_date_to = None
        
        self.current_user = None
        
        # Показываем диалог входа
        login_dialog = LoginDialog(self)
        if login_dialog.exec_() != QDialog.Accepted:
            sys.exit()
            
        self.setup_ui()
        init_db()
        logging.info("Приложение инициализировано")

    @staticmethod
    def validate_email(email):
        """Валидация email адреса."""
        if not email:
            return True  # Email может быть пустым
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError("Неверный формат email адреса")
        return True

    @staticmethod
    def validate_phone(phone):
        """Валидация номера телефона."""
        pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(pattern, phone):
            raise ValidationError("Неверный формат номера телефона")
        return True

    @staticmethod
    def validate_passport(passport):
        """Валидация номера паспорта."""
        if not passport or len(passport) < 6:
            raise ValidationError("Номер паспорта должен содержать минимум 6 символов")
        return True

    @staticmethod
    def validate_name(name, field_name="Имя"):
        """Валидация имени."""
        if not name or len(name.strip()) < 2:
            raise ValidationError(f"{field_name} должно содержать минимум 2 символа")
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s-]+$', name):
            raise ValidationError(f"{field_name} может содержать только буквы, пробелы и дефис")
        return True

    @staticmethod
    def validate_latin_name(name):
        """Валидация имени на латинице."""
        if not name:
            return True  # Может быть пустым
        if not re.match(r'^[a-zA-Z\s-]+$', name):
            raise ValidationError("Имя на латинице может содержать только латинские буквы, пробелы и дефис")
        return True

    def validate_dates(self, birth_date, passport_expiry):
        """Валидация дат."""
        today = date.today()
        
        # Проверка даты рождения
        if birth_date > today:
            raise ValidationError("Дата рождения не может быть в будущем")
        
        # Проверка срока действия паспорта
        if passport_expiry <= today:
            raise ValidationError("Срок действия паспорта истек")
        
        # Проверка возраста
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 18:
            raise ValidationError("Клиент должен быть старше 18 лет")
        if age > 120:
            raise ValidationError("Некорректная дата рождения")
        
        return True

    def validate_client_form(self):
        """Валидация формы клиента."""
        try:
            # Получаем значения полей
            first_name = self.client_first_name.text().strip()
            last_name = self.client_last_name.text().strip()
            name_latin = self.client_name_latin.text().strip()
            passport = self.client_passport.text().strip()
            phone = self.client_phone.text().strip()
            email = self.client_email.text().strip()
            birth_date = self.client_birth_date.date().toPyDate()
            passport_expiry = self.client_passport_expiry.date().toPyDate()

            # Проводим валидацию
            self.validate_name(first_name, "Имя")
            self.validate_name(last_name, "Фамилия")
            self.validate_latin_name(name_latin)
            self.validate_passport(passport)
            self.validate_phone(phone)
            self.validate_email(email)
            self.validate_dates(birth_date, passport_expiry)

            return True

        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
            return False
        except Exception as e:
            logging.error(f"Ошибка валидации: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при валидации данных: {str(e)}")
            return False

    def validate_tour_form(self, dialog):
        """Валидация формы тура."""
        try:
            # Получаем значения полей
            title = dialog.tour_title.text().strip()
            description = dialog.tour_description.toPlainText().strip()
            base_price = float(dialog.tour_base_price.text().strip() or 0)
            tour_type = dialog.tour_type.currentText()

            # Валидация названия
            if not title or len(title) < 5:
                raise ValidationError("Название тура должно содержать минимум 5 символов")

            # Валидация описания
            if not description or len(description) < 20:
                raise ValidationError("Описание тура должно содержать минимум 20 символов")

            # Валидация цены
            if base_price <= 0:
                raise ValidationError("Цена тура должна быть больше 0")

            # Валидация типа тура
            if not tour_type:
                raise ValidationError("Выберите тип тура")

            return True

        except ValueError:
            QMessageBox.warning(self, "Ошибка валидации", "Некорректное значение цены")
            return False
        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
            return False
        except Exception as e:
            logging.error(f"Ошибка валидации тура: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при валидации данных: {str(e)}")
            return False

    def validate_hotel_form(self, dialog):
        """Валидация формы отеля."""
        try:
            # Получаем значения полей
            name = dialog.hotel_name.text().strip()
            city_id = dialog.hotel_city_select.currentData()
            stars = dialog.hotel_stars.value()

            # Валидация названия
            if not name or len(name) < 3:
                raise ValidationError("Название отеля должно содержать минимум 3 символа")

            # Валидация города
            if not city_id:
                raise ValidationError("Выберите город")

            # Валидация звезд
            if stars < 1 or stars > 5:
                raise ValidationError("Количество звезд должно быть от 1 до 5")

            return True

        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
            return False
        except Exception as e:
            logging.error(f"Ошибка валидации отеля: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при валидации данных: {str(e)}")
            return False

    def validate_employee_form(self, dialog):
        """Валидация формы сотрудника."""
        try:
            # Получаем значения полей
            first_name = dialog.employee_first_name.text().strip()
            last_name = dialog.employee_last_name.text().strip()
            position = dialog.employee_position.text().strip()
            salary = float(dialog.employee_salary.text().strip() or 0)
            hire_date = dialog.employee_hire_date.date().toPyDate()

            # Валидация имени и фамилии
            self.validate_name(first_name, "Имя")
            self.validate_name(last_name, "Фамилия")

            # Валидация должности
            if not position or len(position) < 3:
                raise ValidationError("Должность должна содержать минимум 3 символа")

            # Валидация зарплаты
            if salary <= 0:
                raise ValidationError("Зарплата должна быть больше 0")

            # Валидация даты найма
            if hire_date > date.today():
                raise ValidationError("Дата найма не может быть в будущем")

            return True

        except ValueError:
            QMessageBox.warning(self, "Ошибка валидации", "Некорректное значение зарплаты")
            return False
        except ValidationError as e:
            QMessageBox.warning(self, "Ошибка валидации", str(e))
            return False
        except Exception as e:
            logging.error(f"Ошибка валидации сотрудника: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при валидации данных: {str(e)}")
            return False

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Инициализация виджетов поиска
        self.booking_search_client = QLineEdit()
        self.booking_search_client.setPlaceholderText("Поиск по клиенту")
        
        self.booking_search_tour = QLineEdit()
        self.booking_search_tour.setPlaceholderText("Поиск по туру")
        
        self.booking_search_manager = QComboBox()
        self.booking_search_manager.addItem("Все менеджеры")
        
        self.booking_search_status = QComboBox()
        self.booking_search_status.addItems(["Все", "confirmed", "paid", "cancelled", "completed"])
        
        self.booking_search_date_from = QDateEdit()
        self.booking_search_date_from.setCalendarPopup(True)
        self.booking_search_date_from.setDate(QDate.currentDate().addYears(-1))
        
        self.booking_search_date_to = QDateEdit()
        self.booking_search_date_to.setCalendarPopup(True)
        self.booking_search_date_to.setDate(QDate.currentDate().addYears(1))
        
        # Основные вкладки
        self.clients_tab = QWidget()
        self.tours_tab = QWidget()
        self.bookings_tab = QWidget()
        self.hotels_tab = QWidget()
        
        self.tabs.addTab(self.clients_tab, "Клиенты")
        self.tabs.addTab(self.tours_tab, "Туры")
        self.tabs.addTab(self.bookings_tab, "Бронирования")
        self.tabs.addTab(self.hotels_tab, "Отели")
        
        # Добавляем вкладку сотрудников только для руководителя
        if self.current_user.role == UserRole.ADMIN:
            self.employees_tab = QWidget()
            self.tabs.addTab(self.employees_tab, "Сотрудники")
        
        self.setup_clients_tab()
        self.setup_tours_tab()
        self.setup_bookings_tab()
        self.setup_hotels_tab()
        
        if self.current_user.role == UserRole.ADMIN:
            self.setup_employees_tab()

    def setup_clients_tab(self):
        """Настройка вкладки для управления клиентами."""
        layout = QVBoxLayout()
        
        # Добавляем панель поиска
        search_group = QGroupBox("Поиск и фильтры")
        search_layout = QGridLayout()
        
        self.client_search_name = QLineEdit()
        self.client_search_name.setPlaceholderText("Поиск по имени/фамилии")
        self.client_search_name.textChanged.connect(self.filter_clients)
        
        self.client_search_passport = QLineEdit()
        self.client_search_passport.setPlaceholderText("Поиск по номеру паспорта")
        self.client_search_passport.textChanged.connect(self.filter_clients)
        
        self.client_search_phone = QLineEdit()
        self.client_search_phone.setPlaceholderText("Поиск по телефону")
        self.client_search_phone.textChanged.connect(self.filter_clients)
        
        self.client_search_gender = QComboBox()
        self.client_search_gender.addItems(["Все", "Мужской", "Женский"])
        self.client_search_gender.currentTextChanged.connect(self.filter_clients)
        
        search_layout.addWidget(QLabel("Имя/Фамилия:"), 0, 0)
        search_layout.addWidget(self.client_search_name, 0, 1)
        search_layout.addWidget(QLabel("Паспорт:"), 0, 2)
        search_layout.addWidget(self.client_search_passport, 0, 3)
        search_layout.addWidget(QLabel("Телефон:"), 1, 0)
        search_layout.addWidget(self.client_search_phone, 1, 1)
        search_layout.addWidget(QLabel("Пол:"), 1, 2)
        search_layout.addWidget(self.client_search_gender, 1, 3)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить клиента")
        add_button.clicked.connect(self.show_add_client_dialog)
        export_button = QPushButton("Экспорт клиентов")
        export_button.clicked.connect(self.export_clients_data)
        import_button = QPushButton("Импорт клиентов")
        import_button.clicked.connect(self.import_clients_data)
        
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(import_button)
        layout.addLayout(buttons_layout)
        
        # Таблица клиентов
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(9)
        self.clients_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Фамилия", "Имя (лат.)", "Пол", "Дата рождения",
            "Паспорт", "Телефон", "Email"
        ])
        self.clients_table.horizontalHeader().setStretchLastSection(True)
        self.clients_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.clients_table.customContextMenuRequested.connect(self.show_client_context_menu)
        layout.addWidget(self.clients_table)
        
        self.clients_tab.setLayout(layout)
        self.load_clients()

    def load_clients(self):
        """Загрузка клиентов в таблицу."""
        try:
            session = Session()
            clients = session.query(Client).all()
            self.clients_table.setRowCount(len(clients))
            
            for i, client in enumerate(clients):
                self.clients_table.setItem(i, 0, QTableWidgetItem(str(client.client_id)))
                self.clients_table.setItem(i, 1, QTableWidgetItem(client.first_name))
                self.clients_table.setItem(i, 2, QTableWidgetItem(client.last_name))
                self.clients_table.setItem(i, 3, QTableWidgetItem(client.name_latin or ""))
                self.clients_table.setItem(i, 4, QTableWidgetItem(client.gender))
                self.clients_table.setItem(i, 5, QTableWidgetItem(str(client.birth_date)))
                self.clients_table.setItem(i, 6, QTableWidgetItem(client.passport_number))
                self.clients_table.setItem(i, 7, QTableWidgetItem(client.phone))
                self.clients_table.setItem(i, 8, QTableWidgetItem(client.email or ""))
                
            logging.info(f"Загружено {len(clients)} клиентов")
        except Exception as e:
            logging.error(f"Ошибка при загрузке клиентов: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить клиентов: {str(e)}")
        finally:
            session.close()

    def show_add_client_dialog(self):
        """Показать диалог добавления клиента."""
        dialog = AddClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                if not self.validate_client_form(dialog):
                    return
                
                session = Session()
                client = Client(
                    first_name=dialog.client_first_name.text().strip(),
                    last_name=dialog.client_last_name.text().strip(),
                    name_latin=dialog.client_name_latin.text().strip(),
                    passport_number=dialog.client_passport.text().strip(),
                    passport_expiry=dialog.client_passport_expiry.date().toPyDate(),
                    birth_date=dialog.client_birth_date.date().toPyDate(),
                    gender=dialog.client_gender.currentText(),
                    phone=dialog.client_phone.text().strip(),
                    email=dialog.client_email.text().strip() or None,
                    registration_date=datetime.now().date()
                )
                session.add(client)
                session.commit()
                self.load_clients()
                self.load_clients_combo()
                QMessageBox.information(self, "Успех", "Клиент успешно добавлен!")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Ошибка", str(e))
            finally:
                session.close()

    def show_client_context_menu(self, position):
        """Показать контекстное меню для клиента."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec_(self.clients_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.clients_table.currentRow()
            if current_row >= 0:
                client_id = int(self.clients_table.item(current_row, 0).text())
                self.delete_client(client_id)

    def delete_client(self, client_id):
        """Удаление клиента."""
        try:
            reply = QMessageBox.question(self, "Подтверждение", 
                                       "Вы уверены, что хотите удалить этого клиента?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    client = session.query(Client).get(client_id)
                    if client:
                        session.delete(client)
                        session.commit()
                        self.load_clients()
                        self.load_bookings()
                        self.load_clients_combo()
                        QMessageBox.information(self, "Успех", "Клиент успешно удален!")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Клиент не найден")
                finally:
                    session.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def clear_client_form(self):
        """Очистка формы клиента."""
        self.client_first_name.clear()
        self.client_last_name.clear()
        self.client_name_latin.clear()
        self.client_passport.clear()
        self.client_phone.clear()
        self.client_email.clear()
        self.client_passport_expiry.setDate(QDate.currentDate())
        self.client_birth_date.setDate(QDate.currentDate().addYears(-18))
        self.client_gender.setCurrentIndex(0)

    def filter_clients(self):
        """Фильтрация клиентов по заданным критериям."""
        search_name = self.client_search_name.text().lower()
        search_passport = self.client_search_passport.text().lower()
        search_phone = self.client_search_phone.text().lower()
        search_gender = self.client_search_gender.currentText()
        
        for row in range(self.clients_table.rowCount()):
            first_name = self.clients_table.item(row, 1).text().lower()
            last_name = self.clients_table.item(row, 2).text().lower()
            passport = self.clients_table.item(row, 6).text().lower()
            phone = self.clients_table.item(row, 7).text().lower()
            gender = self.clients_table.item(row, 4).text()
            
            name_match = search_name in first_name or search_name in last_name
            passport_match = search_passport in passport
            phone_match = search_phone in phone
            gender_match = search_gender == "Все" or search_gender == gender
            
            self.clients_table.setRowHidden(row, not (
                name_match and passport_match and phone_match and gender_match
            ))

    def setup_tours_tab(self):
        """Настройка вкладки для управления турами."""
        layout = QVBoxLayout()
        
        # Добавляем панель поиска
        search_group = QGroupBox("Поиск и фильтры")
        search_layout = QGridLayout()
        
        self.tour_search_title = QLineEdit()
        self.tour_search_title.setPlaceholderText("Поиск по названию")
        self.tour_search_title.textChanged.connect(self.filter_tours)
        
        self.tour_search_type = QComboBox()
        self.tour_search_type.addItem("Все типы")
        self.tour_search_type.currentTextChanged.connect(self.filter_tours)
        
        self.tour_search_price_min = QSpinBox()
        self.tour_search_price_min.setRange(0, 1000000)
        self.tour_search_price_min.valueChanged.connect(self.filter_tours)
        
        self.tour_search_price_max = QSpinBox()
        self.tour_search_price_max.setRange(0, 1000000)
        self.tour_search_price_max.setValue(1000000)
        self.tour_search_price_max.valueChanged.connect(self.filter_tours)
        
        self.tour_search_active = QComboBox()
        self.tour_search_active.addItems(["Все", "Активные", "Неактивные"])
        self.tour_search_active.currentTextChanged.connect(self.filter_tours)
        
        search_layout.addWidget(QLabel("Название:"), 0, 0)
        search_layout.addWidget(self.tour_search_title, 0, 1)
        search_layout.addWidget(QLabel("Тип:"), 0, 2)
        search_layout.addWidget(self.tour_search_type, 0, 3)
        search_layout.addWidget(QLabel("Цена от:"), 1, 0)
        search_layout.addWidget(self.tour_search_price_min, 1, 1)
        search_layout.addWidget(QLabel("до:"), 1, 2)
        search_layout.addWidget(self.tour_search_price_max, 1, 3)
        search_layout.addWidget(QLabel("Статус:"), 2, 0)
        search_layout.addWidget(self.tour_search_active, 2, 1)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить тур")
        add_button.clicked.connect(self.show_add_tour_dialog)
        manage_types_button = QPushButton("Управление типами туров")
        manage_types_button.clicked.connect(self.show_tour_types_dialog)
        
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(manage_types_button)
        layout.addLayout(buttons_layout)
        
        # Таблица туров
        self.tours_table = QTableWidget()
        self.tours_table.setColumnCount(8)
        self.tours_table.setHorizontalHeaderLabels([
            "ID", "Тип", "Название", "Описание", "Базовая цена", 
            "Кол-во отелей", "Активный", "Создан"
        ])
        self.tours_table.horizontalHeader().setStretchLastSection(True)
        self.tours_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tours_table.customContextMenuRequested.connect(self.show_tour_context_menu)
        layout.addWidget(self.tours_table)
        
        self.tours_tab.setLayout(layout)
        self.load_tour_types()
        self.load_tours()

    def filter_tours(self):
        """Фильтрация туров по заданным критериям."""
        search_title = self.tour_search_title.text().lower()
        search_type = self.tour_search_type.currentText()
        price_min = self.tour_search_price_min.value()
        price_max = self.tour_search_price_max.value()
        search_active = self.tour_search_active.currentText()
        
        for row in range(self.tours_table.rowCount()):
            tour_type = self.tours_table.item(row, 1).text()
            title = self.tours_table.item(row, 2).text().lower()
            price = float(self.tours_table.item(row, 4).text())
            is_active = self.tours_table.item(row, 6).text()
            
            # Проверяем соответствие всем критериям
            title_match = search_title in title
            type_match = search_type == "Все типы" or search_type == tour_type
            price_match = price_min <= price <= price_max
            active_match = (search_active == "Все" or 
                          (search_active == "Активные" and is_active == "Да") or
                          (search_active == "Неактивные" and is_active == "Нет"))
            
            # Скрываем/показываем строку в зависимости от результата фильтрации
            self.tours_table.setRowHidden(row, not (
                title_match and type_match and price_match and active_match
            ))

    def show_tour_context_menu(self, position):
        """Показать контекстное меню для тура."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        edit_hotels_action = menu.addAction("Управление отелями")
        toggle_active_action = menu.addAction("Изменить статус")
        
        action = menu.exec_(self.tours_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.tours_table.currentRow()
            if current_row >= 0:
                tour_id = int(self.tours_table.item(current_row, 0).text())
                self.delete_tour(tour_id)
        elif action == edit_hotels_action:
            current_row = self.tours_table.currentRow()
            if current_row >= 0:
                tour_id = int(self.tours_table.item(current_row, 0).text())
                self.show_tour_hotels_dialog(tour_id)
        elif action == toggle_active_action:
            current_row = self.tours_table.currentRow()
            if current_row >= 0:
                tour_id = int(self.tours_table.item(current_row, 0).text())
                self.toggle_tour_status(tour_id)

    def delete_tour(self, tour_id):
        """Удаление тура."""
        try:
            reply = QMessageBox.question(self, "Подтверждение", 
                                       "Вы уверены, что хотите удалить этот тур?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    tour = session.query(Tour).get(tour_id)
                    if tour:
                        # Проверяем, есть ли связанные бронирования
                        if tour.bookings:
                            QMessageBox.warning(self, "Ошибка",
                                              "Невозможно удалить тур, так как есть связанные бронирования")
                            return
                        
                        session.delete(tour)
                        session.commit()
                        self.load_tours()
                        QMessageBox.information(self, "Успех", "Тур успешно удален!")
                        logging.info(f"Удален тур: {tour_id}")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Тур не найден")
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"Ошибка при удалении тура: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def toggle_tour_status(self, tour_id):
        """Изменение статуса активности тура."""
        try:
            session = Session()
            tour = session.query(Tour).get(tour_id)
            if tour:
                tour.is_active = not tour.is_active
                session.commit()
                self.load_tours()
                status = "активным" if tour.is_active else "неактивным"
                QMessageBox.information(self, "Успех", f"Тур стал {status}!")
                logging.info(f"Изменен статус тура {tour_id} на {status}")
            else:
                QMessageBox.warning(self, "Ошибка", "Тур не найден")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при изменении статуса тура: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def load_tour_types(self, combo_box=None):
        """Загрузка типов туров в комбобокс и поисковый фильтр."""
        try:
            session = Session()
            tour_types = session.query(TourType).all()
            
            # Обновляем поисковый фильтр
            self.tour_search_type.clear()
            self.tour_search_type.addItem("Все типы")
            
            # Если передан конкретный комбобокс, обновляем его
            if combo_box is not None:
                combo_box.clear()
                combo_box.addItem("Выберите тип тура", None)
            
            # Добавляем типы туров
            for tt in tour_types:
                self.tour_search_type.addItem(tt.name)
                if combo_box is not None:
                    combo_box.addItem(tt.name, tt.type_id)
                    
            logging.info(f"Загружено {len(tour_types)} типов туров")
        except Exception as e:
            logging.error(f"Ошибка при загрузке типов туров: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить типы туров: {str(e)}")
        finally:
            session.close()

    def load_tours(self):
        """Загрузка туров в таблицу."""
        try:
            session = Session()
            tours = session.query(Tour).all()
            self.tours_table.setRowCount(len(tours))
            
            for i, tour in enumerate(tours):
                self.tours_table.setItem(i, 0, QTableWidgetItem(str(tour.tour_id)))
                self.tours_table.setItem(i, 1, QTableWidgetItem(tour.tour_type.name))
                self.tours_table.setItem(i, 2, QTableWidgetItem(tour.title))
                self.tours_table.setItem(i, 3, QTableWidgetItem(tour.description))
                self.tours_table.setItem(i, 4, QTableWidgetItem(str(tour.base_price)))
                self.tours_table.setItem(i, 5, QTableWidgetItem(str(len(tour.hotels))))
                self.tours_table.setItem(i, 6, QTableWidgetItem("Да" if tour.is_active else "Нет"))
                self.tours_table.setItem(i, 7, QTableWidgetItem(str(tour.created_at.date())))
                
            logging.info(f"Загружено {len(tours)} туров")
        except Exception as e:
            logging.error(f"Ошибка при загрузке туров: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить туры: {str(e)}")
        finally:
            session.close()

    def load_bookings(self):
        """Загрузка бронирований в таблицу."""
        try:
            with session_scope() as session:
                bookings = session.query(Booking).all()
                self.bookings_table.setRowCount(len(bookings))
                
                for i, booking in enumerate(bookings):
                    self.bookings_table.setItem(i, 0, QTableWidgetItem(str(booking.booking_id)))
                    
                    # Handle client name
                    if booking.client:
                        client_name = f"{booking.client.first_name} {booking.client.last_name}"
                    else:
                        client_name = "Неизвестный клиент"
                    self.bookings_table.setItem(i, 1, QTableWidgetItem(client_name))
                    
                    # Handle tour title
                    tour_title = booking.tour.title if booking.tour else "Неизвестный тур"
                    self.bookings_table.setItem(i, 2, QTableWidgetItem(tour_title))
                    
                    # Handle employee name
                    if booking.employee:
                        employee_name = f"{booking.employee.first_name} {booking.employee.last_name}"
                    else:
                        employee_name = "Неизвестный менеджер"
                    self.bookings_table.setItem(i, 3, QTableWidgetItem(employee_name))
                    
                    # Handle dates
                    self.bookings_table.setItem(i, 4, QTableWidgetItem(str(booking.departure_date)))
                    self.bookings_table.setItem(i, 5, QTableWidgetItem(str(booking.return_date)))
                    self.bookings_table.setItem(i, 6, QTableWidgetItem(str(booking.total_price)))
                    
                    # Calculate total payments
                    total_paid = sum(payment.amount for payment in booking.payments)
                    self.bookings_table.setItem(i, 7, QTableWidgetItem(str(total_paid)))
                    self.bookings_table.setItem(i, 8, QTableWidgetItem(booking.status))
                    
                logging.info(f"Загружено {len(bookings)} бронирований")
        except Exception as e:
            logging.error(f"Ошибка при загрузке бронирований: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить бронирования: {str(e)}")

    def filter_hotels(self):
        """Фильтрация отелей по заданным критериям."""
        search_name = self.hotel_search_name.text().lower()
        search_country = self.hotel_search_country.currentText()
        search_stars = self.hotel_search_stars.currentText()
        search_beach = self.hotel_search_beach.currentText()
        
        for row in range(self.hotels_table.rowCount()):
            name = self.hotels_table.item(row, 1).text().lower()
            country = self.hotels_table.item(row, 2).text()
            stars = self.hotels_table.item(row, 4).text()
            beach_line = self.hotels_table.item(row, 5).text()
            
            # Проверяем соответствие всем критериям
            name_match = search_name in name
            country_match = search_country == "Все страны" or search_country == country
            stars_match = search_stars == "Все" or search_stars == stars
            beach_match = (search_beach == "Все" or 
                         (search_beach == "Первая линия" and beach_line == "Да") or
                         (search_beach == "Не первая линия" and beach_line == "Нет"))
            
            # Скрываем/показываем строку в зависимости от результата фильтрации
            self.hotels_table.setRowHidden(row, not (
                name_match and country_match and stars_match and beach_match
            ))

    def show_add_tour_dialog(self):
        """Показать диалог добавления тура."""
        dialog = AddTourDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                if not self.validate_tour_form(dialog):
                    return
                
                session = Session()
                
                # Создаем новый тур
                tour = Tour(
                    type_id=dialog.tour_type.currentData(),
                    title=dialog.tour_title.text().strip(),
                    description=dialog.tour_description.toPlainText().strip(),
                    base_price=float(dialog.tour_base_price.text().strip()),
                    is_active=dialog.tour_is_active.isChecked()
                )
                
                session.add(tour)
                session.commit()
                
                self.load_tours()
                QMessageBox.information(self, "Успех", "Тур успешно добавлен!")
                logging.info(f"Добавлен новый тур: {tour.tour_id}")
                
            except Exception as e:
                session.rollback()
                logging.error(f"Ошибка при добавлении тура: {str(e)}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить тур: {str(e)}")
            finally:
                session.close()

    def setup_hotels_tab(self):
        """Настройка вкладки для управления отелями."""
        layout = QVBoxLayout()
        
        # Добавляем панель поиска
        search_group = QGroupBox("Поиск и фильтры")
        search_layout = QGridLayout()
        
        self.hotel_search_name = QLineEdit()
        self.hotel_search_name.setPlaceholderText("Поиск по названию")
        self.hotel_search_name.textChanged.connect(self.filter_hotels)
        
        self.hotel_search_country = QComboBox()
        self.hotel_search_country.addItem("Все страны")
        self.hotel_search_country.currentTextChanged.connect(self.filter_hotels)
        
        self.hotel_search_stars = QComboBox()
        self.hotel_search_stars.addItems(["Все", "1", "2", "3", "4", "5"])
        self.hotel_search_stars.currentTextChanged.connect(self.filter_hotels)
        
        self.hotel_search_beach = QComboBox()
        self.hotel_search_beach.addItems(["Все", "Первая линия", "Не первая линия"])
        self.hotel_search_beach.currentTextChanged.connect(self.filter_hotels)
        
        search_layout.addWidget(QLabel("Название:"), 0, 0)
        search_layout.addWidget(self.hotel_search_name, 0, 1)
        search_layout.addWidget(QLabel("Страна:"), 0, 2)
        search_layout.addWidget(self.hotel_search_country, 0, 3)
        search_layout.addWidget(QLabel("Звезды:"), 1, 0)
        search_layout.addWidget(self.hotel_search_stars, 1, 1)
        search_layout.addWidget(QLabel("Расположение:"), 1, 2)
        search_layout.addWidget(self.hotel_search_beach, 1, 3)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить отель")
        add_button.clicked.connect(self.show_add_hotel_dialog)
        manage_countries_button = QPushButton("Управление странами")
        manage_countries_button.clicked.connect(self.show_countries_dialog)
        manage_cities_button = QPushButton("Управление городами")
        manage_cities_button.clicked.connect(self.show_cities_dialog)
        
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(manage_countries_button)
        buttons_layout.addWidget(manage_cities_button)
        layout.addLayout(buttons_layout)
        
        # Таблица отелей
        self.hotels_table = QTableWidget()
        self.hotels_table.setColumnCount(7)
        self.hotels_table.setHorizontalHeaderLabels([
            "ID", "Название", "Страна", "Город", "Звёзды", 
            "Первая линия", "Дата создания"
        ])
        self.hotels_table.horizontalHeader().setStretchLastSection(True)
        self.hotels_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hotels_table.customContextMenuRequested.connect(self.show_hotel_context_menu)
        layout.addWidget(self.hotels_table)
        
        self.hotels_tab.setLayout(layout)
        self.load_hotels()

    def show_add_hotel_dialog(self):
        """Показать диалог добавления отеля."""
        dialog = AddHotelDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                if not self.validate_hotel_form(dialog):
                    return
                
                session = Session()
                hotel = Hotel(
                    city_id=dialog.hotel_city_select.currentData(),
                    name=dialog.hotel_name.text().strip(),
                    stars=dialog.hotel_stars.value(),
                    beach_line=dialog.hotel_beach_line.isChecked()
                )
                session.add(hotel)
                session.commit()
                
                self.load_hotels()
                QMessageBox.information(self, "Успех", "Отель успешно добавлен!")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Ошибка", str(e))
            finally:
                session.close()

    def setup_employees_tab(self):
        """Настройка вкладки для управления сотрудниками."""
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить сотрудника")
        add_button.clicked.connect(self.show_add_employee_dialog)
        
        buttons_layout.addWidget(add_button)
        layout.addLayout(buttons_layout)
        
        # Таблица сотрудников
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(7)
        self.employees_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Фамилия", "Должность", "Дата найма", "Зарплата", "Активный"
        ])
        self.employees_table.horizontalHeader().setStretchLastSection(True)
        self.employees_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.employees_table.customContextMenuRequested.connect(self.show_employee_context_menu)
        layout.addWidget(self.employees_table)
        
        self.employees_tab.setLayout(layout)
        self.load_employees()

    def show_add_employee_dialog(self):
        """Показать диалог добавления сотрудника."""
        dialog = AddEmployeeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                if not self.validate_employee_form(dialog):
                    return
                
                session = Session()
                employee = Employee(
                    first_name=dialog.employee_first_name.text().strip(),
                    last_name=dialog.employee_last_name.text().strip(),
                    position=dialog.employee_position.text().strip(),
                    hire_date=dialog.employee_hire_date.date().toPyDate(),
                    salary=float(dialog.employee_salary.text().strip()),
                    is_active=dialog.employee_active.isChecked()
                )
                session.add(employee)
                session.commit()
                self.load_employees()
                self.load_employees_combo()
                QMessageBox.information(self, "Успех", "Сотрудник успешно добавлен!")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Ошибка", str(e))
            finally:
                session.close()

    def setup_bookings_tab(self):
        """Настройка вкладки для управления бронированиями."""
        layout = QVBoxLayout()
        
        # Создаем таблицу бронирований
        self.bookings_table = QTableWidget()
        self.bookings_table.setColumnCount(9)
        self.bookings_table.setHorizontalHeaderLabels([
            "ID", "Клиент", "Тур", "Менеджер", "Дата отправления",
            "Дата возвращения", "Стоимость", "Оплачено", "Статус"
        ])
        self.bookings_table.horizontalHeader().setStretchLastSection(True)
        self.bookings_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookings_table.customContextMenuRequested.connect(self.show_booking_context_menu)
        
        # Добавляем панель поиска
        search_group = QGroupBox("Поиск и фильтры")
        search_layout = QGridLayout()
        
        # Подключаем сигналы к существующим виджетам
        self.booking_search_client.textChanged.connect(self.filter_bookings)
        self.booking_search_tour.textChanged.connect(self.filter_bookings)
        self.booking_search_manager.currentTextChanged.connect(self.filter_bookings)
        self.booking_search_status.currentTextChanged.connect(self.filter_bookings)
        self.booking_search_date_from.dateChanged.connect(self.filter_bookings)
        self.booking_search_date_to.dateChanged.connect(self.filter_bookings)
        
        # Загружаем менеджеров в комбобокс
        self.load_employees_combo(self.booking_search_manager)
        
        search_layout.addWidget(QLabel("Клиент:"), 0, 0)
        search_layout.addWidget(self.booking_search_client, 0, 1)
        search_layout.addWidget(QLabel("Тур:"), 0, 2)
        search_layout.addWidget(self.booking_search_tour, 0, 3)
        search_layout.addWidget(QLabel("Менеджер:"), 1, 0)
        search_layout.addWidget(self.booking_search_manager, 1, 1)
        search_layout.addWidget(QLabel("Статус:"), 1, 2)
        search_layout.addWidget(self.booking_search_status, 1, 3)
        search_layout.addWidget(QLabel("Дата от:"), 2, 0)
        search_layout.addWidget(self.booking_search_date_from, 2, 1)
        search_layout.addWidget(QLabel("до:"), 2, 2)
        search_layout.addWidget(self.booking_search_date_to, 2, 3)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Создать бронирование")
        add_button.clicked.connect(self.show_add_booking_dialog)
        add_payment_button = QPushButton("Добавить платёж")
        add_payment_button.clicked.connect(self.show_payment_dialog)
        generate_report_button = QPushButton("Создать отчет")
        generate_report_button.clicked.connect(self.generate_bookings_report_action)
        
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(add_payment_button)
        buttons_layout.addWidget(generate_report_button)
        layout.addLayout(buttons_layout)
        
        # Добавляем таблицу в layout
        layout.addWidget(self.bookings_table)
        
        self.bookings_tab.setLayout(layout)
        self.load_bookings()

    def show_add_booking_dialog(self):
        """Показать диалог добавления бронирования."""
        dialog = AddBookingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                with session_scope() as session:
                    # Создаем новое бронирование
                    booking = Booking(
                        client_id=dialog.booking_client.currentData(),
                        tour_id=dialog.booking_tour.currentData(),
                        employee_id=dialog.booking_employee.currentData(),
                        booking_date=datetime.utcnow(),
                        departure_date=dialog.booking_departure.date().toPyDate(),
                        return_date=dialog.booking_return.date().toPyDate(),
                        total_price=float(dialog.booking_total.text()),
                        status=dialog.booking_status.currentText(),
                        is_paid=False,
                        has_prepayment=False
                    )
                    
                    session.add(booking)
                    session.flush()
                    
                    self.load_bookings()
                    QMessageBox.information(self, "Успех", "Бронирование успешно добавлено!")
                    logging.info(f"Добавлено новое бронирование: {booking.booking_id}")
                    
            except ValueError as e:
                QMessageBox.critical(self, "Ошибка", "Неверный формат данных")
                logging.error(f"Ошибка валидации при добавлении бронирования: {str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить бронирование: {str(e)}")
                logging.error(f"Ошибка при добавлении бронирования: {str(e)}")

    def load_clients_combo(self, combo_box=None):
        """Загрузка клиентов в комбобокс."""
        try:
            session = Session()
            clients = session.query(Client).all()
            
            if combo_box is None:
                combo_box = self.booking_client
                
            combo_box.clear()
            combo_box.addItem("Выберите клиента", None)
            for client in clients:
                combo_box.addItem(
                    f"{client.first_name} {client.last_name}", client.client_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def load_tours_combo(self, combo_box=None):
        """Загрузка туров в комбобокс."""
        try:
            session = Session()
            tours = session.query(Tour).filter_by(is_active=True).all()
            
            if combo_box is None:
                combo_box = self.booking_tour
                
            combo_box.clear()
            combo_box.addItem("Выберите тур", None)
            for tour in tours:
                combo_box.addItem(tour.title, tour.tour_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def load_employees_combo(self, combo_box=None):
        """Загрузка сотрудников в комбобокс."""
        try:
            session = Session()
            employees = session.query(Employee).filter_by(is_active=True).all()
            
            if combo_box is None:
                combo_box = self.booking_employee
                
            combo_box.clear()
            combo_box.addItem("Выберите менеджера", None)
            for emp in employees:
                combo_box.addItem(
                    f"{emp.first_name} {emp.last_name}", emp.employee_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def show_payment_dialog(self):
        """Показать диалог добавления платежа."""
        # Получаем выбранное бронирование
        current_row = self.bookings_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите бронирование")
            return
            
        booking_id = int(self.bookings_table.item(current_row, 0).text())
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление платежа")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Форма платежа
        form_layout = QGridLayout()
        
        amount = QLineEdit()
        method = QComboBox()
        method.addItems(["Наличные", "Карта", "Перевод"])
        transaction_id = QLineEdit()
        
        form_layout.addWidget(QLabel("Сумма:"), 0, 0)
        form_layout.addWidget(amount, 0, 1)
        form_layout.addWidget(QLabel("Способ оплаты:"), 1, 0)
        form_layout.addWidget(method, 1, 1)
        form_layout.addWidget(QLabel("ID транзакции:"), 2, 0)
        form_layout.addWidget(transaction_id, 2, 1)
        
        layout.addLayout(form_layout)
        
        # Кнопка добавления
        add_button = QPushButton("Добавить платёж")
        add_button.clicked.connect(lambda: self.add_payment(
            dialog, booking_id, amount, method, transaction_id
        ))
        layout.addWidget(add_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def add_payment(self, dialog, booking_id, amount_widget, method_widget, transaction_widget):
        """Добавление платежа."""
        try:
            amount = float(amount_widget.text().strip())
            method = method_widget.currentText()
            transaction_id = transaction_widget.text().strip()
            
            if amount <= 0:
                QMessageBox.warning(self, "Ошибка", "Введите корректную сумму")
                return
                
            session = Session()
            payment = Payment(
                booking_id=booking_id,
                amount=amount,
                method=method,
                transaction_id=transaction_id if transaction_id else None
            )
            session.add(payment)
            
            # Обновляем статус бронирования если сумма платежей равна стоимости
            booking = session.query(Booking).get(booking_id)
            total_paid = sum(p.amount for p in booking.payments) + amount
            if total_paid >= booking.total_price:
                booking.status = "paid"
                
            session.commit()
            self.load_bookings()
            dialog.accept()
            QMessageBox.information(self, "Успех", "Платёж добавлен!")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()
            
    def update_booking_total(self):
        """Обновление общей стоимости бронирования."""
        try:
            tour_id = self.booking_tour.currentData()
            if not tour_id:
                self.booking_total.clear()
                return
                
            departure = self.booking_departure.date().toPyDate()
            return_date = self.booking_return.date().toPyDate()
            
            if return_date <= departure:
                self.booking_total.clear()
                return
                
            session = Session()
            tour = session.query(Tour).get(tour_id)
            if tour:
                # Базовая стоимость тура
                total = tour.base_price
                
                # Добавляем стоимость за ночи в отелях
                for tour_hotel in tour.hotels:
                    total += tour_hotel.hotel.stars * 1000 * tour_hotel.nights
                    if tour_hotel.hotel.beach_line:
                        total *= 1.2  # Наценка за первую линию
                        
                # Умножаем на количество дней
                days = (return_date - departure).days
                total *= days / 7  # Пересчитываем на реальное количество дней
                
                self.booking_total.setText(f"{total:.2f}")
            else:
                self.booking_total.clear()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()
            
    def clear_booking_form(self):
        """Очистка формы бронирования."""
        self.booking_client.setCurrentIndex(0)
        self.booking_tour.setCurrentIndex(0)
        self.booking_employee.setCurrentIndex(0)
        self.booking_departure.setDate(QDate.currentDate().addDays(1))
        self.booking_return.setDate(QDate.currentDate().addDays(8))
        self.booking_status.setCurrentIndex(0)
        self.booking_total.clear()
        
    def show_booking_context_menu(self, position):
        """Показать контекстное меню для бронирования."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec_(self.bookings_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.bookings_table.currentRow()
            if current_row >= 0:
                booking_id = int(self.bookings_table.item(current_row, 0).text())
                self.delete_booking(booking_id)

    def delete_booking(self, booking_id):
        """Удаление бронирования."""
        try:
            reply = QMessageBox.question(self, "Подтверждение", 
                                       "Вы уверены, что хотите удалить это бронирование?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    booking = session.query(Booking).get(booking_id)
                    if booking:
                        session.delete(booking)
                        session.commit()
                        self.load_bookings()
                        QMessageBox.information(self, "Успех", "Бронирование успешно удалено!")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Бронирование не найдено")
                finally:
                    session.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def filter_bookings(self):
        """Фильтрация бронирований по заданным критериям."""
        search_client = self.booking_search_client.text().lower()
        search_tour = self.booking_search_tour.text().lower()
        search_manager = self.booking_search_manager.currentText()
        search_status = self.booking_search_status.currentText()
        date_from = self.booking_search_date_from.date().toPyDate()
        date_to = self.booking_search_date_to.date().toPyDate()
        
        for row in range(self.bookings_table.rowCount()):
            client = self.bookings_table.item(row, 1).text().lower()
            tour = self.bookings_table.item(row, 2).text().lower()
            manager = self.bookings_table.item(row, 3).text()
            status = self.bookings_table.item(row, 8).text()
            departure_date = datetime.strptime(
                self.bookings_table.item(row, 4).text(), '%Y-%m-%d'
            ).date()
            
            client_match = search_client in client
            tour_match = search_tour in tour
            manager_match = search_manager == "Все менеджеры" or search_manager == manager
            status_match = search_status == "Все" or search_status == status
            date_match = date_from <= departure_date <= date_to
            
            self.bookings_table.setRowHidden(row, not (
                client_match and tour_match and status_match and date_match
            ))

    def show_tour_types_dialog(self):
        """Показать диалог управления типами туров."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Управление типами туров")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Форма добавления типа
        form_layout = QHBoxLayout()
        self.type_name = QLineEdit()
        self.type_description = QLineEdit()
        add_type_button = QPushButton("Добавить тип")
        add_type_button.clicked.connect(lambda: self.add_tour_type(dialog))
        
        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.type_name)
        form_layout.addWidget(QLabel("Описание:"))
        form_layout.addWidget(self.type_description)
        form_layout.addWidget(add_type_button)
        
        layout.addLayout(form_layout)
        
        # Таблица типов
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(3)
        self.types_table.setHorizontalHeaderLabels(["ID", "Название", "Описание"])
        self.types_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.types_table)
        
        dialog.setLayout(layout)
        self.load_tour_types_table()
        dialog.exec_()
        
    def load_tour_types_table(self):
        """Загрузка типов туров в таблицу."""
        try:
            session = Session()
            types = session.query(TourType).all()
            self.types_table.setRowCount(len(types))
            for i, tt in enumerate(types):
                self.types_table.setItem(i, 0, QTableWidgetItem(str(tt.type_id)))
                self.types_table.setItem(i, 1, QTableWidgetItem(tt.name))
                self.types_table.setItem(i, 2, QTableWidgetItem(tt.description or ""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()
            
    def add_tour_type(self, dialog):
        """Добавление нового типа тура."""
        try:
            name = self.type_name.text().strip()
            description = self.type_description.text().strip()
            
            if not name:
                QMessageBox.warning(self, "Ошибка", "Введите название типа тура")
                return
                
            session = Session()
            tour_type = TourType(name=name, description=description)
            session.add(tour_type)
            session.commit()
            
            self.load_tour_types()
            self.load_tour_types_table()
            self.type_name.clear()
            self.type_description.clear()
            QMessageBox.information(dialog, "Успех", "Тип тура добавлен!")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при добавлении типа тура: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()
            
    def add_hotel_to_tour(self):
        """Показать диалог добавления отеля к туру."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление отеля к туру")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Выбор страны и города
        country_layout = QHBoxLayout()
        self.hotel_country = QComboBox()
        self.hotel_city = QComboBox()
        
        country_layout.addWidget(QLabel("Страна:"))
        country_layout.addWidget(self.hotel_country)
        country_layout.addWidget(QLabel("Город:"))
        country_layout.addWidget(self.hotel_city)
        
        layout.addLayout(country_layout)
        
        # Выбор отеля и количества ночей
        hotel_layout = QHBoxLayout()
        self.hotel_select = QComboBox()
        self.nights_count = QSpinBox()
        self.nights_count.setMinimum(1)
        self.nights_count.setMaximum(30)
        
        hotel_layout.addWidget(QLabel("Отель:"))
        hotel_layout.addWidget(self.hotel_select)
        hotel_layout.addWidget(QLabel("Количество ночей:"))
        hotel_layout.addWidget(self.nights_count)
        
        layout.addLayout(hotel_layout)
        
        self.hotel_country_select = QComboBox()
        self.hotel_city_select = QComboBox()
        
        # Основная информация об отеле
        self.hotel_name = QLineEdit()
        self.hotel_stars = QSpinBox()
        self.hotel_stars.setMinimum(1)
        self.hotel_stars.setMaximum(5)
        self.hotel_beach_line = QCheckBox("Первая линия")
        
        # Размещаем элементы в сетке
        form_layout.addWidget(QLabel("Страна:"), 0, 0)
        form_layout.addWidget(self.hotel_country_select, 0, 1)
        form_layout.addWidget(QLabel("Город:"), 0, 2)
        form_layout.addWidget(self.hotel_city_select, 0, 3)
        
        form_layout.addWidget(QLabel("Название:"), 1, 0)
        form_layout.addWidget(self.hotel_name, 1, 1)
        form_layout.addWidget(QLabel("Звёзды:"), 1, 2)
        form_layout.addWidget(self.hotel_stars, 1, 3)
        
        form_layout.addWidget(self.hotel_beach_line, 2, 0)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Загружаем данные и устанавливаем связи
        self.parent.load_countries_combo(self.hotel_country_select)
        self.hotel_country_select.currentIndexChanged.connect(
            lambda: self.parent.load_cities_combo(self.hotel_city_select))

    def show_countries_dialog(self):
        """Показать диалог управления странами."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Управление странами")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Форма добавления страны
        form_layout = QHBoxLayout()
        self.country_name = QLineEdit()
        self.country_visa = QCheckBox("Требуется виза")
        add_country_button = QPushButton("Добавить страну")
        add_country_button.clicked.connect(lambda: self.add_country(dialog))
        
        form_layout.addWidget(QLabel("Название:"))
        form_layout.addWidget(self.country_name)
        form_layout.addWidget(self.country_visa)
        form_layout.addWidget(add_country_button)
        
        layout.addLayout(form_layout)
        
        # Таблица стран
        self.countries_table = QTableWidget()
        self.countries_table.setColumnCount(3)
        self.countries_table.setHorizontalHeaderLabels(["ID", "Название", "Виза"])
        self.countries_table.horizontalHeader().setStretchLastSection(True)
        self.countries_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.countries_table.customContextMenuRequested.connect(
            lambda pos: self.show_country_context_menu(pos, dialog))
        layout.addWidget(self.countries_table)
        
        dialog.setLayout(layout)
        self.load_countries_table()
        dialog.exec_()

    def load_countries_table(self):
        """Загрузка стран в таблицу."""
        try:
            session = Session()
            countries = session.query(Country).all()
            self.countries_table.setRowCount(len(countries))
            
            for i, country in enumerate(countries):
                self.countries_table.setItem(i, 0, QTableWidgetItem(str(country.country_id)))
                self.countries_table.setItem(i, 1, QTableWidgetItem(country.name))
                self.countries_table.setItem(i, 2, QTableWidgetItem(
                    "Да" if country.visa_required else "Нет"))
                
            logging.info(f"Загружено {len(countries)} стран")
        except Exception as e:
            logging.error(f"Ошибка при загрузке стран: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить страны: {str(e)}")
        finally:
            session.close()

    def show_country_context_menu(self, position, dialog):
        """Показать контекстное меню для страны."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec_(self.countries_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.countries_table.currentRow()
            if current_row >= 0:
                country_id = int(self.countries_table.item(current_row, 0).text())
                self.delete_country(country_id, dialog)

    def delete_country(self, country_id, dialog):
        """Удаление страны."""
        try:
            reply = QMessageBox.question(dialog, "Подтверждение", 
                                       "Вы уверены, что хотите удалить эту страну?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    country = session.query(Country).get(country_id)
                    if country:
                        # Проверяем, есть ли связанные города
                        if country.cities:
                            QMessageBox.warning(dialog, "Ошибка",
                                              "Невозможно удалить страну, так как есть связанные города")
                            return
                        
                        session.delete(country)
                        session.commit()
                        self.load_countries_table()
                        self.load_countries_combo()
                        QMessageBox.information(dialog, "Успех", "Страна успешно удалена!")
                        logging.info(f"Удалена страна: {country_id}")
                    else:
                        QMessageBox.warning(dialog, "Ошибка", "Страна не найдена")
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"Ошибка при удалении страны: {str(e)}")
            QMessageBox.critical(dialog, "Ошибка", str(e))

    def add_country(self, dialog):
        """Добавление новой страны."""
        try:
            name = self.country_name.text().strip()
            visa_required = self.country_visa.isChecked()
            
            if not name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название страны")
                return
                
            session = Session()
            # Проверяем, существует ли уже страна с таким названием
            existing = session.query(Country).filter_by(name=name).first()
            if existing:
                QMessageBox.warning(dialog, "Ошибка", "Страна с таким названием уже существует")
                return
                
            country = Country(name=name, visa_required=visa_required)
            session.add(country)
            session.commit()
            
            self.load_countries_table()
            self.load_countries_combo()
            self.country_name.clear()
            self.country_visa.setChecked(False)
            QMessageBox.information(dialog, "Успех", "Страна добавлена!")
            logging.info(f"Добавлена новая страна: {name}")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при добавлении страны: {str(e)}")
            QMessageBox.critical(dialog, "Ошибка", str(e))
        finally:
            session.close()

    def load_countries_combo(self, combo_box=None):
        """Загрузка стран в комбобокс."""
        try:
            session = Session()
            countries = session.query(Country).all()
            
            if combo_box is None:
                combo_box = self.hotel_search_country
                
            combo_box.clear()
            combo_box.addItem("Все страны")
            for country in countries:
                combo_box.addItem(country.name, country.country_id)
                
            logging.info(f"Загружено {len(countries)} стран в комбобокс")
        except Exception as e:
            logging.error(f"Ошибка при загрузке стран в комбобокс: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список стран: {str(e)}")
        finally:
            session.close()

    def show_cities_dialog(self):
        """Показать диалог управления городами."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Управление городами")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Форма добавления города
        form_layout = QGridLayout()
        
        self.city_country = QComboBox()
        self.load_countries_combo(self.city_country)
        
        self.city_name = QLineEdit()
        self.city_popular = QCheckBox("Популярный город")
        add_city_button = QPushButton("Добавить город")
        add_city_button.clicked.connect(lambda: self.add_city(dialog))
        
        form_layout.addWidget(QLabel("Страна:"), 0, 0)
        form_layout.addWidget(self.city_country, 0, 1)
        form_layout.addWidget(QLabel("Название:"), 0, 2)
        form_layout.addWidget(self.city_name, 0, 3)
        form_layout.addWidget(self.city_popular, 1, 0)
        form_layout.addWidget(add_city_button, 1, 3)
        
        layout.addLayout(form_layout)
        
        # Таблица городов
        self.cities_table = QTableWidget()
        self.cities_table.setColumnCount(4)
        self.cities_table.setHorizontalHeaderLabels(["ID", "Страна", "Название", "Популярный"])
        self.cities_table.horizontalHeader().setStretchLastSection(True)
        self.cities_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cities_table.customContextMenuRequested.connect(
            lambda pos: self.show_city_context_menu(pos, dialog))
        layout.addWidget(self.cities_table)
        
        dialog.setLayout(layout)
        self.load_cities_table()
        dialog.exec_()

    def load_cities_table(self):
        """Загрузка городов в таблицу."""
        try:
            session = Session()
            cities = session.query(City).join(Country).all()
            self.cities_table.setRowCount(len(cities))
            
            for i, city in enumerate(cities):
                self.cities_table.setItem(i, 0, QTableWidgetItem(str(city.city_id)))
                self.cities_table.setItem(i, 1, QTableWidgetItem(city.country.name))
                self.cities_table.setItem(i, 2, QTableWidgetItem(city.name))
                self.cities_table.setItem(i, 3, QTableWidgetItem(
                    "Да" if city.is_popular else "Нет"))
                
            logging.info(f"Загружено {len(cities)} городов")
        except Exception as e:
            logging.error(f"Ошибка при загрузке городов: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить города: {str(e)}")
        finally:
            session.close()

    def show_city_context_menu(self, position, dialog):
        """Показать контекстное меню для города."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        toggle_popular_action = menu.addAction("Изменить популярность")
        
        action = menu.exec_(self.cities_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.cities_table.currentRow()
            if current_row >= 0:
                city_id = int(self.cities_table.item(current_row, 0).text())
                self.delete_city(city_id, dialog)
        elif action == toggle_popular_action:
            current_row = self.cities_table.currentRow()
            if current_row >= 0:
                city_id = int(self.cities_table.item(current_row, 0).text())
                self.toggle_city_popular(city_id, dialog)

    def delete_city(self, city_id, dialog):
        """Удаление города."""
        try:
            reply = QMessageBox.question(dialog, "Подтверждение", 
                                       "Вы уверены, что хотите удалить этот город?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    city = session.query(City).get(city_id)
                    if city:
                        # Проверяем, есть ли связанные отели
                        if city.hotels:
                            QMessageBox.warning(dialog, "Ошибка",
                                              "Невозможно удалить город, так как есть связанные отели")
                            return
                        
                        session.delete(city)
                        session.commit()
                        self.load_cities_table()
                        self.load_cities_combo()
                        QMessageBox.information(dialog, "Успех", "Город успешно удален!")
                        logging.info(f"Удален город: {city_id}")
                    else:
                        QMessageBox.warning(dialog, "Ошибка", "Город не найден")
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"Ошибка при удалении города: {str(e)}")
            QMessageBox.critical(dialog, "Ошибка", str(e))

    def toggle_city_popular(self, city_id, dialog):
        """Изменение статуса популярности города."""
        try:
            session = Session()
            city = session.query(City).get(city_id)
            if city:
                city.is_popular = not city.is_popular
                session.commit()
                self.load_cities_table()
                status = "популярным" if city.is_popular else "обычным"
                QMessageBox.information(dialog, "Успех", f"Город стал {status}!")
                logging.info(f"Изменен статус популярности города {city_id}")
            else:
                QMessageBox.warning(dialog, "Ошибка", "Город не найден")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при изменении статуса города: {str(e)}")
            QMessageBox.critical(dialog, "Ошибка", str(e))
        finally:
            session.close()

    def add_city(self, dialog):
        """Добавление нового города."""
        try:
            country_id = self.city_country.currentData()
            name = self.city_name.text().strip()
            is_popular = self.city_popular.isChecked()
            
            if not country_id:
                QMessageBox.warning(dialog, "Ошибка", "Выберите страну")
                return
                
            if not name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название города")
                return
                
            session = Session()
            # Проверяем уникальность города в пределах страны
            existing = session.query(City).filter_by(
                country_id=country_id, name=name).first()
            if existing:
                QMessageBox.warning(dialog, "Ошибка", 
                                  "Город с таким названием уже существует в выбранной стране")
                return
                
            city = City(country_id=country_id, name=name, is_popular=is_popular)
            session.add(city)
            session.commit()
            
            self.load_cities_table()
            self.load_cities_combo()
            self.city_name.clear()
            self.city_popular.setChecked(False)
            QMessageBox.information(dialog, "Успех", "Город добавлен!")
            logging.info(f"Добавлен новый город: {name}")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при добавлении города: {str(e)}")
            QMessageBox.critical(dialog, "Ошибка", str(e))
        finally:
            session.close()

    def load_cities_combo(self, combo_box=None):
        """Загрузка городов в комбобокс."""
        try:
            session = Session()
            cities = session.query(City).join(Country).all()
            
            if combo_box is None:
                combo_box = self.hotel_city_select
                
            combo_box.clear()
            combo_box.addItem("Выберите город", None)
            for city in cities:
                combo_box.addItem(f"{city.name} ({city.country.name})", city.city_id)
                
            logging.info(f"Загружено {len(cities)} городов в комбобокс")
        except Exception as e:
            logging.error(f"Ошибка при загрузке городов в комбобокс: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список городов: {str(e)}")
        finally:
            session.close()

    def show_hotel_context_menu(self, position):
        """Показать контекстное меню для отеля."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        toggle_beach_action = menu.addAction("Изменить расположение")
        
        action = menu.exec_(self.hotels_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.hotels_table.currentRow()
            if current_row >= 0:
                hotel_id = int(self.hotels_table.item(current_row, 0).text())
                self.delete_hotel(hotel_id)
        elif action == toggle_beach_action:
            current_row = self.hotels_table.currentRow()
            if current_row >= 0:
                hotel_id = int(self.hotels_table.item(current_row, 0).text())
                self.toggle_hotel_beach_line(hotel_id)

    def delete_hotel(self, hotel_id):
        """Удаление отеля."""
        try:
            reply = QMessageBox.question(self, "Подтверждение", 
                                       "Вы уверены, что хотите удалить этот отель?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    hotel = session.query(Hotel).get(hotel_id)
                    if hotel:
                        # Проверяем, есть ли связанные туры
                        if hotel.tours:
                            QMessageBox.warning(self, "Ошибка",
                                              "Невозможно удалить отель, так как он используется в турах")
                            return
                        
                        session.delete(hotel)
                        session.commit()
                        self.load_hotels()
                        QMessageBox.information(self, "Успех", "Отель успешно удален!")
                        logging.info(f"Удален отель: {hotel_id}")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Отель не найден")
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"Ошибка при удалении отеля: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def toggle_hotel_beach_line(self, hotel_id):
        """Изменение расположения отеля относительно пляжа."""
        try:
            session = Session()
            hotel = session.query(Hotel).get(hotel_id)
            if hotel:
                hotel.beach_line = not hotel.beach_line
                session.commit()
                self.load_hotels()
                status = "на первой линии" if hotel.beach_line else "не на первой линии"
                QMessageBox.information(self, "Успех", f"Отель теперь {status}!")
                logging.info(f"Изменено расположение отеля {hotel_id}")
            else:
                QMessageBox.warning(self, "Ошибка", "Отель не найден")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при изменении расположения отеля: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def load_hotels(self):
        """Загрузка отелей в таблицу."""
        try:
            session = Session()
            hotels = session.query(Hotel).join(City).join(Country).all()
            self.hotels_table.setRowCount(len(hotels))
            
            for i, hotel in enumerate(hotels):
                self.hotels_table.setItem(i, 0, QTableWidgetItem(str(hotel.hotel_id)))
                self.hotels_table.setItem(i, 1, QTableWidgetItem(hotel.name))
                self.hotels_table.setItem(i, 2, QTableWidgetItem(hotel.city.country.name))
                self.hotels_table.setItem(i, 3, QTableWidgetItem(hotel.city.name))
                self.hotels_table.setItem(i, 4, QTableWidgetItem(str(hotel.stars)))
                self.hotels_table.setItem(i, 5, QTableWidgetItem("Да" if hotel.beach_line else "Нет"))
                self.hotels_table.setItem(i, 6, QTableWidgetItem(str(hotel.created_at.date())))
                
            logging.info(f"Загружено {len(hotels)} отелей")
        except Exception as e:
            logging.error(f"Ошибка при загрузке отелей: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить отели: {str(e)}")
        finally:
            session.close()

    def show_employee_context_menu(self, position):
        """Показать контекстное меню для сотрудника."""
        menu = QMenu()
        delete_action = menu.addAction("Удалить")
        toggle_active_action = menu.addAction("Изменить статус")
        edit_salary_action = menu.addAction("Изменить зарплату")
        
        action = menu.exec_(self.employees_table.mapToGlobal(position))
        if action == delete_action:
            current_row = self.employees_table.currentRow()
            if current_row >= 0:
                employee_id = int(self.employees_table.item(current_row, 0).text())
                self.delete_employee(employee_id)
        elif action == toggle_active_action:
            current_row = self.employees_table.currentRow()
            if current_row >= 0:
                employee_id = int(self.employees_table.item(current_row, 0).text())
                self.toggle_employee_status(employee_id)
        elif action == edit_salary_action:
            current_row = self.employees_table.currentRow()
            if current_row >= 0:
                employee_id = int(self.employees_table.item(current_row, 0).text())
                self.edit_employee_salary(employee_id)

    def delete_employee(self, employee_id):
        """Удаление сотрудника."""
        try:
            reply = QMessageBox.question(self, "Подтверждение", 
                                       "Вы уверены, что хотите удалить этого сотрудника?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                session = Session()
                try:
                    employee = session.query(Employee).get(employee_id)
                    if employee:
                        # Проверяем, есть ли связанные бронирования
                        if employee.bookings:
                            QMessageBox.warning(self, "Ошибка",
                                              "Невозможно удалить сотрудника, так как есть связанные бронирования")
                            return
                        
                        session.delete(employee)
                        session.commit()
                        self.load_employees()
                        self.load_employees_combo()
                        QMessageBox.information(self, "Успех", "Сотрудник успешно удален!")
                        logging.info(f"Удален сотрудник: {employee_id}")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"Ошибка при удалении сотрудника: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def toggle_employee_status(self, employee_id):
        """Изменение статуса активности сотрудника."""
        try:
            session = Session()
            employee = session.query(Employee).get(employee_id)
            if employee:
                employee.is_active = not employee.is_active
                session.commit()
                self.load_employees()
                self.load_employees_combo()
                status = "активным" if employee.is_active else "неактивным"
                QMessageBox.information(self, "Успех", f"Сотрудник стал {status}!")
                logging.info(f"Изменен статус сотрудника {employee_id}")
            else:
                QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при изменении статуса сотрудника: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def edit_employee_salary(self, employee_id):
        """Изменение зарплаты сотрудника."""
        try:
            session = Session()
            employee = session.query(Employee).get(employee_id)
            if not employee:
                QMessageBox.warning(self, "Ошибка", "Сотрудник не найден")
                return
                
            current_salary = float(employee.salary)
            new_salary, ok = QInputDialog.getDouble(
                self, "Изменение зарплаты",
                "Введите новую зарплату:",
                current_salary, 0, 1000000, 2
            )
            
            if ok:
                if new_salary <= 0:
                    QMessageBox.warning(self, "Ошибка", "Зарплата должна быть больше 0")
                    return
                    
                employee.salary = new_salary
                session.commit()
                self.load_employees()
                QMessageBox.information(self, "Успех", "Зарплата успешно изменена!")
                logging.info(f"Изменена зарплата сотрудника {employee_id}: {new_salary}")
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при изменении зарплаты сотрудника: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
        finally:
            session.close()

    def load_employees(self):
        """Загрузка сотрудников в таблицу."""
        try:
            session = Session()
            employees = session.query(Employee).all()
            self.employees_table.setRowCount(len(employees))
            
            for i, employee in enumerate(employees):
                self.employees_table.setItem(i, 0, QTableWidgetItem(str(employee.employee_id)))
                self.employees_table.setItem(i, 1, QTableWidgetItem(employee.first_name))
                self.employees_table.setItem(i, 2, QTableWidgetItem(employee.last_name))
                self.employees_table.setItem(i, 3, QTableWidgetItem(employee.position))
                self.employees_table.setItem(i, 4, QTableWidgetItem(str(employee.hire_date)))
                self.employees_table.setItem(i, 5, QTableWidgetItem(str(employee.salary)))
                self.employees_table.setItem(i, 6, QTableWidgetItem("Да" if employee.is_active else "Нет"))
                
            logging.info(f"Загружено {len(employees)} сотрудников")
        except Exception as e:
            logging.error(f"Ошибка при загрузке сотрудников: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить сотрудников: {str(e)}")
        finally:
            session.close()

    def export_clients_data(self):
        """Экспорт данных клиентов в CSV."""
        try:
            export_clients()
            QMessageBox.information(self, "Успех", f"Данные клиентов экспортированы в {CSV_EXPORT_PATH}")
            logging.info("Выполнен экспорт данных клиентов")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать данные: {str(e)}")
            logging.error(f"Ошибка при экспорте данных клиентов: {str(e)}")

    def import_clients_data(self):
        """Импорт данных клиентов из CSV."""
        try:
            import_clients()
            self.load_clients()
            QMessageBox.information(self, "Успех", f"Данные клиентов импортированы из {CSV_IMPORT_PATH}")
            logging.info("Выполнен импорт данных клиентов")
        except FileNotFoundError:
            QMessageBox.warning(self, "Предупреждение", f"Файл {CSV_IMPORT_PATH} не найден")
            logging.warning(f"Файл для импорта {CSV_IMPORT_PATH} не найден")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать данные: {str(e)}")
            logging.error(f"Ошибка при импорте данных клиентов: {str(e)}")

    def generate_bookings_report_action(self):
        """Создание отчета по бронированиям."""
        try:
            generate_bookings_report()
            QMessageBox.information(self, "Успех", f"Отчет по бронированиям создан в {REPORT_PATH}")
            logging.info("Создан отчет по бронированиям")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать отчет: {str(e)}")
            logging.error(f"Ошибка при создании отчета по бронированиям: {str(e)}")

class AddEmployeeDialog(QDialog):
    """Диалог для добавления нового сотрудника."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Новый сотрудник")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Создаем сетку для формы
        form_layout = QGridLayout()
        
        # Основная информация
        self.employee_first_name = QLineEdit()
        self.employee_last_name = QLineEdit()
        self.employee_position = QLineEdit()
        self.employee_hire_date = QDateEdit()
        self.employee_salary = QLineEdit()
        self.employee_active = QCheckBox("Активный")
        
        self.employee_hire_date.setCalendarPopup(True)
        self.employee_hire_date.setDate(QDate.currentDate())
        self.employee_active.setChecked(True)
        
        # Размещаем элементы в сетке
        form_layout.addWidget(QLabel("Имя:"), 0, 0)
        form_layout.addWidget(self.employee_first_name, 0, 1)
        form_layout.addWidget(QLabel("Фамилия:"), 0, 2)
        form_layout.addWidget(self.employee_last_name, 0, 3)
        
        form_layout.addWidget(QLabel("Должность:"), 1, 0)
        form_layout.addWidget(self.employee_position, 1, 1)
        form_layout.addWidget(QLabel("Дата найма:"), 1, 2)
        form_layout.addWidget(self.employee_hire_date, 1, 3)
        
        form_layout.addWidget(QLabel("Зарплата:"), 2, 0)
        form_layout.addWidget(self.employee_salary, 2, 1)
        form_layout.addWidget(self.employee_active, 2, 2)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)

class AddClientDialog(QDialog):
    """Диалог для добавления нового клиента."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Новый клиент")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Создаем сетку для формы
        form_layout = QGridLayout()
        
        # Основная информация
        self.client_first_name = QLineEdit()
        self.client_last_name = QLineEdit()
        self.client_name_latin = QLineEdit()
        self.client_passport = QLineEdit()
        self.client_passport_expiry = QDateEdit()
        self.client_passport_expiry.setCalendarPopup(True)
        self.client_passport_expiry.setDate(QDate.currentDate())
        
        self.client_birth_date = QDateEdit()
        self.client_birth_date.setCalendarPopup(True)
        self.client_birth_date.setDate(QDate.currentDate().addYears(-18))
        
        self.client_gender = QComboBox()
        self.client_gender.addItems(["Мужской", "Женский"])
        
        self.client_phone = QLineEdit()
        self.client_email = QLineEdit()
        
        # Размещаем элементы в сетке
        form_layout.addWidget(QLabel("Имя:"), 0, 0)
        form_layout.addWidget(self.client_first_name, 0, 1)
        form_layout.addWidget(QLabel("Фамилия:"), 0, 2)
        form_layout.addWidget(self.client_last_name, 0, 3)
        
        form_layout.addWidget(QLabel("Имя (латиницей):"), 1, 0)
        form_layout.addWidget(self.client_name_latin, 1, 1)
        form_layout.addWidget(QLabel("Пол:"), 1, 2)
        form_layout.addWidget(self.client_gender, 1, 3)
        
        form_layout.addWidget(QLabel("Дата рождения:"), 2, 0)
        form_layout.addWidget(self.client_birth_date, 2, 1)
        form_layout.addWidget(QLabel("Телефон:"), 2, 2)
        form_layout.addWidget(self.client_phone, 2, 3)
        
        form_layout.addWidget(QLabel("Email:"), 3, 0)
        form_layout.addWidget(self.client_email, 3, 1)
        form_layout.addWidget(QLabel("Номер паспорта:"), 3, 2)
        form_layout.addWidget(self.client_passport, 3, 3)
        
        form_layout.addWidget(QLabel("Срок действия паспорта:"), 4, 0)
        form_layout.addWidget(self.client_passport_expiry, 4, 1)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)

class AddTourDialog(QDialog):
    """Диалог для добавления нового тура."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Новый тур")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Создаем сетку для формы
        form_layout = QGridLayout()
        
        # Основная информация о туре
        self.tour_type = QComboBox()
        self.tour_title = QLineEdit()
        self.tour_base_price = QLineEdit()
        self.tour_description = QTextEdit()
        self.tour_description.setMaximumHeight(100)
        self.tour_is_active = QCheckBox("Активный")
        self.tour_is_active.setChecked(True)
        
        # Размещаем основные элементы в сетке
        form_layout.addWidget(QLabel("Тип тура:"), 0, 0)
        form_layout.addWidget(self.tour_type, 0, 1)
        form_layout.addWidget(QLabel("Название:"), 0, 2)
        form_layout.addWidget(self.tour_title, 0, 3)
        
        form_layout.addWidget(QLabel("Базовая цена:"), 1, 0)
        form_layout.addWidget(self.tour_base_price, 1, 1)
        form_layout.addWidget(self.tour_is_active, 1, 2)
        
        form_layout.addWidget(QLabel("Описание:"), 2, 0)
        form_layout.addWidget(self.tour_description, 2, 1, 1, 3)
        
        # Секция выбора отелей
        hotels_group = QWidget()
        hotels_layout = QVBoxLayout()
        hotels_group.setLayout(hotels_layout)
        
        hotels_header = QHBoxLayout()
        hotels_header.addWidget(QLabel("Отели тура"))
        add_hotel_button = QPushButton("Добавить отель")
        add_hotel_button.clicked.connect(lambda: self.parent.add_hotel_to_tour(self))
        hotels_header.addWidget(add_hotel_button)
        hotels_layout.addLayout(hotels_header)
        
        # Таблица отелей тура
        self.tour_hotels_table = QTableWidget()
        self.tour_hotels_table.setColumnCount(5)
        self.tour_hotels_table.setHorizontalHeaderLabels([
            "Отель", "Город", "Страна", "Количество ночей", "Действия"
        ])
        self.tour_hotels_table.horizontalHeader().setStretchLastSection(True)
        hotels_layout.addWidget(self.tour_hotels_table)
        
        form_layout.addWidget(hotels_group, 3, 0, 1, 4)
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Загружаем данные
        self.parent.load_tour_types(self.tour_type)

class AddHotelDialog(QDialog):
    """Диалог для добавления нового отеля."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Новый отель")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Создаем сетку для формы
        form_layout = QGridLayout()
        
        # Выбор страны и города
        self.hotel_country_select = QComboBox()
        self.hotel_city_select = QComboBox()
        
        # Основная информация об отеле
        self.hotel_name = QLineEdit()
        self.hotel_stars = QSpinBox()
        self.hotel_stars.setMinimum(1)
        self.hotel_stars.setMaximum(5)
        self.hotel_beach_line = QCheckBox("Первая линия")
        
        # Размещаем элементы в сетке
        form_layout.addWidget(QLabel("Страна:"), 0, 0)
        form_layout.addWidget(self.hotel_country_select, 0, 1)
        form_layout.addWidget(QLabel("Город:"), 0, 2)
        form_layout.addWidget(self.hotel_city_select, 0, 3)
        
        form_layout.addWidget(QLabel("Название:"), 1, 0)
        form_layout.addWidget(self.hotel_name, 1, 1)
        form_layout.addWidget(QLabel("Звёзды:"), 1, 2)
        form_layout.addWidget(self.hotel_stars, 1, 3)
        
        form_layout.addWidget(self.hotel_beach_line, 2, 0)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Загружаем данные и устанавливаем связи
        self.parent.load_countries_combo(self.hotel_country_select)
        self.hotel_country_select.currentIndexChanged.connect(
            lambda: self.parent.load_cities_combo(self.hotel_city_select))

class AddBookingDialog(QDialog):
    """Диалог для добавления нового бронирования."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Новое бронирование")
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout()
        
        # Создаем сетку для формы
        form_layout = QGridLayout()
        
        # Выбор клиента
        self.booking_client = QComboBox()
        self.parent.load_clients_combo(self.booking_client)
        
        # Выбор тура
        self.booking_tour = QComboBox()
        self.parent.load_tours_combo(self.booking_tour)
        self.booking_tour.currentIndexChanged.connect(self.parent.update_booking_total)
        
        # Выбор менеджера
        self.booking_employee = QComboBox()
        self.parent.load_employees_combo(self.booking_employee)
        
        # Даты
        self.booking_departure = QDateEdit()
        self.booking_departure.setCalendarPopup(True)
        self.booking_departure.setDate(QDate.currentDate().addDays(1))
        self.booking_departure.dateChanged.connect(self.parent.update_booking_total)
        
        self.booking_return = QDateEdit()
        self.booking_return.setCalendarPopup(True)
        self.booking_return.setDate(QDate.currentDate().addDays(8))
        self.booking_return.dateChanged.connect(self.parent.update_booking_total)
        
        # Статус и стоимость
        self.booking_status = QComboBox()
        self.booking_status.addItems(["confirmed", "paid", "cancelled", "completed"])
        
        self.booking_total = QLineEdit()
        self.booking_total.setReadOnly(True)
        
        # Размещаем элементы в сетке
        form_layout.addWidget(QLabel("Клиент:"), 0, 0)
        form_layout.addWidget(self.booking_client, 0, 1)
        form_layout.addWidget(QLabel("Тур:"), 0, 2)
        form_layout.addWidget(self.booking_tour, 0, 3)
        
        form_layout.addWidget(QLabel("Менеджер:"), 1, 0)
        form_layout.addWidget(self.booking_employee, 1, 1)
        form_layout.addWidget(QLabel("Статус:"), 1, 2)
        form_layout.addWidget(self.booking_status, 1, 3)
        
        form_layout.addWidget(QLabel("Дата выезда:"), 2, 0)
        form_layout.addWidget(self.booking_departure, 2, 1)
        form_layout.addWidget(QLabel("Дата возвращения:"), 2, 2)
        form_layout.addWidget(self.booking_return, 2, 3)
        
        form_layout.addWidget(QLabel("Стоимость:"), 3, 0)
        form_layout.addWidget(self.booking_total, 3, 1)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)