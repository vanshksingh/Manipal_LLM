import mysql.connector
from fuzzywuzzy import fuzz, process
from langchain.tools import tool
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def connect_db():
    """
    Establishes a connection to the MySQL database.
    Returns the connection object if successful, else None.
    """
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="ManipalUniversityJaipur"  # Ensure this database contains both FacultyInfo and Faculty tables
        )
        logging.info("Database connection established.")
        return conn
    except mysql.connector.Error as err:
        logging.error("Error connecting to the database: %s", err)
        return None


def normalize_name(name):
    """
    Removes titles like Dr., Mr., Ms., etc., and converts to lowercase for normalization.
    """
    return re.sub(r'\b(Dr\.|Mr\.|Ms\.|Prof\.)\b', '', name).strip().lower()


# -------------------- FacultyInfo Table Functions --------------------

# Helper function to retrieve all faculty names from FacultyInfo
def get_all_faculty_info_names():
    connection = connect_db()
    if connection is None:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM FacultyInfo")
        results = cursor.fetchall()
        faculty_names = [row[0] for row in results]
        logging.info("Retrieved %d faculty names from FacultyInfo.", len(faculty_names))
        return faculty_names
    except mysql.connector.Error as err:
        logging.error("Error retrieving faculty names from FacultyInfo: %s", err)
        return []
    finally:
        cursor.close()
        connection.close()


# Helper function to retrieve all faculty records from FacultyInfo
def get_all_faculty_info_records():
    connection = connect_db()
    if connection is None:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name, research_area, google_scholar_link FROM FacultyInfo")
        results = cursor.fetchall()
        logging.info("Retrieved %d faculty records from FacultyInfo.", len(results))
        return results
    except mysql.connector.Error as err:
        logging.error("Error retrieving faculty records from FacultyInfo: %s", err)
        return []
    finally:
        cursor.close()
        connection.close()


# Helper function to retrieve full faculty details by name from FacultyInfo
def get_faculty_info_details(name):
    connection = connect_db()
    if connection is None:
        return None
    try:
        cursor = connection.cursor()
        sql = """
        SELECT name, email, ext_number, phone_number, block_location, 
               floor_location, room_number, workstation, research_area, google_scholar_link 
        FROM FacultyInfo WHERE name = %s
        """
        cursor.execute(sql, (name,))
        result = cursor.fetchone()
        if result:
            details = {
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
            }
            logging.info("Retrieved details for faculty member: %s", name)
            return details
        else:
            logging.warning("No details found for faculty member: %s", name)
            return None
    except mysql.connector.Error as err:
        logging.error("Error retrieving faculty details from FacultyInfo: %s", err)
        return None
    finally:
        cursor.close()
        connection.close()


@tool
def get_faculty_by_research_area(search_research_area: str) -> str:
    """
    Returns a list of FacultyInfo members matching the given research area based on fuzzy matching input is like "IOT" , "AI/ML" etc.
    """
    results = get_all_faculty_info_records()
    if not results:
        return "No faculty records found in FacultyInfo."

    # Use fuzzy matching to find close matches to the search query
    matches = []
    for name, research_area, google_scholar_link in results:
        if fuzz.partial_ratio(search_research_area.lower(), research_area.lower()) > 70:  # Adjusted threshold
            matches.append({
                'name': name,
                'research_area': research_area,
                'google_scholar_link': google_scholar_link
            })

    if matches:
        return (
                f"Faculty in FacultyInfo matching research area '{search_research_area}':\n" +
                "\n".join([
                    f"- {m['name']} (Research Area: {m['research_area']}, Google Scholar: {m['google_scholar_link']})"
                    for m in matches
                ])
        )
    else:
        return f"No FacultyInfo members found with a research area matching '{search_research_area}'."


@tool
def search_faculty_info_by_name(search_name: str) -> str:
    """
    Returns FacultyInfo details based on fuzzy matching of the provided name.
    returns phone number , email , work station , block location etc.
    IOT Department Only , try to use this first. If cannot find data , go to global function.
    """

    detailed = True
    results = get_all_faculty_info_records()
    if not results:
        return "No faculty records found in FacultyInfo."

    # Normalize search name
    normalized_search = normalize_name(search_name)

    # Use fuzzy matching to find the closest match on normalized names
    faculty_names = [normalize_name(name) for name, _, _ in results]
    matches = process.extract(normalized_search, faculty_names, limit=1, scorer=fuzz.token_sort_ratio)
    best_match = matches[0] if matches else None

    if best_match and best_match[1] >= 70:
        # Find the original name from results
        index = faculty_names.index(best_match[0])
        original_name = results[index][0]
        # Retrieve full details
        details = get_faculty_info_details(original_name)
        if details:
            if detailed:
                return (
                        f"Details for '{original_name}' in FacultyInfo:\n" +
                        "\n".join([f"{key.capitalize()}: {value}" for key, value in details.items()])
                )
            else:
                # Return basic details
                basic_info = {
                    'name': details['name'],
                    'email': details['email'],
                    'phone_number': details['phone_number'],
                    'research_area': details['research_area']
                }
                return (
                        f"Details for '{original_name}' in FacultyInfo:\n" +
                        "\n".join([f"{key.capitalize()}: {value}" for key, value in basic_info.items()])
                )
        else:
            return f"No details found for '{original_name}' in FacultyInfo."
    else:
        # Attempt to find the closest match even with lower confidence
        closest_match = process.extractOne(normalized_search, faculty_names, scorer=fuzz.token_sort_ratio)
        if closest_match:
            original_name = results[faculty_names.index(closest_match[0])][0]
            return (f"No suitable match found for '{search_name}' in FacultyInfo. "
                    f"Closest match: '{original_name}' (Score: {closest_match[1]}). "
                    f"Please verify the information.")
        else:
            return f"No suitable match found for '{search_name}' in FacultyInfo."


