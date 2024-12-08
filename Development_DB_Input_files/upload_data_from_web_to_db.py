import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import re  # Import regex module

# List of URLs to scrape
urls = [
    'https://jaipur.manipal.edu/foe/faculty-list.php'
]

# Create a list to hold all faculty details
faculty_list = []


# Function to clean up text by stripping whitespace and newlines
def clean_text(text):
    return text.strip().replace('\n', ' ').replace('  ', ' ')


# Helper function to extract email and phone number
def extract_contact_details(modal):
    email = None
    phone = None
    contact_items = modal.find_all('li')  # Find all <li> tags that might contain contact info
    for item in contact_items:
        item_text = item.get_text()

        # Check for email
        if '@' in item_text:
            email = clean_text(item_text)

        # Check for phone number using a regex that matches 10-digit numbers (with or without +, spaces, etc.)
        phone_match = re.search(r'\+?\d{10,}', item_text.replace(' ', ''))  # Match continuous digit sequences of 10 or more digits
        if phone_match:
            phone = clean_text(phone_match.group())  # Extract the matched phone number
    return email, phone


# Loop through each URL, send request, and extract faculty data
for url in urls:
    # Send a GET request to fetch the webpage content
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract all faculty boxes (assuming each faculty section is inside a div with class 'home-faculty-box')
    faculty_boxes = soup.find_all('div', class_='home-faculty-box')

    # Loop through each faculty box and extract information
    for box in faculty_boxes:
        name = clean_text(box.find('h2').text)  # Extract and clean name
        position = clean_text(box.find('h3').text) if box.find('h3') else None
        department = clean_text(box.find('p').text) if box.find('p') else None  # Extract department
        img_url = box.find('img')['src'] if box.find('img') else None  # Extract image URL

        # Extract additional details like email and phone
        # Assume the contact details are found in another part of the page or modal
        modal_id = box.find('a')['data-bs-target'] if box.find('a') else None
        modal = soup.find('div', id=modal_id.replace('#', '')) if modal_id else None

        # Extract email and phone using the helper function
        email, phone = extract_contact_details(modal) if modal else (None, None)

        # Extract qualifications, expertise, and achievements
        qualifications = [clean_text(li.text) for li in modal.find_all('li') if 'PHD' in li.text or 'M.TECH' in li.text or 'B.SC' in li.text]
        expertise = [clean_text(li.text) for li in modal.find_all('li') if 'Applications' in li.text or 'Computer Vision' in li.text]
        achievements = [clean_text(li.text) for li in modal.find_all('li') if 'Excellence Award' in li.text]

        details = {
            'name': name,
            'position': position,
            'email': email,
            'phone': phone,
            'department': department,  # Add department information
            'img_url': img_url,  # Add image URL
            'qualifications': qualifications,  # Add qualifications
            'expertise': expertise,  # Add expertise
            'achievements': achievements,  # Add achievements
        }
        faculty_list.append(details)


# Fuzzy match function
def get_best_matching_faculty(input_name):
    faculty_names = [faculty['name'] for faculty in faculty_list]
    best_match, score = process.extractOne(input_name, faculty_names)
    if score > 70:  # Set a confidence threshold
        for faculty in faculty_list:
            if faculty['name'] == best_match:
                return faculty
    return None


# Function to display the faculty details in a readable format
def print_faculty_details(faculty):
    if faculty:
        print(f"Name: {faculty['name']}")
        print(f"Position: {faculty['position']}")
        print(f"Email: {faculty['email']}")
        print(f"Phone: {faculty['phone']}")
        print(f"Department: {faculty['department']}")  # Print the department information
        print(f"Image URL: {faculty['img_url']}")  # Print the image URL
        print(f"Qualifications: {', '.join(faculty['qualifications'])}")  # Print qualifications
        print(f"Expertise: {', '.join(faculty['expertise'])}")  # Print expertise
        print(f"Achievements: {', '.join(faculty['achievements'])}")  # Print achievements
        print("\n" + "-" * 50 + "\n")
    else:
        print("No matching faculty member found.")


# Input name to search for
input_name = "geeta rani"  # Example input

# Get faculty details based on fuzzy matching
matched_faculty = get_best_matching_faculty(input_name)

# Print the matched faculty details
#print_faculty_details(matched_faculty)

import mysql.connector

# Function to upload data to the MySQL database
def upload_to_db(faculty_list):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="ManipalUniversityJaipur"
        )

        # Create a cursor object to execute SQL queries
        cursor = conn.cursor()

        # Insert each faculty member's data into the Faculty table
        for faculty in faculty_list:
            sql = """
            INSERT INTO Faculty (name, position, email, phone, department, img_url, qualifications, expertise, achievements)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Join qualifications, expertise, and achievements as comma-separated strings
            qualifications_str = ', '.join(faculty['qualifications']) if faculty['qualifications'] else None
            expertise_str = ', '.join(faculty['expertise']) if faculty['expertise'] else None
            achievements_str = ', '.join(faculty['achievements']) if faculty['achievements'] else None

            # Execute the SQL query with the faculty details
            cursor.execute(sql, (
                faculty['name'],
                faculty['position'],
                faculty['email'],
                faculty['phone'],
                faculty['department'],
                faculty['img_url'],
                qualifications_str,
                expertise_str,
                achievements_str
            ))

        # Commit the transaction
        conn.commit()

        print("Data uploaded successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Example usage
upload_to_db(faculty_list)
