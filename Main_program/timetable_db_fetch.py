import mysql.connector
from datetime import datetime, time, timedelta
from fuzzywuzzy import process  # Consider using rapidfuzz for better performance
import sys
import re
import logging
from langchain.tools import tool  # Import the tool decorator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
TIME_SLOT_PATTERN = re.compile(r'^(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})')


# Function to map input name to matched name
def get_matched_teacher_name(input_name):
    teacher_names = get_teacher_names()
    if not teacher_names:
        logging.error("No teacher names available for matching.")
        return None, 0
    matched_name, confidence = fuzzy_match_name(input_name, teacher_names)
    return matched_name, confidence


# Utility function to check if a given time is within a time slot
def is_time_in_range(time_range: str, check_time: str) -> bool:
    try:
        # Split only on the hyphen to get start and end times
        start_time_str, end_time_str = re.split(r'\s*-\s*', time_range)

        # Convert times to minutes since midnight for comparison
        start_time = int(start_time_str.split(':')[0]) * 60 + int(start_time_str.split(':')[1])
        end_time = int(end_time_str.split(':')[0]) * 60 + int(end_time_str.split(':')[1])
        check_time_mins = int(check_time.split(':')[0]) * 60 + int(check_time.split(':')[1])

        return start_time <= check_time_mins <= end_time
    except ValueError as e:
        logging.error(f"Error parsing time range '{time_range}' or check_time '{check_time}': {e}")
        return False


# ===================== Decorated Tool Functions =====================
current_time: str = None
@tool
def check_if_free_now(input_name: str) -> str:
    """
    Checks if the specified teacher is free at the current time.
    """
    matched_name, confidence = get_matched_teacher_name(input_name)
    if not matched_name:
        return f"No matching teacher found for '{input_name}'."

    if current_time is None:
        current_time_obj = datetime.now().time()
        current_time_str = current_time_obj.strftime("%H:%M")
    else:
        current_time_obj = parse_time(current_time)
        if current_time_obj is None:
            return "Invalid time format. Please use HH:MM."
        current_time_str = current_time

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
        cursor.execute(query, (matched_name, day_of_week))
        records = cursor.fetchall()
        logging.info(f"Fetched {len(records)} records for {matched_name} on {day_of_week_full}.")
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
            logging.info(f"Checking if {current_time_obj} is between {start_time} and {end_time} for {matched_name}.")

            if start_time <= current_time_obj <= end_time:
                # Person is busy right now
                return (f"{matched_name} is currently busy teaching {subject} in {class_name} at {location}. "
                        f"They will be free after {end_time.strftime('%H:%M')}.")
        else:
            logging.warning(f"Time slot '{time_slot}' does not match the expected format.")
            continue  # Skip entries that don't match the pattern

    # If no match, they are free
    return f"{matched_name} is free now."


