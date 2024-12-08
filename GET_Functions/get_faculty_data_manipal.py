import mysql.connector
from fuzzywuzzy import process

# Database connection function
def connect_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="ManipalUniversityJaipur"
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None


# Function to retrieve all faculty names from the database
def get_all_faculty_names():
    try:
        conn = connect_db()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Faculty")
        result = cursor.fetchall()

        faculty_names = [row[0] for row in result]

        cursor.close()
        conn.close()

        return faculty_names
    except mysql.connector.Error as err:
        print(f"Error retrieving names: {err}")
        return None


# Function to query the database and return faculty details by name
def get_faculty_details_by_name(name):
    try:
        conn = connect_db()
        if conn is None:
            return None

        cursor = conn.cursor()
        sql = """
        SELECT name, position, email, phone, department, img_url, qualifications, expertise, achievements
        FROM Faculty WHERE name = %s
        """
        cursor.execute(sql, (name,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                'name': result[0],
                'position': result[1],
                'email': result[2],
                'phone': result[3],
                'department': result[4],
                'img_url': result[5],
                'qualifications': result[6],
                'expertise': result[7],
                'achievements': result[8]
            }
        else:
            return None
    except mysql.connector.Error as err:
        print(f"Error retrieving details: {err}")
        return None


# Function to find the best matching faculty using fuzzy matching
def find_best_match(input_name):
    faculty_names = get_all_faculty_names()
    if faculty_names is None:
        return None

    # Use fuzzy matching to find the closest match
    best_match, score = process.extractOne(input_name, faculty_names)
    print(f"Best match: {best_match} (Score: {score})")

    if score > 70:  # Only accept matches with a confidence score greater than 70
        return best_match
    else:
        return None


# Function to retrieve and print the details of the best-matched faculty
def get_best_match_details(input_name):
    best_match = find_best_match(input_name)
    if best_match:
        faculty_details = get_faculty_details_by_name(best_match)
        if faculty_details:
            # Print details and handle None values by showing "No data found"
            print(f"Name: {faculty_details['name']}")
            print(f"Position: {faculty_details['position'] if faculty_details['position'] else 'No data found'}")
            print(f"Email: {faculty_details['email'] if faculty_details['email'] else 'No data found'}")
            print(f"Phone: {faculty_details['phone'] if faculty_details['phone'] else 'No data found'}")
            print(f"Department: {faculty_details['department'] if faculty_details['department'] else 'No data found'}")
            print(f"Image URL: {faculty_details['img_url'] if faculty_details['img_url'] else 'No data found'}")
            print(f"Qualifications: {faculty_details['qualifications'] if faculty_details['qualifications'] else 'No data found'}")
            print(f"Expertise: {faculty_details['expertise'] if faculty_details['expertise'] else 'No data found'}")
            print(f"Achievements: {faculty_details['achievements'] if faculty_details['achievements'] else 'No data found'}")
        else:
            print("No details found for the best match.")
    else:
        print("No suitable match found.")



if __name__ == "__main__":
    # Example usage
    input_name = "somya goyel"  # Replace this with the name you're searching for
    get_best_match_details(input_name)
