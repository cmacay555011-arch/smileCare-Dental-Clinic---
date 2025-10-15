import sys
import os
import datetime
import pandas as pd
import numpy as np
import mysql.connector
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QComboBox, QTextEdit, QFrame,
                             QCheckBox, QTableWidget, QTableWidgetItem, QMessageBox,
                             QFileDialog, QDateEdit, QHeaderView, QScrollArea, QDialog,
                             QTabWidget, QGridLayout, QGroupBox, QInputDialog)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QKeySequence, QShortcut, QFont, QColor
import matplotlib

matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


# ----------------------- DATABASE CONNECTION -----------------------
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="dental_clinic",
            charset="utf8mb4"
        )
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None


def fetch_data(query, conn, params=None):
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as exc:
        print(f"[fetch_data] SQL Error: {exc}")
        return pd.DataFrame()


# ----------------------- DATABASE SETUP -----------------------
def setup_database():
    """Initialize database tables"""
    try:
        db = get_db_connection()
        if db is not None:
            cursor = db.cursor()

            # Drop old patient_accounts table to ensure clean schema
            try:
                cursor.execute("DROP TABLE IF EXISTS patient_accounts")
                db.commit()
            except:
                pass

            # Create admin accounts table first
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_accounts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            """)

            # Create patient accounts table with correct schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patient_accounts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            """)

            # Create patients table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    birth_date DATE,
                    demographic_type VARCHAR(50),
                    contact VARCHAR(100),
                    type VARCHAR(50) DEFAULT 'Pending'
                )
            """)

            # Create appointments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    patient_name VARCHAR(255) NOT NULL,
                    date DATE NOT NULL,
                    time_slot VARCHAR(50) NOT NULL,
                    services TEXT,
                    status VARCHAR(50) DEFAULT 'Booked'
                )
            """)

            # Create payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    appointment_id INT,
                    amount DECIMAL(10,2),
                    method VARCHAR(50),
                    date_paid DATETIME
                )
            """)

            # Insert default admin if not exists
            try:
                cursor.execute("""
                    INSERT INTO admin_accounts (username, password) 
                    VALUES ('admin', 'admin123')
                """)
                db.commit()
            except:
                pass

            db.close()
            print("Database initialized successfully")
            return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False


# ----------------------- LOGIN WINDOW -----------------------
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smile Care Dental Clinic - Login")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #333333;
                font-family: Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header
        header = QLabel("Smile Care Dental Clinic")
        header.setStyleSheet("""
            background-color: #007acc; 
            color: white; 
            font-size: 22px; 
            font-weight: bold; 
            padding: 20px;
            border-radius: 8px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("Please select login type")
        subtitle.setStyleSheet("font-size: 16px; color: #6c757d; text-align: center;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Admin Login Button
        admin_btn = QPushButton("Admin Login")
        admin_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        admin_btn.setMinimumHeight(50)
        admin_btn.clicked.connect(self.open_admin_login)
        layout.addWidget(admin_btn)

        # Patient/User Login Button
        user_btn = QPushButton("Patient Portal")
        user_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        user_btn.setMinimumHeight(50)
        user_btn.clicked.connect(self.open_patient_portal)
        layout.addWidget(user_btn)

        layout.addStretch()

        self.setLayout(layout)
        self.user_type = None
        self.logged_in_user = None

    def open_admin_login(self):
        admin_login = AdminLogin(self)
        if admin_login.exec() == QDialog.DialogCode.Accepted:
            self.user_type = "admin"
            self.accept()

    def open_patient_portal(self):
        patient_login = PatientLogin(self)
        if patient_login.exec() == QDialog.DialogCode.Accepted:
            self.user_type = "patient"
            self.logged_in_user = patient_login.logged_in_email
            self.accept()


# ----------------------- PATIENT LOGIN/REGISTER -----------------------
class PatientLogin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patient Login - Smile Care Dental Clinic")
        self.setFixedSize(450, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #333333;
                font-family: Arial, sans-serif;
            }
        """)

        self.logged_in_email = None

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("Patient Login/Register")
        header.setStyleSheet("""
            background-color: #28a745; 
            color: white; 
            font-size: 20px; 
            font-weight: bold; 
            padding: 15px;
            border-radius: 8px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Form
        form_layout = QGridLayout()
        form_layout.setSpacing(15)

        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(email_label, 0, 0)
        self.email_entry = QLineEdit()
        self.email_entry.setPlaceholderText("Enter your email")
        self.email_entry.setStyleSheet(
            "font-size: 14px; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.email_entry.setMinimumHeight(40)
        form_layout.addWidget(self.email_entry, 0, 1)

        # Password
        password_label = QLabel("Password:")
        password_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(password_label, 1, 0)
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText("Enter password")
        self.password_entry.setStyleSheet(
            "font-size: 14px; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.password_entry.setMinimumHeight(40)
        form_layout.addWidget(self.password_entry, 1, 1)

        layout.addLayout(form_layout)

        # Login button
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        login_btn.setMinimumHeight(45)
        login_btn.clicked.connect(self.login_patient)
        layout.addWidget(login_btn)

        # Register button
        register_btn = QPushButton("Create New Account")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        register_btn.setMinimumHeight(45)
        register_btn.clicked.connect(self.register_patient)
        layout.addWidget(register_btn)

        # Info label
        info_label = QLabel("Default password for new accounts: 123")
        info_label.setStyleSheet("font-size: 12px; color: #6c757d; text-align: center; font-weight: bold;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        self.setLayout(layout)
        self.password_entry.returnPressed.connect(self.login_patient)
        self.email_entry.setFocus()

    def login_patient(self):
        email = self.email_entry.text().strip()
        password = self.password_entry.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Missing Information", "Please enter both email and password.")
            return

        if '@' not in email:
            QMessageBox.warning(self, "Invalid Email", "Email must contain '@' symbol.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM patient_accounts WHERE email=%s AND password=%s", (email, password))
            patient = cursor.fetchone()
            db.close()

            if patient:
                self.logged_in_email = email
                QMessageBox.information(self, "Login Successful", f"Welcome back, {email}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Failed", "Invalid email or password.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Login error: {str(e)}")

    def register_patient(self):
        email = self.email_entry.text().strip()

        if not email:
            QMessageBox.warning(self, "Missing Information", "Please enter an email address.")
            return

        if '@' not in email:
            QMessageBox.warning(self, "Invalid Email", "Email must contain '@' symbol.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()

            # Check if email already exists
            cursor.execute("SELECT * FROM patient_accounts WHERE email=%s", (email,))
            if cursor.fetchone():
                QMessageBox.warning(self, "Email Exists", "This email is already registered. Please login instead.")
                db.close()
                return

            # Create account with default password
            cursor.execute("INSERT INTO patient_accounts (email, password) VALUES (%s, %s)", (email, "123"))
            db.commit()
            db.close()

            QMessageBox.information(self, "Success",
                                    f"Account created successfully!\n\nEmail: {email}\nPassword: 123\n\nYou can now login.")
            self.password_entry.setText("123")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Registration error: {str(e)}")


# ----------------------- ADMIN LOGIN -----------------------
class AdminLogin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Login - Smile Care Dental Clinic")
        self.setFixedSize(450, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                color: #333333;
                font-family: Arial, sans-serif;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("Admin Login")
        header.setStyleSheet("""
            background-color: #007acc; 
            color: white; 
            font-size: 20px; 
            font-weight: bold; 
            padding: 15px;
            border-radius: 8px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Form
        form_layout = QGridLayout()
        form_layout.setSpacing(15)

        # Username
        username_label = QLabel("Username:")
        username_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(username_label, 0, 0)
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Enter your username")
        self.username_entry.setStyleSheet(
            "font-size: 14px; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.username_entry.setMinimumHeight(40)
        form_layout.addWidget(self.username_entry, 0, 1)

        # Password
        password_label = QLabel("Password:")
        password_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(password_label, 1, 0)
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_entry.setPlaceholderText("Enter your password")
        self.password_entry.setStyleSheet(
            "font-size: 14px; padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.password_entry.setMinimumHeight(40)
        form_layout.addWidget(self.password_entry, 1, 1)

        layout.addLayout(form_layout)

        # Login button
        login_btn = QPushButton("Login to Admin Dashboard")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        login_btn.setMinimumHeight(45)
        login_btn.clicked.connect(self.login_admin)
        layout.addWidget(login_btn)

        # Info label
        info_label = QLabel("Default credentials: admin / admin123")
        info_label.setStyleSheet("font-size: 12px; color: #6c757d; text-align: center; font-weight: bold;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        self.setLayout(layout)
        self.password_entry.returnPressed.connect(self.login_admin)
        self.username_entry.setFocus()

    def login_admin(self):
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Information", "Please enter both username and password.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM admin_accounts WHERE username=%s AND password=%s", (username, password))
            admin = cursor.fetchone()
            db.close()

            if admin:
                QMessageBox.information(self, "Login Successful", f"Welcome back, {username}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Failed",
                                     "Invalid username or password.\n\nDefault credentials:\nUsername: admin\nPassword: admin123")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Login error: {str(e)}")


# ----------------------- ADMIN DASHBOARD -----------------------
class AdminDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard - Smile Care Dental Clinic")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
                color: #333333;
                font-family: Arial, sans-serif;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Admin Dashboard")
        header.setStyleSheet("""
            background-color: #007acc; 
            color: white; 
            font-size: 24px; 
            font-weight: bold; 
            padding: 20px;
            border-radius: 8px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #007acc;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #333333;
                padding: 10px 20px;
                margin: 2px;
                border-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
                color: white;
            }
        """)

        # Dashboard Overview tab
        overview_tab = self.create_overview_tab()
        tabs.addTab(overview_tab, "Dashboard")

        # Patients tab
        patients_tab = self.create_patients_tab()
        tabs.addTab(patients_tab, "Patients")

        # Appointments tab
        appointments_tab = self.create_appointments_tab()
        tabs.addTab(appointments_tab, "Appointments")

        # Payments tab
        payments_tab = self.create_payments_tab()
        tabs.addTab(payments_tab, "Payments")

        layout.addWidget(tabs)

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        logout_btn.setMinimumHeight(45)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Statistics cards
        stats_layout = QHBoxLayout()

        try:
            db = get_db_connection()
            cursor = db.cursor()

            # Get statistics
            cursor.execute("SELECT COUNT(*) FROM patients")
            total_patients = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM appointments")
            total_appointments = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(amount) FROM payments")
            total_revenue = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Booked'")
            pending_appointments = cursor.fetchone()[0]

            db.close()
        except:
            total_patients = 0
            total_appointments = 0
            total_revenue = 0
            pending_appointments = 0

        # Create stat cards
        cards = [
            ("Total Patients", str(total_patients), "#007acc"),
            ("Total Appointments", str(total_appointments), "#28a745"),
            ("Total Revenue", f"PHP {total_revenue:,.2f}", "#ffc107"),
            ("Pending", str(pending_appointments), "#dc3545")
        ]

        for title, value, color in cards:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 8px;
                    padding: 20px;
                }}
            """)
            card_layout = QVBoxLayout(card)

            title_label = QLabel(title)
            title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            value_label = QLabel(value)
            value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            stats_layout.addWidget(card)

        layout.addLayout(stats_layout)

        # Charts
        charts_layout = QHBoxLayout()

        # Appointment Status Chart
        fig1 = Figure(figsize=(6, 4))
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM appointments GROUP BY status")
            status_data = cursor.fetchall()
            db.close()

            if status_data:
                statuses = [row[0] for row in status_data]
                counts = [row[1] for row in status_data]
                colors_chart = ['#007acc', '#28a745', '#ffc107', '#dc3545']
                ax1.pie(counts, labels=statuses, autopct='%1.1f%%', colors=colors_chart[:len(statuses)])
                ax1.set_title('Appointment Status Distribution')
        except:
            ax1.text(0.5, 0.5, 'No data available', ha='center', va='center')

        charts_layout.addWidget(canvas1)

        # Revenue Chart
        fig2 = Figure(figsize=(6, 4))
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("""
                SELECT DATE_FORMAT(date_paid, '%Y-%m') as month, SUM(amount) 
                FROM payments 
                GROUP BY month 
                ORDER BY month DESC 
                LIMIT 6
            """)
            revenue_data = cursor.fetchall()
            db.close()

            if revenue_data:
                months = [row[0] for row in reversed(revenue_data)]
                amounts = [float(row[1]) for row in reversed(revenue_data)]
                ax2.bar(months, amounts, color='#007acc')
                ax2.set_title('Monthly Revenue')
                ax2.set_xlabel('Month')
                ax2.set_ylabel('Revenue (PHP)')
                ax2.tick_params(axis='x', rotation=45)
        except:
            ax2.text(0.5, 0.5, 'No data available', ha='center', va='center')

        fig2.tight_layout()
        charts_layout.addWidget(canvas2)

        layout.addLayout(charts_layout)

        widget.setLayout(layout)
        return widget

    def create_patients_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Button layout
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.load_patients_table(table))
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        edit_btn = QPushButton("Edit Status")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_patient_status(table))
        btn_layout.addWidget(edit_btn)

        layout.addLayout(btn_layout)

        # Table
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333333;
                gridline-color: #d0d0d0;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #007acc;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(table)

        self.load_patients_table(table)

        widget.setLayout(layout)
        return widget

    def load_patients_table(self, table):
        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute(
                "SELECT name, birth_date, demographic_type, contact, type FROM patients ORDER BY name")
            patients = cursor.fetchall()
            db.close()

            table.setRowCount(len(patients))
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Name", "Birth Date", "Type", "Contact", "Status"])

            for row_idx, row_data in enumerate(patients):
                for col_idx, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    if col_idx == 4:
                        if value == "Complete":
                            item.setBackground(QColor("#d4edda"))
                        elif value == "Pending":
                            item.setBackground(QColor("#fff3cd"))
                        elif value == "Cancelled":
                            item.setBackground(QColor("#f8d7da"))
                    table.setItem(row_idx, col_idx, item)

            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error loading patients: {str(e)}")

    def edit_patient_status(self, table):
        current_row = table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a patient to edit.")
            return

        patient_name = table.item(current_row, 0).text()
        current_status = table.item(current_row, 4).text()

        statuses = ["Pending", "Complete", "Cancelled"]
        new_status, ok = QInputDialog.getItem(
            self, "Edit Patient Status",
            f"Change status for {patient_name}:",
            statuses, statuses.index(current_status) if current_status in statuses else 0, False
        )

        if ok and new_status:
            try:
                db = get_db_connection()
                cursor = db.cursor()
                cursor.execute("UPDATE patients SET type = %s WHERE name = %s", (new_status, patient_name))
                db.commit()
                db.close()
                QMessageBox.information(self, "Success", f"Patient status updated to: {new_status}")
                self.load_patients_table(table)
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Error updating status: {str(e)}")

    def create_appointments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Button layout
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.load_appointments_table(table))
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        edit_btn = QPushButton("Edit Status")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_appointment_status(table))
        btn_layout.addWidget(edit_btn)

        layout.addLayout(btn_layout)

        # Table
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333333;
                gridline-color: #d0d0d0;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #007acc;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(table)

        self.load_appointments_table(table)

        widget.setLayout(layout)
        return widget

    def load_appointments_table(self, table):
        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute(
                "SELECT patient_name, date, time_slot, services, status FROM appointments ORDER BY date DESC")
            appointments = cursor.fetchall()
            db.close()

            table.setRowCount(len(appointments))
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Patient", "Date", "Time", "Services", "Status"])

            for row_idx, row_data in enumerate(appointments):
                for col_idx, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    if col_idx == 4:
                        if value == "Complete":
                            item.setBackground(QColor("#d4edda"))
                        elif value == "Booked":
                            item.setBackground(QColor("#d1ecf1"))
                        elif value == "Pending":
                            item.setBackground(QColor("#fff3cd"))
                        elif value == "Cancelled":
                            item.setBackground(QColor("#f8d7da"))
                    table.setItem(row_idx, col_idx, item)

            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error loading appointments: {str(e)}")

    def edit_appointment_status(self, table):
        current_row = table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an appointment to edit.")
            return

        patient_name = table.item(current_row, 0).text()
        appt_date = table.item(current_row, 1).text()
        current_status = table.item(current_row, 4).text()

        statuses = ["Booked", "Pending", "Complete", "Cancelled"]
        new_status, ok = QInputDialog.getItem(
            self, "Edit Appointment Status",
            f"Change status for {patient_name} ({appt_date}):",
            statuses, statuses.index(current_status) if current_status in statuses else 0, False
        )

        if ok and new_status:
            try:
                db = get_db_connection()
                cursor = db.cursor()
                cursor.execute("UPDATE appointments SET status = %s WHERE patient_name = %s AND date = %s",
                               (new_status, patient_name, appt_date))
                db.commit()
                db.close()
                QMessageBox.information(self, "Success", f"Appointment status updated to: {new_status}")
                self.load_appointments_table(table)
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Error updating status: {str(e)}")

    def create_payments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("Refresh Payments")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.load_payments_table(table))
        layout.addWidget(refresh_btn)

        # Table
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333333;
                gridline-color: #d0d0d0;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #007acc;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(table)

        self.load_payments_table(table)

        widget.setLayout(layout)
        return widget

    def load_payments_table(self, table):
        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute("SELECT appointment_id, amount, method, date_paid FROM payments ORDER BY date_paid DESC")
            payments = cursor.fetchall()
            db.close()

            table.setRowCount(len(payments))
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Appointment ID", "Amount", "Method", "Date Paid"])

            for row_idx, row_data in enumerate(payments):
                for col_idx, value in enumerate(row_data):
                    if col_idx == 1:
                        item = QTableWidgetItem(f"PHP {float(value):,.2f}")
                    else:
                        item = QTableWidgetItem(str(value))
                    table.setItem(row_idx, col_idx, item)

            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error loading payments: {str(e)}")

    def logout(self):
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            login_window = LoginWindow()
            if login_window.exec() == QDialog.DialogCode.Accepted:
                if login_window.user_type == "admin":
                    dashboard = AdminDashboard()
                    dashboard.show()
                elif login_window.user_type == "patient":
                    app = DentalBookingApp(login_window.logged_in_user)
                    app.show()


