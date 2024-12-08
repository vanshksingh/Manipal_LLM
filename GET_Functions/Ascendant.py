import mysql.connector
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import GoogleGenerativeAI
import json
import os
from datetime import datetime
import streamlit as st
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.tools import tool
from langchain.tools.render import render_text_description
from langchain_core.output_parsers import JsonOutputParser
from operator import itemgetter
import mysql.connector
import subprocess
from fuzzywuzzy import process
import glob

# Define the file path for saving chat history
CHAT_HISTORY_FILE = "chat_history.json"
api_key = "AIzaSyAIsE4C0ZjwCuO0A6S7IEjszpY9MBjAgWE"
directory = '/Users/vanshkumarsingh/Desktop/BEEHIVE/pythonProject/generated-pictures'


# Ping Google DNS to check internet connection
def ping_google_dns():
    try:
        output = subprocess.run(['ping', '8.8.8.8', '-c', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if output.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


Online = ping_google_dns()

# Set up the LLM model
if Online:
    st.toast("Using Gemini.")
    model = GoogleGenerativeAI(model="models/gemini-1.5-flash", google_api_key=api_key)
else:
    st.toast("Using Mistral")
    model = Ollama(model='mistral:instruct')

chat_history = []  # Store the chat history

# Establish connection to MySQL database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Set your password for MySQL here
    database="ManipalUniversityJaipur"
)
cursor = conn.cursor()


# Function to retrieve all faculty names from the database
def get_faculty_names():
    cursor.execute("SELECT name FROM Faculty")
    results = cursor.fetchall()
    return [row[0] for row in results]


# Function to use fuzzywuzzy logic to match the closest faculty name
def match_faculty_name(user_input):
    faculty_names = get_faculty_names()
    best_match, match_score = process.extractOne(user_input, faculty_names)
    if match_score > 70:  # Threshold for a good match
        return best_match
    return None


# Function to get current time
def get_current_time():
    return datetime.now().strftime('%H:%M')


# Function to get the room number where the faculty member is currently
@tool
def where_is_faculty(faculty_name: str) -> str:
    """Returns the room number where the faculty is currently, based on the current time."""
    faculty_name = match_faculty_name(faculty_name)
    current_time = get_current_time()
    query = f"""
    SELECT room_number FROM RoomTimings
    WHERE faculty_reg_no = (SELECT reg_no FROM Faculty WHERE name = '{faculty_name}')
    AND '{current_time}' BETWEEN SUBSTRING(time_slot, 1, 5) AND SUBSTRING(time_slot, 7, 11);
    """
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return f"{faculty_name} is currently in room {result[0]}."
    else:
        return f"{faculty_name} is not in any room at the current time."


# Function to check if the faculty member is free at the current time
@tool
def is_faculty_free(faculty_name: str) -> str:
    """Checks if the faculty is currently free or in a meeting/class."""
    faculty_name = match_faculty_name(faculty_name)
    current_time = get_current_time()
    query = f"""
    SELECT * FROM RoomTimings
    WHERE faculty_reg_no = (SELECT reg_no FROM Faculty WHERE name = '{faculty_name}')
    AND '{current_time}' BETWEEN SUBSTRING(time_slot, 1, 5) AND SUBSTRING(time_slot, 7, 11);
    """
    cursor.execute(query)
    result = cursor.fetchall()
    if result:
        return f"{faculty_name} is currently busy."
    else:
        return f"{faculty_name} is currently free."


# Function to get the next free slot for the faculty member
@tool
def next_free_slot(faculty_name: str) -> str:
    """Returns the next free time slot for the faculty member."""
    faculty_name = match_faculty_name(faculty_name)
    current_time = get_current_time()
    query = f"""
    SELECT time_slot FROM RoomTimings
    WHERE faculty_reg_no = (SELECT reg_no FROM Faculty WHERE name = '{faculty_name}')
    AND SUBSTRING(time_slot, 1, 5) > '{current_time}'
    ORDER BY SUBSTRING(time_slot, 1, 5) ASC
    LIMIT 1;
    """
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return f"{faculty_name}'s next slot is free after {result[0]}."
    else:
        return f"{faculty_name} has no more scheduled slots today."


# Function to get contact information of the faculty member
@tool
def contact_information(faculty_name: str) -> str:
    """Returns the contact information of the faculty member."""
    faculty_name = match_faculty_name(faculty_name)
    query = f"""
    SELECT phone_number, email FROM Faculty
    WHERE name = '{faculty_name}';
    """
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        phone, email = result
        return f"Contact Information for {faculty_name}:\nPhone Number: {phone}\nEmail: {email}"
    else:
        return f"No contact information found for {faculty_name}."


# Function to list all faculties
@tool
def list_all_faculties() -> str:
    """Returns a list of all faculty members."""
    cursor.execute("SELECT name FROM Faculty;")
    results = cursor.fetchall()
    if results:
        faculty_list = "\n".join([f"- {row[0]}" for row in results])
        return f"List of All Faculties:\n{faculty_list}"
    else:
        return "No faculty members found in the database."


# Define tools available
tools = [
    where_is_faculty,
    is_faculty_free,
    next_free_slot,
    contact_information,
    list_all_faculties
]

# Configure the system prompts
rendered_tools = render_text_description(tools)
system_prompt = f"""You answer questions with simple answers and no funny stuff. The current time is {get_current_time()}, use it in SQL queries if needed.
    You are an AI SQL generator. The database schema is as follows:

    Faculty table:
    - reg_no: VARCHAR(10)
    - name: VARCHAR(100)
    - age: INT
    - qualification: VARCHAR(50)
    - gender: CHAR(1)
    - phone_number: VARCHAR(13)
    - email: VARCHAR(100)
    - faculty_block: VARCHAR(10)
    - office_number: VARCHAR(10)

    RoomTimings table:
    - room_number: VARCHAR(10)
    - floor_number: INT
    - faculty_reg_no: VARCHAR(10) (Foreign key referencing Faculty)
    - time_slot: VARCHAR(20)

    You have access to the following set of tools. Here are the names and descriptions for each tool:

{rendered_tools}

Given the user input, return the name and input of the tool to use. Return your response as a JSON blob with 'name' and 'arguments' keys. The value associated with the 'arguments' key should be a dictionary of parameters."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])


# Define a function which returns the chosen tools as a runnable, based on user input
def tool_chain(model_output):
    tool_map = {tool.name: tool for tool in tools}
    chosen_tool = tool_map.get(model_output.get("name"))
    if chosen_tool:
        return itemgetter("arguments") | chosen_tool
    else:
        return "I couldn't find a suitable tool to handle your request."


# The main chain: an LLM with tools
chain = prompt | model | JsonOutputParser() | tool_chain


# Function to save chat history
def save_chat_history():
    chat_history_data = []
    for message in chat_history:
        if isinstance(message, HumanMessage) or isinstance(message, AIMessage):
            chat_history_data.append({
                "type": "human" if isinstance(message, HumanMessage) else "ai",
                "content": message.content
            })
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(chat_history_data, f, default=str)


# Function to clear chat history
def clear_chat_history():
    global chat_history
    chat_history = []
    if os.path.exists(CHAT_HISTORY_FILE):
        os.remove(CHAT_HISTORY_FILE)


# Function to delete all files in the generated pictures directory
def delete_all_files():
    files = glob.glob(os.path.join(directory, '*'))
    for file in files:
        os.remove(file)
    return len(files)


# Load chat history from file if it exists
if os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE, "r") as f:
        try:
            chat_history_data = json.load(f)
            for item in chat_history_data:
                if item['type'] == 'human':
                    chat_history.append(HumanMessage(content=item['content']))
                elif item['type'] == 'ai':
                    chat_history.append(AIMessage(content=item['content']))
        except json.JSONDecodeError:
            pass

# Set up message history
msgs = StreamlitChatMessageHistory(key="langchain_messages")
if len(msgs.messages) == 0:
    msgs.add_ai_message(
        "From calculations to image generation, data analysis to task prioritization, I'm here to assist. Always on, always learning. How can I help you today?")

# Set the page title
st.title("Ascendant Ai")

# Render the chat history
for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)

# React to user input
if input_text := st.chat_input("What is up?"):

    if input_text.strip().lower() == "/clear":
        clear_chat_history()
        st.chat_message("assistant").write("Chat history cleared.")
        delete_all_files()
        st.toast("Data Cleared")
    else:
        # Match faculty name using fuzzy logic
        matched_name = match_faculty_name(input_text)

        st.chat_message("user").write(input_text)
        msgs.add_user_message(input_text)

        # If a match is found, use it in the query
        if matched_name:
            if "free" in input_text.lower() or "available" in input_text.lower():
                response = is_faculty_free(matched_name)
            elif "where" in input_text.lower():
                response = where_is_faculty(matched_name)
            elif "next slot" in input_text.lower():
                response = next_free_slot(matched_name)
            elif "contact" in input_text.lower() or "contact information" in input_text.lower():
                response = contact_information(matched_name)


            else:
                # No specific tool found, use the AI chain

                bar = st.progress(0)
                response = chain.invoke({"input": input_text, "chat_history": chat_history})
                chat_history.append(HumanMessage(content=input_text))
                chat_history.append(AIMessage(content=response))
                bar.progress(90)
        else:
            # If no faculty name match, use the AI chain for general queries

            bar = st.progress(0)
            response = chain.invoke({"input": input_text, "chat_history": chat_history})
            chat_history.append(HumanMessage(content=input_text))
            chat_history.append(AIMessage(content=response))
            bar.progress(90)

        # Display and save the response
        st.chat_message("assistant").write(str(response))
        msgs.add_ai_message(response)
        save_chat_history()
        st.toast("Context Updated")
        if 'bar' in locals():
            bar.progress(100)
            clear_chat_history()
            delete_all_files()