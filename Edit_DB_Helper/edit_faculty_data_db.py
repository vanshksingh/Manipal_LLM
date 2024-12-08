import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout
)
from PyQt5.QtCore import Qt
import mysql.connector
from fuzzywuzzy import process


class FacultyDatabaseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Faculty Database Management')
        self.setGeometry(100, 100, 1000, 600)

        # Database connection parameters
        self.host = 'localhost'
        self.user = 'root'
        self.password = ''
        self.database = 'ManipalUniversityJaipur'

        # Connect to the MySQL database
        self.connection = self.create_connection()

        # Layout for the form
        self.layout = QVBoxLayout()

        # Search layout
        self.search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Professor by Name")
        self.search_button = QPushButton('Search')
        self.search_button.clicked.connect(self.search_professor)
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.search_button)
        self.layout.addLayout(self.search_layout)

        # Table widget to display data
        self.table_widget = QTableWidget()
        self.layout.addWidget(self.table_widget)

        # Load the data initially
        self.load_data()

        # Add buttons for delete and add operations
        self.button_layout = QHBoxLayout()
        self.add_button = QPushButton('Add New Faculty')
        self.add_button.clicked.connect(self.add_new_faculty)
        self.delete_button = QPushButton('Delete Selected Faculty')
        self.delete_button.clicked.connect(self.delete_selected_row)
        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.delete_button)
        self.layout.addLayout(self.button_layout)

        # Connect the itemChanged signal to handle editing in place
        self.table_widget.itemChanged.connect(self.update_db_from_table)

        self.setLayout(self.layout)

    def create_connection(self):
        """Creates a connection to the MySQL database."""
        connection = None
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                passwd=self.password,
                database=self.database
            )
            print("Connection to MySQL DB successful")
        except mysql.connector.Error as e:
            print(f"The error '{e}' occurred")
            QMessageBox.critical(self, "Database Connection Error", f"Failed to connect to database:\n{e}")
            sys.exit(1)  # Exit the application if the connection fails
        return connection

    def load_data(self):
        """Load data from the database into the table."""
        query = """
            SELECT id, name, email, ext_number, phone_number, block_location, 
                   floor_location, room_number, workstation, research_area, google_scholar_link 
            FROM FacultyInfo
        """
        cursor = self.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        # Set table column headers
        column_headers = [
            'ID', 'Name', 'Email', 'Ext. Number', 'Phone Number', 'Block',
            'Floor', 'Room', 'Workstation', 'Research Area', 'Google Scholar Link'
        ]
        self.table_widget.setColumnCount(len(column_headers))
        self.table_widget.setHorizontalHeaderLabels(column_headers)
        self.table_widget.setRowCount(len(results) + 1)  # Extra row for adding new faculty

        # Populate the table with data from the database
        for row_idx, row_data in enumerate(results):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data))
                item.setFlags(item.flags() | Qt.ItemIsEditable)  # Ensure items are editable
                self.table_widget.setItem(row_idx, col_idx, item)

        # Add an empty row for adding new faculty
        new_label = QTableWidgetItem('New')
        new_label.setFlags(Qt.ItemIsEnabled)  # Make the 'New' label non-editable
        self.table_widget.setItem(len(results), 0, new_label)  # First column is 'New'

        # Initialize other cells in the 'New' row with empty QTableWidgetItems
        for col in range(1, self.table_widget.columnCount()):
            empty_item = QTableWidgetItem('')
            self.table_widget.setItem(len(results), col, empty_item)

        # Allow double-clicking for editing
        self.table_widget.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)

    def update_db_from_table(self, item):
        """Update the database when a table cell is edited."""
        row = item.row()
        column = item.column()

        # If it's the 'New' row, do not process
        if self.table_widget.item(row, 0).text() == 'New':
            return

        # Get the ID of the faculty from the first column (ID column)
        faculty_id = self.table_widget.item(row, 0).text()

        # Ensure faculty_id is valid (numeric)
        if not faculty_id.isdigit():
            return

        # Map columns to database field names
        columns = [
            'id', 'name', 'email', 'ext_number', 'phone_number', 'block_location',
            'floor_location', 'room_number', 'workstation', 'research_area', 'google_scholar_link'
        ]

        # Update the corresponding column in the database
        column_name = columns[column]
        new_value = item.text()

        query = f"UPDATE FacultyInfo SET {column_name} = %s WHERE id = %s"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (new_value, faculty_id))
            self.connection.commit()
            # Optionally, log the update or update the UI in another way
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Update Error", f"Failed to update record:\n{e}")
            self.connection.rollback()

    def delete_selected_row(self):
        """Delete the selected faculty from the database and table."""
        selected_row = self.table_widget.currentRow()

        # Get the faculty ID from the first column
        faculty_id_item = self.table_widget.item(selected_row, 0)
        if faculty_id_item is None:
            QMessageBox.warning(self, "Error", "No faculty selected.")
            return

        faculty_id = faculty_id_item.text()

        if faculty_id == 'New':
            QMessageBox.warning(self, "Error", "Cannot delete the new faculty row.")
            return

        # Confirm deletion
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete the selected faculty?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm == QMessageBox.No:
            return

        query = "DELETE FROM FacultyInfo WHERE id = %s"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (faculty_id,))
            self.connection.commit()
            # Remove the row from the table
            self.table_widget.removeRow(selected_row)
            QMessageBox.information(self, "Success", "Faculty deleted successfully!")
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Deletion Error", f"Failed to delete record:\n{e}")
            self.connection.rollback()

    def add_new_faculty(self):
        """Add a new faculty record to the database."""
        row_count = self.table_widget.rowCount() - 1  # Last row is the 'New' row

        # Helper function to get text from a cell and handle None values
        def get_cell_text(row, col):
            item = self.table_widget.item(row, col)
            if item and item.text().strip():
                return item.text().strip()
            else:
                return ''  # Return an empty string if the cell is empty

        # Collect data from the 'New' row
        name = get_cell_text(row_count, 1)
        email = get_cell_text(row_count, 2)
        ext = get_cell_text(row_count, 3)
        phone = get_cell_text(row_count, 4)
        block = get_cell_text(row_count, 5)
        floor = get_cell_text(row_count, 6)
        room = get_cell_text(row_count, 7)
        workstation = get_cell_text(row_count, 8)
        research_area = get_cell_text(row_count, 9)
        google_scholar = get_cell_text(row_count, 10)


        if not name or not email:
            QMessageBox.warning(self, "Error", "Name and Email are required fields.")
            return

        query = """
            INSERT INTO FacultyInfo (
                name, email, ext_number, phone_number, 
                block_location, floor_location, room_number, 
                workstation, research_area, google_scholar_link
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (
                name, email, ext, phone, block, floor, room, workstation, research_area, google_scholar
            ))
            self.connection.commit()
            # Reload the table to reflect the new faculty
            self.load_data()
            QMessageBox.information(self, "Success", "New faculty added successfully!")
        except mysql.connector.Error as e:
            QMessageBox.critical(self, "Insertion Error", f"Failed to add new faculty:\n{e}")
            self.connection.rollback()

    def search_professor(self):
        """Search for a professor by name using fuzzy matching."""
        search_text = self.search_input.text().strip()
        if not search_text:
            QMessageBox.warning(self, "Input Error", "Please enter a name to search.")
            return

        # Get all names from the table excluding the 'New' row
        names = [
            self.table_widget.item(row, 1).text()
            for row in range(self.table_widget.rowCount() - 1)
            if self.table_widget.item(row, 1) is not None
        ]

        if not names:
            QMessageBox.warning(self, "Search Error", "No faculty records available to search.")
            return

        # Use fuzzy matching to find the best match
        best_match = process.extractOne(search_text, names)

        if best_match and best_match[1] >= 60:  # You can adjust the threshold as needed
            match_name = best_match[0]
            match_row = next(
                (row for row in range(self.table_widget.rowCount() - 1)
                 if self.table_widget.item(row, 1).text() == match_name),
                None
            )
            if match_row is not None:
                # Scroll to the matching row
                self.table_widget.scrollToItem(self.table_widget.item(match_row, 1))
                # Highlight the matching row
                self.table_widget.selectRow(match_row)
                QMessageBox.information(self, "Search Result", f"Found match: {match_name}")
            else:
                QMessageBox.warning(self, "Search Error", "No matching professor found.")
        else:
            QMessageBox.warning(self, "Search Error", "No matching professor found.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FacultyDatabaseApp()
    window.show()
    sys.exit(app.exec_())