@tool
def get_faculty_info_details_by_name(name: str) -> str:
    """
    Returns comprehensive details of a FacultyInfo member by name.
    """
    details = get_faculty_info_details(name)
    if details:
        return (
                "FacultyInfo Details:\n" +
                "\n".join([f"{key.capitalize()}: {value}" for key, value in details.items()])
        )
    else:
        return f"No details found for FacultyInfo member '{name}'."


# -------------------- Faculty Table Functions (Global Search) --------------------

# Helper function to retrieve all faculty names from Faculty
def get_all_faculty_names():
    connection = connect_db()
    if connection is None:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM Faculty")
        result = cursor.fetchall()
        faculty_names = [row[0] for row in result]
        logging.info("Retrieved %d faculty names from Faculty.", len(faculty_names))
        return faculty_names
    except mysql.connector.Error as err:
        logging.error("Error retrieving names from Faculty: %s", err)
        return []
    finally:
        cursor.close()
        connection.close()


# Function to query the database and return faculty details by name from Faculty
def get_faculty_details_by_name(name):
    connection = connect_db()
    if connection is None:
        return None

    try:
        cursor = connection.cursor()
        sql = """
        SELECT name, position, email, phone, department, img_url, qualifications, expertise, achievements
        FROM Faculty WHERE name = %s
        """
        cursor.execute(sql, (name,))
        result = cursor.fetchone()

        if result:
            details = {
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
            logging.info("Retrieved details for faculty member: %s", name)
            return details
        else:
            logging.warning("No details found for faculty member: %s", name)
            return None
    except mysql.connector.Error as err:
        logging.error("Error retrieving details from Faculty: %s", err)
        return None
    finally:
        cursor.close()
        connection.close()


# Function to find the best matching faculty using fuzzy matching from Faculty
def find_best_match(input_name):
    faculty_names = get_all_faculty_names()
    if not faculty_names:
        return None

    # Use fuzzy matching to find the closest match
    best_match, score = process.extractOne(input_name, faculty_names)
    logging.info("Best match: %s (Score: %d)", best_match, score)

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
            return "No details found for the best match."
    else:
        return "No suitable match found."


@tool
def find_best_match_tool(input_name: str) -> str:
    """
    Performs Global Search
    Finds and returns the best matching details for faculty member from Global Faculty table for the given input name
    such as phone number , email etc.

    returns link to photo of the faculty too
    """
    best_match = find_best_match(input_name)
    if best_match:
        faculty_details = get_faculty_details_by_name(best_match)
        if faculty_details:
            return (
                    f"Best match: {best_match}\n"
                    f"Details:\n" +
                    "\n".join([f"{key.capitalize()}: {value}" for key, value in faculty_details.items()])
            )
        else:
            return f"Best match: {best_match}\nNo additional details found."
    else:
        return "No suitable match found."


@tool
def get_best_match_details_tool(input_name: str) -> str:
    """
    Finds the best match for a faculty member from Faculty table and returns their details.
    """
    best_match_response = find_best_match_tool(input_name)
    return best_match_response


# -------------------- Main Execution --------------------

if __name__ == "__main__":


    logging.info("Searching for FacultyInfo members in the research area 'IoT':")
    print(get_faculty_by_research_area.invoke("IoT"))

    logging.info("\nSearching for FacultyInfo by name (Detailed):")
    search_name = "Sandeep Singh"
    print(search_faculty_info_by_name.invoke({"search_name": search_name}))

    # Example queries for Faculty (Global Search)
    logging.info("\n=== Faculty Table (Global Search) Queries ===")

    logging.info("Finding best match for faculty name 'Somya Goyel':")
    input_name = "somya goyel"  # Replace this with the name you're searching for
    print(find_best_match_tool.invoke(input_name))