# ----------------------- PATIENT UI -----------------------
class DentalBookingApp(QMainWindow):
    def __init__(self, logged_in_email=None):
        super().__init__()
        self.setWindowTitle("Smilecare Dental Clinic - Patient Portal")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #eaf6fb;
                color: #333333;
                font-family: Arial, sans-serif;
            }
        """)

        self.logged_in_email = logged_in_email
        self.current_selected_appt_id = None
        self.service_vars = {}
        self.selected_services = {}
        self.current_patient_name = ""

        # Default services & prices
        self.services = {
            "Dental Cleaning": 500,
            "Tooth Extraction": 1000,
            "Braces Consultation": 700,
            "Whitening": 1200,
            "Dental Check-up": 300,
            "Root Canal": 3500,
            "Dental Filling": 1500,
            "X-Ray": 800,
            "Gum Treatment": 2000,
            "Dental Implant": 8000
        }

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #eaf6fb; color: #333333;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #007acc; color: white;")
        header.setFixedHeight(120)
        header_layout = QHBoxLayout(header)

        logo_label = QLabel("Smile Care Dental Clinic")
        logo_label.setStyleSheet("font-size: 28px; color: white; font-weight: bold;")
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        # Show logged in email
        if self.logged_in_email:
            email_label = QLabel(f"Logged in: {self.logged_in_email}")
            email_label.setStyleSheet("font-size: 14px; color: white; padding: 10px;")
            header_layout.addWidget(email_label)

        # Logout button in header
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

        main_layout.addWidget(header)

        # Main content
        content_layout = QHBoxLayout()

        # Sidebar
        sidebar = QWidget()
        sidebar.setStyleSheet("background-color: #f2f9ff; color: #333333;")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)

        nav_buttons = [
            ("Patient Info", self.build_patient_tab),
            ("Services", self.build_services_tab),
            ("Appointments", self.build_appointment_tab),
            ("Payment", self.build_payment_tab),
        ]

        for text, func in nav_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f2f9ff;
                    border: none;
                    text-align: left;
                    padding: 15px;
                    font-size: 14px;
                    font-weight: bold;
                    color: #333333;
                }
                QPushButton:hover {
                    background-color: #d0e7ff;
                    color: #000000;
                }
            """)
            btn.clicked.connect(func)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar)

        # Content frame
        self.content_frame = QWidget()
        self.content_frame.setStyleSheet("background-color: white; color: #333333;")
        self.content_layout = QVBoxLayout(self.content_frame)
        content_layout.addWidget(self.content_frame)

        main_layout.addLayout(content_layout)
        self.build_patient_tab()

    def logout(self):
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            login_window = LoginWindow()
            if login_window.exec() == QDialog.DialogCode.Accepted:
                if login_window.user_type == "admin":
                    dashboard = AdminDashboard()
                    dashboard.show()
                elif login_window.user_type == "patient":
                    app = DentalBookingApp(login_window.logged_in_user)
                    app.show()

    def clear_content(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def build_patient_tab(self):
        self.clear_content()

        title = QLabel("Patient Information")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; padding: 20px;")
        self.content_layout.addWidget(title)

        group = QGroupBox("Enter Patient Details")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 16px;
                padding: 20px;
                color: #333333;
                background-color: white;
                border: 2px solid #007acc;
                border-radius: 8px;
            }
            QGroupBox::title {
                color: #007acc;
                background-color: white;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        layout = QGridLayout()
        layout.setSpacing(15)

        name_label = QLabel("Full Name:")
        name_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(name_label, 0, 0)
        self.patient_name = QLineEdit()
        self.patient_name.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.patient_name.setMinimumHeight(35)
        layout.addWidget(self.patient_name, 0, 1)

        bdate_label = QLabel("Birth Date:")
        bdate_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(bdate_label, 1, 0)
        self.patient_bdate = QDateEdit()
        self.patient_bdate.setCalendarPopup(True)
        self.patient_bdate.setDate(QDate.currentDate())
        self.patient_bdate.setDisplayFormat("yyyy-MM-dd")
        self.patient_bdate.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.patient_bdate.setMinimumHeight(35)
        layout.addWidget(self.patient_bdate, 1, 1)

        contact_label = QLabel("Contact Number:")
        contact_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(contact_label, 2, 0)
        self.patient_contact = QLineEdit()
        self.patient_contact.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.patient_contact.setMinimumHeight(35)
        layout.addWidget(self.patient_contact, 2, 1)

        type_label = QLabel("Patient Type (Discount):")
        type_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(type_label, 3, 0)
        self.patient_demographic_type = QComboBox()
        self.patient_demographic_type.addItems(["Regular", "Senior", "Student", "PWD"])
        self.patient_demographic_type.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.patient_demographic_type.setMinimumHeight(35)
        layout.addWidget(self.patient_demographic_type, 3, 1)

        save_btn = QPushButton("Save Patient Information")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)
        save_btn.setMinimumHeight(45)
        save_btn.clicked.connect(self.save_patient)
        layout.addWidget(save_btn, 4, 0, 1, 2)

        group.setLayout(layout)
        self.content_layout.addWidget(group)
        self.content_layout.addStretch()

    def save_patient(self):
        name = self.patient_name.text().strip()
        bdate = self.patient_bdate.date().toString("yyyy-MM-dd")
        demographic_type = self.patient_demographic_type.currentText()
        contact = self.patient_contact.text().strip()

        if not name or not contact:
            QMessageBox.warning(self, "Missing Information", "Please fill out all fields.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO patients (name, birth_date, demographic_type, contact, type) VALUES (%s, %s, %s, %s, %s)",
                (name, bdate, demographic_type, contact, "Pending")
            )
            db.commit()
            db.close()
            QMessageBox.information(self, "Success", f"Patient {name} saved successfully!")
            self.patient_name.clear()
            self.patient_demographic_type.setCurrentIndex(0)
            self.patient_contact.clear()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")

    def build_services_tab(self):
        self.clear_content()

        title = QLabel("Dental Services")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; padding: 20px;")
        self.content_layout.addWidget(title)

        group = QGroupBox("Select Services Needed")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 16px;
                padding: 15px;
                color: #333333;
                background-color: white;
                border: 2px solid #007acc;
                border-radius: 8px;
            }
            QGroupBox::title {
                color: #007acc;
                background-color: white;
            }
        """)
        services_layout = QVBoxLayout()

        self.service_vars = {}
        for service, price in self.services.items():
            chk = QCheckBox(f"{service} - PHP {price:,.2f}")
            chk.setStyleSheet("font-size: 14px; padding: 10px;")
            chk.stateChanged.connect(self.update_selected_services)
            services_layout.addWidget(chk)
            self.service_vars[service] = chk

        group.setLayout(services_layout)

        scroll = QScrollArea()
        scroll.setWidget(group)
        scroll.setWidgetResizable(True)
        self.content_layout.addWidget(scroll)

    def update_selected_services(self):
        self.selected_services = {s: p for s, p in self.services.items()
                                  if self.service_vars.get(s) and self.service_vars[s].isChecked()}

    def build_appointment_tab(self):
        self.clear_content()

        title = QLabel("Book Appointment")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; padding: 20px;")
        self.content_layout.addWidget(title)

        group = QGroupBox("Schedule Your Appointment")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 16px;
                padding: 20px;
                color: #333333;
                border: 2px solid #007acc;
                border-radius: 8px;
            }
        """)
        layout = QGridLayout()
        layout.setSpacing(15)

        date_label = QLabel("Appointment Date:")
        date_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(date_label, 0, 0)
        self.appointment_date = QDateEdit()
        self.appointment_date.setCalendarPopup(True)
        self.appointment_date.setDate(QDate.currentDate())
        self.appointment_date.setDisplayFormat("yyyy-MM-dd")
        self.appointment_date.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.appointment_date.setMinimumHeight(35)
        layout.addWidget(self.appointment_date, 0, 1)

        time_label = QLabel("Time Slot:")
        time_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(time_label, 1, 0)
        self.appointment_time = QComboBox()
        self.appointment_time.addItems(["9:00 AM", "10:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"])
        self.appointment_time.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.appointment_time.setMinimumHeight(35)
        layout.addWidget(self.appointment_time, 1, 1)

        book_btn = QPushButton("Book Appointment")
        book_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        book_btn.setMinimumHeight(45)
        book_btn.clicked.connect(self.book_appointment)
        layout.addWidget(book_btn, 2, 0, 1, 2)

        group.setLayout(layout)
        self.content_layout.addWidget(group)
        self.content_layout.addStretch()

    def book_appointment(self):
        patient = self.patient_name.text().strip()
        date = self.appointment_date.date().toString("yyyy-MM-dd")
        time = self.appointment_time.currentText()

        if not patient:
            QMessageBox.warning(self, "Missing Information", "Please save patient information first.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            services = ", ".join(self.selected_services.keys()) if self.selected_services else "No services"
            cursor.execute(
                "INSERT INTO appointments (patient_name, date, time_slot, services, status) VALUES (%s, %s, %s, %s, %s)",
                (patient, date, time, services, "Booked"))
            db.commit()
            db.close()
            QMessageBox.information(self, "Success",
                                    f"Appointment booked!\nPatient: {patient}\nDate: {date}\nTime: {time}")

            for chk in self.service_vars.values():
                chk.setChecked(False)
            self.selected_services = {}
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error: {str(e)}")

    def build_payment_tab(self):
        self.clear_content()

        title = QLabel("Payment & Receipt")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; padding: 20px;")
        self.content_layout.addWidget(title)

        group = QGroupBox("Process Payment and Generate Receipt")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; 
                font-size: 16px;
                padding: 20px;
                border: 2px solid #007acc;
                border-radius: 8px;
            }
        """)
        layout = QGridLayout()
        layout.setSpacing(15)

        patient_name = self.patient_name.text().strip()
        appointments = []

        if patient_name:
            try:
                db = get_db_connection()
                if db is not None:
                    cursor = db.cursor()
                    cursor.execute(
                        "SELECT id, patient_name, date, time_slot, services FROM appointments WHERE patient_name = %s AND status != 'Cancelled' ORDER BY date DESC",
                        (patient_name,))
                    appointments = cursor.fetchall()
                    db.close()
            except:
                appointments = []

        self.appointment_map = {}
        appointment_display_values = []
        for row in appointments:
            appt_id, pname, adate, tslot, services = row
            display = f"{adate} | {tslot} | {services}"
            appointment_display_values.append(display)
            self.appointment_map[display] = {
                "id": appt_id,
                "patient": pname,
                "date": adate,
                "time": tslot,
                "services": services
            }

        if not appointment_display_values:
            no_appt_label = QLabel("No appointments found. Please book an appointment first.")
            no_appt_label.setStyleSheet("color: #dc3545; font-size: 14px; font-weight: bold; padding: 10px;")
            layout.addWidget(no_appt_label, 0, 0, 1, 2)
        else:
            self.current_appointment_display = appointment_display_values[0]
            appt_info_label = QLabel(f"Current Appointment: {self.current_appointment_display}")
            appt_info_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold; padding: 10px;")
            layout.addWidget(appt_info_label, 0, 0, 1, 2)

        method_label = QLabel("Payment Method:")
        method_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(method_label, 1, 0)
        self.payment_method = QComboBox()
        self.payment_method.addItems(["Cash", "GCash", "Credit/Debit Card"])
        self.payment_method.setStyleSheet("font-size: 14px; padding: 8px; border: 1px solid #ccc;")
        self.payment_method.setMinimumHeight(35)
        layout.addWidget(self.payment_method, 1, 1)

        total_label = QLabel("Total Amount:")
        total_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(total_label, 2, 0)
        self.total_amount_label = QLabel("PHP 0.00")
        self.total_amount_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c; padding: 8px;")
        layout.addWidget(self.total_amount_label, 2, 1)

        calc_btn = QPushButton("Calculate Total & Discount")
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        calc_btn.setMinimumHeight(40)
        calc_btn.clicked.connect(self.calculate_total)
        layout.addWidget(calc_btn, 3, 0)

        receipt_btn = QPushButton("Generate Receipt & Save Payment")
        receipt_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        receipt_btn.setMinimumHeight(40)
        receipt_btn.clicked.connect(self.generate_receipt)
        layout.addWidget(receipt_btn, 3, 1)

        receipt_label = QLabel("Receipt:")
        receipt_label.setStyleSheet("color: #333333; font-size: 14px; font-weight: bold;")
        layout.addWidget(receipt_label, 4, 0, 1, 2)

        self.receipt_box = QTextEdit()
        self.receipt_box.setReadOnly(True)
        self.receipt_box.setMinimumHeight(400)
        self.receipt_box.setStyleSheet(
            "font-size: 14px; font-family: 'Courier New'; padding: 10px; border: 1px solid #ccc;")
        layout.addWidget(self.receipt_box, 5, 0, 1, 2)

        group.setLayout(layout)
        self.content_layout.addWidget(group)
        self.content_layout.addStretch()

        if appointment_display_values:
            self.calculate_total()

    def calculate_total(self):
        patient_name = self.patient_name.text().strip()
        if not patient_name:
            self.total_amount_label.setText("PHP 0.00")
            QMessageBox.warning(self, "No Patient", "Please save patient information first.")
            return

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute(
                "SELECT id, patient_name, date, time_slot, services FROM appointments WHERE patient_name = %s AND status != 'Cancelled' ORDER BY date DESC LIMIT 1",
                (patient_name,))
            appointment = cursor.fetchone()
            db.close()

            if not appointment:
                self.total_amount_label.setText("PHP 0.00")
                QMessageBox.warning(self, "No Appointment", "No appointments found for this patient.")
                return

            appt_id, pname, adate, tslot, services_str = appointment

            # Calculate base total from services
            base_total = 0
            for service_name, service_price in self.services.items():
                if service_name in services_str:
                    base_total += service_price

            # Get patient type for discount
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("SELECT demographic_type FROM patients WHERE name = %s", (patient_name,))
            result = cursor.fetchone()
            db.close()

            patient_type = result[0] if result else "Regular"

            # Apply discounts
            discount_rate = 0
            if patient_type == "Senior":
                discount_rate = 0.20
            elif patient_type == "Student":
                discount_rate = 0.10
            elif patient_type == "PWD":
                discount_rate = 0.20

            discount_amount = base_total * discount_rate
            final_total = base_total - discount_amount

            self.current_selected_appt_id = appt_id
            self.current_patient_name = patient_name

            # Display the total
            self.total_amount_label.setText(f"PHP {final_total:,.2f}")

            # Show discount info
            if discount_rate > 0:
                discount_info = f"Base: PHP {base_total:,.2f} - {discount_rate * 100:.0f}% discount (PHP {discount_amount:,.2f}) = PHP {final_total:,.2f}"
                self.total_amount_label.setToolTip(discount_info)
            else:
                self.total_amount_label.setToolTip(f"Base amount: PHP {base_total:,.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error calculating total: {str(e)}")

    def generate_receipt(self):
        patient_name = self.patient_name.text().strip()
        if not patient_name:
            QMessageBox.warning(self, "No Patient", "Please save patient information first.")
            return

        if self.current_selected_appt_id is None:
            QMessageBox.warning(self, "Error", "Please calculate the total first.")
            return

        payment_method = self.payment_method.currentText()

        try:
            db = get_db_connection()
            if db is None:
                QMessageBox.critical(self, "Database Error", "Cannot connect to database.")
                return
            cursor = db.cursor()
            cursor.execute(
                "SELECT date, time_slot, services FROM appointments WHERE id = %s",
                (self.current_selected_appt_id,))
            appointment = cursor.fetchone()
            db.close()

            if not appointment:
                QMessageBox.warning(self, "Error", "Appointment not found.")
                return

            appt_date, appt_time, appt_services = appointment

            # Calculate total again to ensure accuracy
            self.calculate_total()
            total_amount_text = self.total_amount_label.text().replace('PHP', '').replace(',', '').strip()
            total_amount = float(total_amount_text)

            # Generate receipt text
            receipt_text = f"""
