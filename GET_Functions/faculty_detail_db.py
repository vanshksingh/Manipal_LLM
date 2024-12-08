import mysql.connector
from fuzzywuzzy import fuzz, process

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



# Retrieve data by research area using fuzzy matching
def get_faculty_by_research_area(search_research_area):
    connection = connect_db()
    query = "SELECT name, research_area, google_scholar_link FROM FacultyInfo"
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()

    # Use fuzzy matching to find close matches to the search query
    matches = []
    for result in results:
        if fuzz.partial_ratio(search_research_area.lower(), result[1].lower()) > 80:
            matches.append(result)

    return str(matches)


# Retrieve faculty data based on fuzzy matching for names
def get_faculty_by_name(search_name):
    connection = connect_db()
    query = "SELECT name, email, ext_number, block_location, floor_location, room_number, google_scholar_link FROM FacultyInfo"
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()

    # Use fuzzy matching to find close matches to the search query
    matches = process.extract(search_name, [result[0] for result in results], limit=1, scorer=fuzz.token_sort_ratio)
    return str([result for result in results if result[0] in [match[0] for match in matches]])


# Retrieve faculty parameters by fuzzy matching the name
def get_faculty_parameters_by_name(search_name):
    connection = connect_db()
    query = """SELECT name, email, ext_number, phone_number, block_location, 
                      floor_location, room_number, workstation, research_area, google_scholar_link 
               FROM FacultyInfo"""
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()

    # Extract names for fuzzy matching
    names = [result[0] for result in results]
    matches = process.extract(search_name, names, limit=1, scorer=fuzz.token_sort_ratio)

    # Retrieve full details for the best matches
    faculty_details = []
    for match in matches:
        if match[1] >= 85:  # Only consider matches with a score above 80
            for result in results:
                if result[0] == match[0]:  # Find corresponding record
                    faculty_details.append({
                        'name': result[0],
                        'email': result[1],
                        'ext_number': result[2],
                        'phone_number': result[3],
                        'block_location': result[4],
                        'floor_location': result[5],
                        'room_number': result[6],
                        'workstation': result[7],
                        'research_area': result[8],
                        'google_scholar_link': result[9]
                    })
    return str(faculty_details)


# Retrieve faculty by block location
def get_faculty_by_block(block_location):
    connection = connect_db()
    query = """SELECT name, email, ext_number, floor_location, room_number, google_scholar_link 
               FROM FacultyInfo WHERE block_location = %s"""
    cursor = connection.cursor()
    cursor.execute(query, (block_location,))
    results = cursor.fetchall()

    return results


# Retrieve faculty count by floor location
def get_faculty_count_by_floor(floor_location):
    connection = connect_db()
    query = "SELECT COUNT(*) FROM FacultyInfo WHERE floor_location = %s"
    cursor = connection.cursor()
    cursor.execute(query, (floor_location,))
    count = cursor.fetchone()[0]

    return count


# Retrieve all faculty names for fuzzy matching
def get_all_faculty_names():
    connection = connect_db()
    query = "SELECT name FROM FacultyInfo"
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()

    # Return a list of names
    return [result[0] for result in results]







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

def get_best_match_details(input_name):
    best_match = find_best_match(input_name)
    if best_match:
        faculty_details = get_faculty_details_by_name(best_match)
        if faculty_details:
            return str(faculty_details)
        else:
            return str("No details found for the best match.")
    else:
        return str("No suitable match found.")




# Main execution
if __name__ == "__main__":


    # Example queries
    print("Searching for faculty in the research area 'IoT':")
    print(get_faculty_by_research_area("IoT"))

    print("\nSearching for faculty by name :")
    print(get_faculty_by_name("Dr. Sandeep Singh"))

    print("\nSearching for faculty parameter by name :")

    search_name = "Dr. Sandeep Singh"
    print(get_faculty_parameters_by_name(search_name))

    print("\nSearching for faculty globally :")

    input_name = "somya goyel"  # Replace this with the name you're searching for
    print(get_best_match_details(input_name))


