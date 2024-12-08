import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
import mysql.connector
from PyQt5.QtWidgets import QInputDialog


class TimetableApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the GUI window
        self.setWindowTitle('Timetable SQL Query Generator')
        self.setGeometry(100, 100, 800, 600)

        # Layout and widgets
        layout = QVBoxLayout()

        self.label = QLabel("Drag and drop an Excel file (.xlsx) to begin", self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.query_text = QTextEdit(self)
        self.query_text.setReadOnly(True)
        layout.addWidget(self.query_text)

        # Buttons for navigating queries
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous Query", self)
        self.prev_button.clicked.connect(self.show_previous_query)
        nav_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next Query", self)
        self.next_button.clicked.connect(self.show_next_query)
        nav_layout.addWidget(self.next_button)

        self.jump_unknown_button = QPushButton("Jump to Next Unknown", self)
        self.jump_unknown_button.clicked.connect(self.jump_to_unknown)
        nav_layout.addWidget(self.jump_unknown_button)

        layout.addLayout(nav_layout)

        # Buttons for editing and executing
        self.edit_button = QPushButton("Edit Unknown Values", self)
        self.edit_button.clicked.connect(self.edit_unknowns)
        layout.addWidget(self.edit_button)

        self.execute_button = QPushButton("Execute Queries in Database", self)
        self.execute_button.clicked.connect(self.execute_queries)
        layout.addWidget(self.execute_button)

        self.save_button = QPushButton("Save Queries to File", self)
        self.save_button.clicked.connect(self.save_queries)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        # Allow file drag and drop
        self.setAcceptDrops(True)

        # Variables to hold data
        self.query_list = []
        self.current_index = 0
        self.excel_file = None

    # Enable drag and drop of Excel files
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            if file_path.endswith('.xlsx'):
                self.excel_file = file_path
                self.load_excel_file(file_path)
            else:
                self.show_message("Invalid file", "Please drop an Excel (.xlsx) file.")

    # Load Excel data and generate SQL queries
    def load_excel_file(self, file_path):
        self.query_list = self.generate_sql_queries(file_path)
        if self.query_list:
            self.display_query(self.current_index)

    def generate_sql_queries(self, excel_file):
        try:
            xl = pd.ExcelFile(excel_file)
            all_sql_queries = []

            for sheet in xl.sheet_names:
                df_timetable_full = pd.read_excel(xl, sheet_name=sheet, header=None)
                df_timetable = df_timetable_full.iloc[4:].reset_index(drop=True)
                df_timetable.columns = ['Day', 'Period_1', 'Period_2', 'Period_3', 'Period_4',
                                        'Period_5', 'Period_6', 'Period_7', 'Period_8', 'Period_9', 'Period_10',
                                        'Period_11', 'Period_12']
                df_timetable.dropna(subset=['Day'], inplace=True)
                time_slots = df_timetable_full.iloc[6, 1:].values
                class_names = df_timetable_full.iloc[8, 1:].values
                locations = df_timetable_full.iloc[10, 1:].values
                teacher_name = df_timetable_full.iloc[4, 0]

                for index, row in df_timetable.iloc[1:].iterrows():
                    day = row['Day']
                    if day == "Day / Time":
                        continue

                    for i, period in enumerate(row[1:], start=1):
                        if pd.notna(period):
                            time_slot = time_slots[i - 1]
                            class_name = class_names[i - 1] if pd.notna(class_names[i - 1]) else "Unknown"
                            location = locations[i - 1] if pd.notna(locations[i - 1]) else "Unknown"

                            sql_query = f"INSERT INTO timetable (teacher_name, day, period_number, time_slot, subject, class_name, location) " \
                                        f"VALUES ('{teacher_name}', '{day}', {i}, '{time_slot}', '{period}', '{class_name}', '{location}');"
                            all_sql_queries.append(sql_query)

            return all_sql_queries
        except Exception as e:
            self.show_message("Error", str(e))
            return []

    def display_query(self, index):
        if self.query_list:
            self.query_text.clear()
            query = self.query_list[index]
            self.query_text.setText(query)
            self.highlight_unknowns(query)

    # Highlight unknown values in red
    def highlight_unknowns(self, query):
        cursor = QTextCursor(self.query_text.document())
        format = QTextCharFormat()
        format.setForeground(QColor("red"))

        pos = 0
        while True:
            pos = query.find("Unknown", pos)
            if pos == -1:
                break
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len("Unknown"))
            cursor.mergeCharFormat(format)
            pos += len("Unknown")

    def show_next_query(self):
        self.current_index += 1
        if self.current_index >= len(self.query_list):
            self.current_index = len(self.query_list) - 1
            self.show_message("Info", "This is the last query.")
        self.display_query(self.current_index)

    def show_previous_query(self):
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = 0
            self.show_message("Info", "This is the first query.")
        self.display_query(self.current_index)

    def jump_to_unknown(self):
        for i in range(self.current_index + 1, len(self.query_list)):
            if "Unknown" in self.query_list[i]:
                self.current_index = i
                self.display_query(self.current_index)
                return
        self.show_message("Info", "No more queries with 'Unknown' values.")

    def edit_unknowns(self):
        current_query = self.query_list[self.current_index]
        if "Unknown" in current_query:
            # Use QInputDialog to get user input for class name and location
            class_name, ok_class = QInputDialog.getText(self, "Input", "Enter class name:")
            location, ok_location = QInputDialog.getText(self, "Input", "Enter location:")

            if ok_class and ok_location:
                updated_query = current_query.replace("Unknown", class_name, 1)
                updated_query = updated_query.replace("Unknown", location, 1)
                self.query_list[self.current_index] = updated_query
                self.display_query(self.current_index)
        else:
            self.show_message("Info", "No 'Unknown' values in this query.")

    def execute_queries(self):
        try:
            # Connect to MySQL
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",  # Set your MySQL password
                database="ManipalUniversityJaipur"
            )
            cursor = conn.cursor()

            # Create table if not exists
            create_table_query = """
            CREATE TABLE IF NOT EXISTS timetable (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_name VARCHAR(255),
                day VARCHAR(50),
                period_number INT,
                time_slot VARCHAR(50),
                subject VARCHAR(255),
                class_name VARCHAR(255),
                location VARCHAR(255)
            );
            """
            cursor.execute(create_table_query)

            # Execute each query
            for query in self.query_list:
                cursor.execute(query)

            # Commit the changes and close the connection
            conn.commit()
            conn.close()

            self.show_message("Success", "All queries executed successfully!")
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error: {err}")



    def save_queries(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Queries", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, "w") as file:
                    for query in self.query_list:
                        file.write(query + "\n")
                self.show_message("Success", "Queries saved successfully!")
            except Exception as e:
                self.show_message("Error", str(e))

    def show_message(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()


# Main program
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TimetableApp()
    main_window.show()
    sys.exit(app.exec_())
