import mysql.connector
from datetime import datetime, time, timedelta
from fuzzywuzzy import process  # Consider using rapidfuzz for better performance
import sys
import re
import logging



# Helper function to map full day names to abbreviations
def get_day_abbreviation(full_day_name):
    """
    Converts full day name to three-letter uppercase abbreviation.
    Example: 'Friday' -> 'FRI'
    """
    return full_day_name[:3].upper()


# MySQL connection setup
def get_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Set your MySQL password
            database="ManipalUniversityJaipur"
        )
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        sys.exit(1)


# Function to get the current time (for debugging)
def get_current_time():
    return datetime.now().strftime("%H:%M")


# Helper function to get distinct teacher names from the database
def get_teacher_names():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT teacher_name FROM timetable")
        names = [row[0] for row in cursor.fetchall()]
        logging.info("Successfully fetched teacher names.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching teacher names: {err}")
        names = []
    finally:
        cursor.close()
        conn.close()
    return names


# Helper function to match the correct name using fuzzy matching
def fuzzy_match_name(input_name, name_list):
    matched = process.extractOne(input_name, name_list)
    if matched:
        matched_name, confidence = matched
        logging.info(f"Fuzzy matched '{input_name}' to '{matched_name}' with confidence {confidence}%.")
        return matched_name, confidence
    else:
        logging.warning(f"No fuzzy match found for '{input_name}'.")
        return None, 0


# Function to parse time strings into time objects
def parse_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%H:%M").time()
    except ValueError:
        logging.warning(f"Failed to parse time string: '{time_str}'")
        return None


# Regular expression pattern to extract start and end times
TIME_SLOT_PATTERN = re.compile(r'^(\d{1,2}:\d{2})\s*[-:]\s*(\d{1,2}:\d{2})')