=====================================
  SMILE CARE DENTAL CLINIC
    OFFICIAL RECEIPT
=====================================
Patient: {patient_name}
Date: {appt_date}
Time: {appt_time}
Payment Method: {payment_method}
=====================================
             SERVICES
=====================================
"""

            services_list = appt_services.split(', ') if appt_services != "No services" else []
            for service in services_list:
                if service in self.services:
                    price = self.services[service]
                    receipt_text += f"  • {service:<25} PHP {price:>8,.2f}\n"

            receipt_text += f"""=====================================
Total Amount: PHP {total_amount:,.2f}
Payment Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
=====================================

Thank you for choosing Smile Care Dental Clinic!
"""

            self.receipt_box.setText(receipt_text)

            # Save payment to database
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO payments (appointment_id, amount, method, date_paid) VALUES (%s, %s, %s, %s)",
                (self.current_selected_appt_id, total_amount, payment_method, datetime.datetime.now())
            )
            db.commit()
            db.close()

            QMessageBox.information(self, "Success", "Payment saved successfully and receipt generated!")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error saving payment: {str(e)}")


# ----------------------- MAIN APPLICATION -----------------------
def main():
    # Initialize database
    setup_database()

    # Start the application
    app = QApplication(sys.argv)

    # Show login window first
    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        if login_window.user_type == "admin":
            dashboard = AdminDashboard()
            dashboard.show()
        elif login_window.user_type == "patient":
            dental_app = DentalBookingApp(login_window.logged_in_user)
            dental_app.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()