@tool
def get_weekly_timetable(input_name: str) -> str:
    """
    Retrieves the weekly timetable for the specified teacher.
    Can be used to deduce the timetable for an particular day of the week
    """
    matched_name, confidence = get_matched_teacher_name(input_name)
    if not matched_name:
        return f"No matching teacher found for '{input_name}'."

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
        cursor.execute(query, (matched_name,))
        records = cursor.fetchall()
        logging.info(f"Fetched weekly timetable for {matched_name}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching weekly timetable: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    if records:
        timetable = f"Weekly Timetable for {matched_name}:\n"
        current_day = None
        for record in records:
            day = record['day']
            time_slot = record['time_slot']
            subject = record['subject'] if record['subject'] else "N/A"
            class_name = record['class_name'] if record['class_name'] else "N/A"
            location = record['location'] if record['location'] else "N/A"

            # Start a new day section if the day has changed
            if day != current_day:
                current_day = day
                timetable += f"\n{current_day}:\n"

            timetable += f"  {time_slot} - {subject} in {class_name} at {location}\n"
        return timetable
    else:
        return f"No timetable found for {matched_name}."


@tool
def get_daily_timetable(input_name: str) -> str:
    """
    Retrieves today's timetable for the specified teacher.
    """
    matched_name, confidence = get_matched_teacher_name(input_name)
    if not matched_name:
        return f"No matching teacher found for '{input_name}'."

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
    matched_day, confidence_day = fuzzy_match_name(day_of_week_full, available_days)
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
        cursor.execute(query, (matched_name, matched_day))
        records = cursor.fetchall()
        logging.info(f"Fetched daily timetable for {matched_name} on {matched_day}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching daily timetable: {err}")
        records = []
    finally:
        cursor.close()
        conn.close()

    if records:
        timetable = (f"Timetable for {matched_name} on {matched_day} "
                     f"(Confidence: {confidence_day}%)\n")
        for record in records:
            time_slot, subject, class_name, location = record
            subject = subject if subject else "N/A"
            class_name = class_name if class_name else "N/A"
            location = location if location else "N/A"
            timetable += f"  {time_slot} - {subject} in {class_name} at {location}\n"
        return timetable
    else:
        return f"No classes for {matched_name} today."


@tool
def get_free_teachers(current_time: str = None) -> str:
    """
    Retrieves a list of teachers who are free at the current time.
    """

    current_time_str = datetime.now().strftime("%H:%M")


    day_of_week_full = datetime.now().strftime("%A")
    day_of_week = get_day_abbreviation(day_of_week_full)  # e.g., 'FRI'

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
            if is_time_in_range(time_slot, current_time_str):
                busy_teachers.add(teacher_name)

        logging.info(f"Fetched busy teachers at {current_time_str} on {day_of_week_full}.")

        free_teachers = all_teachers - busy_teachers
    except mysql.connector.Error as err:
        logging.error(f"Error fetching free teachers: {err}")
        free_teachers = set()
    finally:
        cursor.close()
        conn.close()

    if free_teachers:
        return f"Teachers free right now ({current_time_str} on {day_of_week_full}): {', '.join(sorted(free_teachers))}"
    else:
        return "No teachers are free right now."


@tool
def get_busy_teachers(current_time: str = None) -> str:
    """
    Retrieves a list of teachers who are busy at the current time.
    """

    current_time_str = datetime.now().strftime("%H:%M")


    day_of_week_full = datetime.now().strftime("%A")
    day_of_week = get_day_abbreviation(day_of_week_full)  # e.g., 'FRI'

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT teacher_name, time_slot FROM timetable WHERE day = %s", (day_of_week,))
        busy_teachers = []
        for row in cursor.fetchall():
            teacher_name, time_slot = row
            if is_time_in_range(time_slot, current_time_str):
                busy_teachers.append(teacher_name)

        logging.info(f"Fetched busy teachers at {current_time_str} on {day_of_week_full}.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching busy teachers: {err}")
        busy_teachers = []
    finally:
        cursor.close()
        conn.close()

    if busy_teachers:
        return f"Teachers busy right now ({current_time_str} on {day_of_week_full}): {', '.join(sorted(busy_teachers))}"
    else:
        return "No teachers are busy right now."


@tool
def get_next_free_slot(input_name: str ) -> str:
    """
    Finds the next free slot for the specified teacher after the current time.
    """
    matched_name, confidence = get_matched_teacher_name(input_name)
    if not matched_name:
        return f"No matching teacher found for '{input_name}'."

    if current_time is None:
        current_datetime = datetime.now()
    else:
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            current_datetime = datetime.strptime(f"{today_str} {current_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return "Invalid time format. Please use HH:MM."

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
        cursor.execute(query, (matched_name, day_of_week))
        records = cursor.fetchall()
        logging.info(f"Fetched {len(records)} time slots for {matched_name} on {day_of_week_full}.")
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
        try:
            start_str, end_str = re.split(r'\s*-\s*', time_slot)
            start_time = datetime.strptime(f"{current_datetime.strftime('%Y-%m-%d')} {start_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{current_datetime.strftime('%Y-%m-%d')} {end_str}", "%Y-%m-%d %H:%M")
            time_slots.append((start_time, end_time))
        except ValueError:
            logging.warning(f"Invalid time slot format: {time_slot}")
            continue

    # Sort the time slots by start_time
    time_slots.sort(key=lambda x: x[0])

    for i, (start, end) in enumerate(time_slots):
        if current_datetime < start:
            # There's a free slot between now and the next class
            return (
                f"{matched_name} is free from {current_datetime.strftime('%H:%M')} to {start.strftime('%H:%M')} on {day_of_week_full}."
            )
        elif start <= current_datetime <= end:
            # Currently busy, check if there's another class later in the day
            if i + 1 < len(time_slots):
                next_start, next_end = time_slots[i + 1]
                return (
                    f"{matched_name} is currently busy and will be free after {end.strftime('%H:%M')} on {day_of_week_full}, until their next class at {next_start.strftime('%H:%M')}."
                )
            else:
                # No more classes after this one
                return (
                    f"{matched_name} is currently busy and will be free after {end.strftime('%H:%M')} on {day_of_week_full} for the rest of the day."
                )

    # If current time is after all classes
    return f"{matched_name} is free for the rest of the day ({day_of_week_full})."

@tool
def get_faculty_availability(faculty_name: str) -> str:
    """
    Returns a comprehensive availability status of a faculty member.
    It checks if the faculty is free now, retrieves their weekly and daily timetables,
    and provides information about their next free slot.
    """
    status = []

    # Check if the faculty is free now
    free_now = check_if_free_now.invoke({"input_name": faculty_name, "current_time": current_time})
    status.append(free_now)

    # Get weekly timetable
    weekly_tt = get_weekly_timetable.invoke({"input_name": faculty_name})
    status.append(weekly_tt)

    # Get today's timetable
    daily_tt = get_daily_timetable.invoke({"input_name": faculty_name})
    status.append(daily_tt)

    # Get next free slot
    if current_time:
        next_free = get_next_free_slot.invoke({"input_name": faculty_name, "current_time": current_time})
    else:
        next_free = get_next_free_slot.invoke({"input_name": faculty_name})
    status.append(next_free)

    # Compile all information
    availability_info = "\n\n".join(status)
    return availability_info


# ===================== End of Decorated Tool Functions =====================


# ===================== Main Execution Block =====================
if __name__ == "__main__":
    # Example input name
    input_name = 'abhay'

    # Fetch and display available teachers
    teacher_names = get_teacher_names()
    if not teacher_names:
        print("No teachers found in the database.")
        sys.exit(1)

    print(f"Available Teachers ({len(teacher_names)}):")
    print(", ".join(teacher_names))
    print("\n")

    # Get matched teacher name
    matched_name, confidence = fuzzy_match_name(input_name, teacher_names)
    if matched_name:
        print(f"\nBest match for '{input_name}': {matched_name} (Confidence: {confidence}%)\n")
    else:
        print(f"\nNo matching teacher found for '{input_name}'.\n")
        sys.exit(1)

    # Refactor tool calls with .invoke() and dictionary format
    # Check if a teacher is free now
    print(check_if_free_now.invoke({"input_name": input_name, "current_time": '13:31'}))
    print("\n")

    # Get weekly timetable for a teacher
    print(get_weekly_timetable.invoke({"input_name": input_name}))
    print("\n")

    # Get today's timetable for a teacher
    print(get_daily_timetable.invoke({"input_name": input_name}))
    print("\n")

    # Get teachers who are free right now
    print(get_free_teachers.invoke({"current_time": '13:31'}))
    print("\n")

    # Get teachers who are busy right now
    print(get_busy_teachers.invoke({"current_time": '13:31'}))
    print("\n")

    # Get next free slot for a teacher
    print(get_next_free_slot.invoke({"input_name": input_name, "current_time": '13:31'}))
    print("\n")

    # Get faculty availability using the new tool
    print(get_faculty_availability.invoke({"faculty_name": input_name, "current_time": '13:31'}))
    print("\n")

    # Example usage with both day of the week and time for testing
    print(get_next_free_slot.invoke(
        {"input_name": "Abhay Sharma, Dr.", "current_time": "09:00", "day_of_week_full": "Monday"}))
    print(get_next_free_slot.invoke(
        {"input_name": "Abhay Sharma, Dr.", "current_time": "14:00", "day_of_week_full": "Wednesday"}))