# Function to check if a person is free now, and when they will be free if they are busy
def check_if_free_now(teacher_name, current_time=None):
    if current_time is None:
        current_time = datetime.now().time()
    else:
        current_time = parse_time(current_time)
        if current_time is None:
            return "Invalid time format. Please use HH:MM."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get today's full day name and convert to abbreviation
        day_of_week_full = datetime.now().strftime("%A")  # e.g., 'Friday'
        day_of_week = get_day_abbreviation(day_of_week_full)  # 'FRI'

        query = """
            SELECT time_slot, subject, class_name, location
            FROM timetable
            WHERE teacher_name = %s AND day = %s
        """
        cursor.execute(query, (teacher_name, day_of_week))
        records = cursor.fetchall()
        logging.info(f"Fetched {len(records)} records for {teacher_name} on {day_of_week_full}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching timetable: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    # Check each time slot for a match
    for record in records:
        time_slot, subject, class_name, location = record
        match = TIME_SLOT_PATTERN.match(time_slot)
        if match:
            start_str, end_str = match.groups()
            start_time = parse_time(start_str)
            end_time = parse_time(end_str)
            if not start_time or not end_time:
                logging.warning(f"Invalid time format in time_slot: {time_slot}")
                continue  # Skip invalid time formats

            # Debug: Log time comparison
            logging.info(f"Checking if {current_time} is between {start_time} and {end_time} for {teacher_name}.")

            if start_time <= current_time <= end_time:
                # Person is busy right now
                return (f"{teacher_name} is currently busy teaching {subject} in {class_name} at {location}. "
                        f"They will be free after {end_time.strftime('%H:%M')}.")
        else:
            logging.warning(f"Time slot '{time_slot}' does not match the expected format.")
            continue  # Skip entries that don't match the pattern

    # If no match, they are free
    return f"{teacher_name} is free now."


# Function to get the timetable of a person for the entire week
def get_weekly_timetable(teacher_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary cursor for easier access
    try:
        # Define the order of days
        days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        # Fetch timetable for the entire week
        query = """
            SELECT day, time_slot, subject, class_name, location
            FROM timetable
            WHERE teacher_name = %s
            ORDER BY FIELD(day, 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'), 
                     STR_TO_DATE(SUBSTRING_INDEX(time_slot, '-', 1), '%H:%i')
        """
        cursor.execute(query, (teacher_name,))
        records = cursor.fetchall()
        logging.info(f"Fetched weekly timetable for {teacher_name}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching weekly timetable: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    if records:
        timetable = f"Weekly Timetable for {teacher_name}:\n"
        current_day = None
        for record in records:
            day = record['day']
            time_slot = record['time_slot']
            subject = record['subject']
            class_name = record['class_name']
            location = record['location']

            # Start a new day section if the day has changed
            if day != current_day:
                current_day = day
                timetable += f"\n{current_day}:\n"

            timetable += f"  {time_slot} - {subject} in {class_name} at {location}\n"
        return timetable
    else:
        return f"No timetable found for {teacher_name}."


# Function to get the daily timetable of a person, using fuzzy matching for day names
def get_daily_timetable(teacher_name):
    day_of_week_full = datetime.now().strftime("%A")  # e.g., 'Friday'

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch distinct day values from the database for fuzzy matching
        cursor.execute("SELECT DISTINCT day FROM timetable")
        available_days = [row[0] for row in cursor.fetchall()]
        logging.info("Fetched available days for fuzzy matching.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching available days: {err}")
        available_days = []
    finally:
        cursor.close()
        conn.close()

    # Use fuzzy matching to find the closest match for today's day
    matched_day, confidence = fuzzy_match_name(day_of_week_full, available_days)
    if not matched_day:
        return "Could not match the current day with available days in the timetable."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch timetable for the matched day
        query = """
            SELECT time_slot, subject, class_name, location
            FROM timetable
            WHERE teacher_name = %s AND day = %s
            ORDER BY STR_TO_DATE(SUBSTRING_INDEX(time_slot, '-', 1), '%H:%i')
        """
        cursor.execute(query, (teacher_name, matched_day))
        records = cursor.fetchall()
        logging.info(f"Fetched daily timetable for {teacher_name} on {matched_day}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching daily timetable: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    if records:
        timetable = (f"Timetable for {teacher_name} on {matched_day} "
                     f"(Confidence: {confidence}%)\n")
        for record in records:
            time_slot, subject, class_name, location = record
            timetable += f"  {time_slot} - {subject} in {class_name} at {location}\n"
        return timetable
    else:
        return f"No classes for {teacher_name} today."

from datetime import datetime
import logging

# Utility function to check if a given time is within a time slot
def is_time_in_range(time_range: str, check_time: str) -> bool:
    start_time_str, end_time_str = time_range.split('-')
    start_time = int(start_time_str.split(':')[0]) * 60 + int(start_time_str.split(':')[1])
    end_time = int(end_time_str.split(':')[0]) * 60 + int(end_time_str.split(':')[1])
    check_time_mins = int(check_time.split(':')[0]) * 60 + int(check_time.split(':')[1])
    return start_time <= check_time_mins <= end_time

# Function to find which teachers are free right now
def get_free_teachers(current_time=None):
    if current_time is None:
        current_time = datetime.now().strftime("%H:%M")
    day_of_week_full = datetime.now().strftime("%A")
    day_of_week = get_day_abbreviation(day_of_week_full)  # 'FRI'

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Fetch all teachers
        cursor.execute("SELECT DISTINCT teacher_name FROM timetable")
        all_teachers = set(row[0] for row in cursor.fetchall())
        logging.info("Fetched all teachers.")

        # Fetch busy teachers at current_time using Python time comparison
        cursor.execute("SELECT teacher_name, time_slot FROM timetable WHERE day = %s", (day_of_week,))
        busy_teachers = set()
        for row in cursor.fetchall():
            teacher_name, time_slot = row
            if is_time_in_range(time_slot, current_time):
                busy_teachers.add(teacher_name)

        logging.info(f"Fetched busy teachers at {current_time} on {day_of_week_full}.")

        free_teachers = all_teachers - busy_teachers
    except mysql.connector.Error as err:
        logging.error(f"Error fetching free teachers: {err}")
        free_teachers = set()
    finally:
        cursor.close()
        conn.close()

    if free_teachers:
        return f"Teachers free right now ({current_time} on {day_of_week_full}): {', '.join(sorted(free_teachers))}"
    else:
        return "No teachers are free right now."


# Function to find which teachers are busy right now
def get_busy_teachers(current_time=None):
    if current_time is None:
        current_time = datetime.now().strftime("%H:%M")
    day_of_week_full = datetime.now().strftime("%A")
    day_of_week = get_day_abbreviation(day_of_week_full)  # 'FRI'

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT teacher_name, time_slot FROM timetable WHERE day = %s", (day_of_week,))
        busy_teachers = []
        for row in cursor.fetchall():
            teacher_name, time_slot = row
            if is_time_in_range(time_slot, current_time):
                busy_teachers.append(teacher_name)

        logging.info(f"Fetched busy teachers at {current_time} on {day_of_week_full}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching busy teachers: {err}")
        busy_teachers = []
    finally:
        cursor.close()
        conn.close()

    if busy_teachers:
        return f"Teachers busy right now ({current_time} on {day_of_week_full}): {', '.join(sorted(busy_teachers))}"
    else:
        return "No teachers are busy right now."


def get_next_free_slot(teacher_name, current_time=None, day_of_week_full=None):
    if current_time is None:
        current_datetime = datetime.now()
    else:
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            current_datetime = datetime.strptime(f"{today_str} {current_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid time format. Please use HH:MM."

    if day_of_week_full is None:
        day_of_week_full = current_datetime.strftime("%A")
    day_of_week = get_day_abbreviation(day_of_week_full)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT time_slot
            FROM timetable
            WHERE teacher_name = %s AND day = %s
        """
        cursor.execute(query, (teacher_name, day_of_week))
        records = cursor.fetchall()
        logging.info(f"Fetched {len(records)} time slots for {teacher_name} on {day_of_week_full}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching timetable for next free slot: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    # Parse and sort the time slots
    time_slots = []
    for record in records:
        time_slot = record[0]
        start_str, end_str = time_slot.split('-')
        start_time = datetime.strptime(f"{current_datetime.strftime('%Y-%m-%d')} {start_str}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{current_datetime.strftime('%Y-%m-%d')} {end_str}", "%Y-%m-%d %H:%M")
        time_slots.append((start_time, end_time))

    # Sort the time slots by start_time
    time_slots.sort(key=lambda x: x[0])

    for i, (start, end) in enumerate(time_slots):
        if current_datetime < start:
            # There's a free slot between now and the next class
            return (
                f"{teacher_name} is free from {current_datetime.strftime('%H:%M')} to {start.strftime('%H:%M')} on {day_of_week_full}."
            )
        elif start <= current_datetime <= end:
            # Currently busy, check if there's another class later in the day
            if i + 1 < len(time_slots):
                next_start, next_end = time_slots[i + 1]
                return (
                    f"{teacher_name} is currently busy and will be free after {end.strftime('%H:%M')} on {day_of_week_full}, until their next class at {next_start.strftime('%H:%M')}."
                )
            else:
                # No more classes after this one
                return (
                    f"{teacher_name} is currently busy and will be free after {end.strftime('%H:%M')} on {day_of_week_full} for the rest of the day."
                )

    # If current time is after all classes
    return f"{teacher_name} is free for the rest of the day ({day_of_week_full})."

# ===================== End of New Function =====================

# Example usage
if __name__ == "__main__":
    # Fetch all teacher names
    teacher_names = get_teacher_names()
    if not teacher_names:
        print("No teachers found in the database.")
        sys.exit(1)

    print(f"Available Teachers ({len(teacher_names)}):")
    print(", ".join(teacher_names))
    print("\n")

    # Example fuzzy matching usage
    # input_name = input("Enter teacher name: ").strip()
    # if not input_name:
    #    print("No input provided.")
    #    sys.exit(1)
    input_name = 'abhay'

    matched_name, confidence = fuzzy_match_name(input_name, teacher_names)
    if matched_name:
        print(f"\nBest match for '{input_name}': {matched_name} (Confidence: {confidence}%)\n")
    else:
        print(f"\nNo matching teacher found for '{input_name}'.\n")
        sys.exit(1)

    # Check if a teacher is free now
    # You can pass a specific time as a string in "HH:MM" format or leave it as None to use current time
    print(check_if_free_now(matched_name, '13:31'))
    print("\n")

    # Get weekly timetable for a teacher
    print(get_weekly_timetable(matched_name))
    print("\n")

    # Get today's timetable for a teacher
    print(get_daily_timetable(matched_name))
    print("\n")

    # Get teachers who are free right now
    print(get_free_teachers('13:31'))
    print("\n")

    # Get teachers who are busy right now
    print(get_busy_teachers('13:31'))
    print("\n")

    print(get_next_free_slot(matched_name, '13:31'))
    print("\n")

    # Example usage with both day of the week and time for testing
    print(get_next_free_slot("Abhay Sharma, Dr.", "09:00", "Monday"))
    print(get_next_free_slot("Abhay Sharma, Dr.", "14:00", "Wednesday"))
