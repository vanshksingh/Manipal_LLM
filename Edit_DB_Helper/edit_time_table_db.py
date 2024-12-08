import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QComboBox, QDialog, QLabel, QDialogButtonBox, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt
import mysql.connector
from datetime import datetime, timedelta


class UpdateDialog(QDialog):
    """Dialog to update the timetable entry's details."""

    def __init__(self, entry_data, parent=None):
        """
        Initialize the dialog with existing entry data.

        :param entry_data: Dictionary containing entry details.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Update Entry")
        self.setModal(True)
        self.updated_entry = None

        # Layout
        layout = QVBoxLayout()

        # Form Layout using QHBoxLayout for each field
        # Teacher Name (Read-Only)
        teacher_layout = QHBoxLayout()
        teacher_label = QLabel("Teacher Name:")
        self.teacher_display = QLineEdit(self)
        self.teacher_display.setText(entry_data.get('teacher_name', ''))
        self.teacher_display.setReadOnly(True)
        teacher_layout.addWidget(teacher_label)
        teacher_layout.addWidget(self.teacher_display)
        layout.addLayout(teacher_layout)

        # Day (Read-Only)
        day_layout = QHBoxLayout()
        day_label = QLabel("Day:")
        self.day_display = QLineEdit(self)
        self.day_display.setText(entry_data.get('day', ''))
        self.day_display.setReadOnly(True)
        day_layout.addWidget(day_label)
        day_layout.addWidget(self.day_display)
        layout.addLayout(day_layout)

        # Period Number (Read-Only)
        period_layout = QHBoxLayout()
        period_label = QLabel("Period Number:")
        self.period_display = QLineEdit(self)
        self.period_display.setText(str(entry_data.get('period_number', '')))
        self.period_display.setReadOnly(True)
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_display)
        layout.addLayout(period_layout)

        # Time Slot (Read-Only)
        time_slot_layout = QHBoxLayout()
        time_slot_label = QLabel("Time Slot:")
        self.time_slot_display = QLineEdit(self)
        self.time_slot_display.setText(entry_data.get('time_slot', ''))
        self.time_slot_display.setReadOnly(True)
        time_slot_layout.addWidget(time_slot_label)
        time_slot_layout.addWidget(self.time_slot_display)
        layout.addLayout(time_slot_layout)

        # Subject (Editable)
        subject_layout = QHBoxLayout()
        subject_label = QLabel("Subject:")
        self.subject_input = QLineEdit(self)
        self.subject_input.setText(entry_data.get('subject', ''))
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        layout.addLayout(subject_layout)

        # Class Name (Editable)
        classname_layout = QHBoxLayout()
        classname_label = QLabel("Class Name:")
        self.classname_input = QLineEdit(self)
        self.classname_input.setText(entry_data.get('class_name', ''))
        classname_layout.addWidget(classname_label)
        classname_layout.addWidget(self.classname_input)
        layout.addLayout(classname_layout)

        # Location (Editable)
        location_layout = QHBoxLayout()
        location_label = QLabel("Location:")
        self.location_input = QLineEdit(self)
        self.location_input.setText(entry_data.get('location', ''))
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_input)
        layout.addLayout(location_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        """Capture the updated values before closing the dialog."""
        subject = self.subject_input.text().strip()
        class_name = self.classname_input.text().strip()
        location = self.location_input.text().strip()

        if not subject:
            QMessageBox.warning(self, "Input Error", "Subject cannot be empty.")
            return

        # Optional: Further validation can be added here

        self.updated_entry = {
            'subject': subject,
            'class_name': class_name,
            'location': location
        }

        super().accept()


class TimetableEditor(QWidget):
    def __init__(self):
        super().__init__()

        # Generate time slots dynamically
        self.time_slots = self.generate_time_slots(start_time="09:00", increment_minutes=45, periods=12)

        # MySQL connection setup with buffered cursor
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",  # Set your MySQL password
                database="ManipalUniversityJaipur"
            )
            self.cursor = self.conn.cursor(buffered=True)  # Buffered cursor
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Connection Error", f"Error connecting to the database: {err}")
            sys.exit(1)

        # Set up the GUI
        self.setWindowTitle('Timetable Editor')
        self.setGeometry(100, 100, 1800, 900)  # Increased width for better layout

        # Main Layout
        main_layout = QVBoxLayout()

        # Dropdown filter for faculty name
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter by Faculty:", self)
        filter_layout.addWidget(filter_label)

        self.filter_dropdown = QComboBox(self)
        self.filter_dropdown.addItem("All Faculties")
        self.filter_dropdown.currentIndexChanged.connect(self.filter_by_faculty)
        self.load_faculty_names()
        filter_layout.addWidget(self.filter_dropdown)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # Buttons for editing (aligned horizontally)
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add New Entry")
        self.add_button.clicked.connect(self.add_new_entry)
        self.add_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("Delete Selected Entry")
        self.delete_button.clicked.connect(self.delete_selected_entry)
        self.delete_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(self.delete_button)

        self.update_button = QPushButton("Update Selected Entry")
        self.update_button.clicked.connect(self.update_selected_entry)
        self.update_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(self.update_button)

        self.null_button = QPushButton("Mark Slot as NULL")
        self.null_button.clicked.connect(self.mark_slot_null)
        self.null_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button_layout.addWidget(self.null_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Table to show and edit records
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)  # MON-FRI columns
        self.table.setRowCount(len(self.time_slots))    # Number of time slots
        self.table.setHorizontalHeaderLabels(["MON", "TUE", "WED", "THU", "FRI"])  # Updated headers
        self.table.setVerticalHeaderLabels([f"{slot}" for slot in self.time_slots])  # Time slots
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Prevent direct editing
        self.table.cellDoubleClicked.connect(self.cell_double_clicked)

        # Enable word wrap and adjust row height
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # Adjust row heights based on content
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 60)  # Adjust as needed

        main_layout.addWidget(self.table)

        # Scroll Area for Input Fields
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Input fields for adding a new entry using QHBoxLayout
        input_group_layout = QVBoxLayout()

        # First Row of Inputs
        row1 = QHBoxLayout()

        teacher_layout = QHBoxLayout()
        teacher_label = QLabel("Teacher Name:")
        self.teacher_input = QLineEdit(self)
        self.teacher_input.setPlaceholderText("Enter teacher's name")
        teacher_layout.addWidget(teacher_label)
        teacher_layout.addWidget(self.teacher_input)
        row1.addLayout(teacher_layout)

        day_layout = QHBoxLayout()
        day_label = QLabel("Day:")
        self.day_input = QComboBox(self)
        self.day_input.addItems(["MON", "TUE", "WED", "THU", "FRI"])
        day_layout.addWidget(day_label)
        day_layout.addWidget(self.day_input)
        row1.addLayout(day_layout)

        period_layout = QHBoxLayout()
        period_label = QLabel("Period Number:")
        self.period_input = QComboBox(self)
        self.period_input.addItems([f"{i + 1}" for i in range(len(self.time_slots))])  # Periods 1 to N
        self.period_input.currentIndexChanged.connect(self.update_time_slot_display)
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_input)
        row1.addLayout(period_layout)

        time_slot_layout = QHBoxLayout()
        time_slot_label = QLabel("Time Slot:")
        self.time_slot_display = QLineEdit(self)
        self.time_slot_display.setReadOnly(True)
        self.time_slot_display.setPlaceholderText("Time Slot")
        time_slot_layout.addWidget(time_slot_label)
        time_slot_layout.addWidget(self.time_slot_display)
        row1.addLayout(time_slot_layout)

        input_group_layout.addLayout(row1)

        # Second Row of Inputs
        row2 = QHBoxLayout()

        subject_layout = QHBoxLayout()
        subject_label = QLabel("Subject:")
        self.subject_input = QLineEdit(self)
        self.subject_input.setPlaceholderText("Enter subject name")
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_input)
        row2.addLayout(subject_layout)

        classname_layout = QHBoxLayout()
        classname_label = QLabel("Class Name:")
        self.classname_input = QLineEdit(self)
        self.classname_input.setPlaceholderText("Enter class name")
        classname_layout.addWidget(classname_label)
        classname_layout.addWidget(self.classname_input)
        row2.addLayout(classname_layout)

        location_layout = QHBoxLayout()
        location_label = QLabel("Classroom:")
        self.location_input = QLineEdit(self)
        self.location_input.setPlaceholderText("Enter classroom")
        location_layout.addWidget(location_label)
        location_layout.addWidget(self.location_input)
        row2.addLayout(location_layout)

        input_group_layout.addLayout(row2)

        scroll_layout.addLayout(input_group_layout)
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Set layout and show data
        self.setLayout(main_layout)
        self.load_data()

    def generate_time_slots(self, start_time="09:00", increment_minutes=45, periods=12):
        """Generate a list of time slots starting from start_time with given increments."""
        time_format = "%H:%M"
        start = datetime.strptime(start_time, time_format)
        slots = []
        for i in range(periods):
            end = start + timedelta(minutes=increment_minutes)
            slot = f"{start.strftime(time_format)}-{end.strftime(time_format)}"
            slots.append(slot)
            start = end
        return slots

    def load_faculty_names(self):
        """Load distinct faculty names into the dropdown."""
        try:
            self.cursor.execute("SELECT DISTINCT teacher_name FROM timetable ORDER BY teacher_name ASC")
            faculty_names = [row[0] for row in self.cursor.fetchall()]
            # Clear existing items except the first one ("All Faculties")
            self.filter_dropdown.blockSignals(True)
            self.filter_dropdown.clear()
            self.filter_dropdown.addItem("All Faculties")
            for name in faculty_names:
                self.filter_dropdown.addItem(name)
            self.filter_dropdown.blockSignals(False)
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error loading faculty names: {err}")

    def filter_by_faculty(self):
        """Filter the timetable based on selected faculty."""
        self.refresh_table()

    def refresh_table(self):
        """Refresh the table based on the current faculty filter."""
        selected_faculty = self.filter_dropdown.currentText()
        if selected_faculty == "All Faculties":
            self.load_data()
        else:
            self.load_data(teacher_name=selected_faculty)

    def load_data(self, teacher_name=None):
        """Load data from MySQL database into the table."""
        self.table.clearContents()
        try:
            if teacher_name:
                query = "SELECT day, period_number, subject, class_name, location FROM timetable WHERE teacher_name = %s"
                params = (teacher_name,)
            else:
                query = "SELECT day, period_number, subject, class_name, location FROM timetable"
                params = ()
            self.cursor.execute(query, params)
            records = self.cursor.fetchall()

            # Clear existing data
            self.table.setRowCount(len(self.time_slots))
            self.table.setColumnCount(5)
            self.table.clearContents()

            for record in records:
                day, period, subject, class_name, location = record
                try:
                    day_idx = ["MON", "TUE", "WED", "THU", "FRI"].index(day)
                except ValueError:
                    # If day is not recognized, skip this record
                    continue
                period_idx = int(period) - 1  # Periods are 1-indexed
                if not (0 <= period_idx < len(self.time_slots)):
                    # Invalid period number, skip
                    continue

                if subject and class_name and location:
                    display_text = f"{subject}\n({class_name})\n{location}"
                elif subject and class_name:
                    display_text = f"{subject}\n({class_name})"
                elif subject:
                    display_text = f"{subject}"
                else:
                    display_text = "NULL"

                item = QTableWidgetItem(display_text)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make item non-editable directly
                self.table.setItem(period_idx, day_idx, item)

            # Adjust row heights based on content
            for row in range(self.table.rowCount()):
                self.table.setRowHeight(row, 60)  # Adjust as needed
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error loading data: {err}")

    def add_new_entry(self):
        """Add a new timetable entry to the database."""
        teacher_name = self.teacher_input.text().strip()
        day = self.day_input.currentText()
        period_number = self.period_input.currentText()
        time_slot = self.time_slot_display.text().strip()
        subject = self.subject_input.text().strip()
        class_name = self.classname_input.text().strip()
        location = self.location_input.text().strip()

        # Input validation
        if not (teacher_name and day and period_number and time_slot and subject and class_name and location):
            self.show_message("Input Error", "All fields must be filled to add a new entry.")
            return

        # Validate period_number is within valid range
        try:
            period_num = int(period_number)
            if not (1 <= period_num <= len(self.time_slots)):
                raise ValueError
        except ValueError:
            self.show_message("Input Error", f"Period Number must be an integer between 1 and {len(self.time_slots)}.")
            return

        try:
            # Check if entry already exists for the day and period
            check_query = "SELECT COUNT(*) FROM timetable WHERE day = %s AND period_number = %s"
            self.cursor.execute(check_query, (day, period_number))
            count = self.cursor.fetchone()[0]
            if count > 0:
                self.show_message("Input Error", f"An entry already exists for {day}, Period {period_number}.")
                return

            query = """
                INSERT INTO timetable (teacher_name, day, period_number, time_slot, subject, class_name, location)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (teacher_name, day, period_number, time_slot, subject, class_name, location))
            self.conn.commit()
            self.refresh_table()  # Refresh the table based on current filter
            self.show_message("Success", "New entry added successfully!")
            self.clear_input_fields()
            self.load_faculty_names()  # Refresh faculty names in case a new one was added
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error adding new entry: {err}")

    def delete_selected_entry(self):
        """Delete the selected timetable entry."""
        selected_row = self.table.currentRow()
        selected_col = self.table.currentColumn()

        if selected_row == -1 or selected_col == -1:
            self.show_message("Selection Error", "Please select a cell to delete.")
            return

        day = ["MON", "TUE", "WED", "THU", "FRI"][selected_col]
        period = selected_row + 1

        # Confirm deletion
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the entry for {day}, Period {period}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            query = "DELETE FROM timetable WHERE day = %s AND period_number = %s"
            self.cursor.execute(query, (day, period))
            self.conn.commit()
            self.refresh_table()  # Refresh the table based on current filter
            self.show_message("Success", "Selected entry deleted successfully!")
            self.load_faculty_names()  # Refresh faculty names in case a faculty has no more entries
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error deleting entry: {err}")

    def update_selected_entry(self):
        """Update the selected timetable entry using a separate dialog."""
        selected_row = self.table.currentRow()
        selected_col = self.table.currentColumn()

        if selected_row == -1 or selected_col == -1:
            self.show_message("Selection Error", "Please select a cell to update.")
            return

        day = ["MON", "TUE", "WED", "THU", "FRI"][selected_col]
        period = selected_row + 1

        teacher_name = self.filter_dropdown.currentText()

        # Fetch current entry data from the database
        try:
            query = "SELECT teacher_name, day, period_number, time_slot, subject, class_name, location FROM timetable WHERE teacher_name = %s AND day = %s AND period_number = %s"
            self.cursor.execute(query, (teacher_name,day, period))
            result = self.cursor.fetchone()

            if not result:
                # Entry might be NULL; allow adding a new entry
                # Check if the cell is marked as NULL
                cell_item = self.table.item(selected_row, selected_col)
                if cell_item and cell_item.text() == "NULL":
                    # Open a dialog to add a new entry to this slot
                    entry_data = {
                        'teacher_name': teacher_name,  # Since the entry is NULL, all fields should be empty
                        'day': day,
                        'period_number': period,
                        'time_slot': self.time_slots[selected_row],
                        'subject': '',
                        'class_name': '',
                        'location': ''
                    }
                else:
                    self.show_message("Not Found", "No entry found for the selected cell.")
                    update_query = "INSERT INTO timetable (teacher_name, day, period_number, time_slot ) VALUES (%s, %s,%s,%s);"
                    self.cursor.execute(update_query, (teacher_name, day, period, self.time_slots[selected_row], ))
                    self.conn.commit()
                    self.refresh_table()  # Refresh the table based on current filter
                    self.show_message("Success", "Selected entry updated successfully!")


                    entry_data = {
                        'teacher_name': teacher_name,  # Since the entry is NULL, all fields should be empty
                        'day': day,
                        'period_number': period,
                        'time_slot': self.time_slots[selected_row],
                        'subject': '',
                        'class_name': '',
                        'location': ''
                    }




            else:
                # Populate entry data for the existing record
                teacher_name, day, period_number, time_slot, subject, class_name, location = result
                entry_data = {
                    'teacher_name': teacher_name,
                    'day': day,
                    'period_number': period_number,
                    'time_slot': time_slot,
                    'subject': subject,
                    'class_name': class_name,
                    'location': location
                }

        except mysql.connector.Error as err:
            self.show_message("Error", f"Error fetching entry: {err}")
            return

        # Open the Update Dialog with entry data
        dialog = UpdateDialog(entry_data, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_entry = dialog.updated_entry
            new_subject = updated_entry['subject']
            new_class = updated_entry['class_name']
            new_location = updated_entry['location']

            try:
                if any([new_subject, new_class, new_location]):
                    # Update existing entry or add a new one
                    update_query = """
                        UPDATE timetable SET subject = %s, class_name = %s, location = %s 
                        WHERE day = %s AND period_number = %s
                    """
                    self.cursor.execute(update_query, (
                        new_subject,
                        new_class,
                        new_location,
                        day,
                        period
                    ))
                else:
                    # If all fields are empty, mark the slot as NULL
                    update_query = "UPDATE timetable SET subject = NULL, class_name = NULL, location = NULL WHERE day = %s AND period_number = %s"
                    self.cursor.execute(update_query, (day, period))

                self.conn.commit()
                self.refresh_table()  # Refresh the table based on current filter
                self.show_message("Success", "Selected entry updated successfully!")
                self.load_faculty_names()  # Refresh faculty names in case a new one was added
            except mysql.connector.Error as err:
                self.show_message("Error", f"Error updating entry: {err}")

    def is_entry_null(self, entry_data):
        """Check if the entry data is marked as NULL."""
        return not any([entry_data.get('subject'), entry_data.get('class_name'), entry_data.get('location')])

    def mark_slot_null(self):
        """Mark the selected slot as NULL."""
        selected_row = self.table.currentRow()
        selected_col = self.table.currentColumn()

        if selected_row == -1 or selected_col == -1:
            self.show_message("Selection Error", "Please select a cell to mark as NULL.")
            return

        day = ["MON", "TUE", "WED", "THU", "FRI"][selected_col]
        period = selected_row + 1

        # Confirm action
        confirm = QMessageBox.question(
            self, "Confirm Action",
            f"Are you sure you want to mark the slot for {day}, Period {period} as NULL?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            query = "UPDATE timetable SET subject = NULL, class_name = NULL, location = NULL WHERE day = %s AND period_number = %s"
            self.cursor.execute(query, (day, period))
            self.conn.commit()
            self.refresh_table()  # Refresh the table based on current filter
            self.show_message("Success", "Selected slot marked as NULL!")
            self.load_faculty_names()  # Refresh faculty names in case a faculty has no more entries
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error marking slot as NULL: {err}")

    def cell_double_clicked(self, row, column):
        """Open update dialog on double-click."""
        self.table.selectRow(row)
        self.table.selectColumn(column)
        self.update_selected_entry()

    def clear_input_fields(self):
        """Clear all input fields after adding a new entry."""
        self.teacher_input.clear()
        self.day_input.setCurrentIndex(0)
        self.period_input.setCurrentIndex(0)
        self.subject_input.clear()
        self.classname_input.clear()
        self.location_input.clear()

    def update_time_slot_display(self, index):
        """Auto-fill time slot based on period number."""
        if 0 <= index < len(self.time_slots):
            self.time_slot_display.setText(self.time_slots[index])
        else:
            self.time_slot_display.clear()

    def show_message(self, title, message):
        """Display a message box."""
        msg = QMessageBox()
        if title.lower() in ["error", "selection error", "input error", "database connection error"]:
            msg.setIcon(QMessageBox.Critical)
        elif title.lower() == "success":
            msg.setIcon(QMessageBox.Information)
        else:
            msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def closeEvent(self, event):
        """Ensure the MySQL connection is closed when the app is closed."""
        try:
            self.cursor.close()
            self.conn.close()
        except mysql.connector.Error as err:
            self.show_message("Error", f"Error closing database connection: {err}")
        except AttributeError:
            # If cursor or conn wasn't created due to a connection error
            pass
        event.accept()


# Main program
if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = TimetableEditor()
    editor.show()
    sys.exit(app.exec_())