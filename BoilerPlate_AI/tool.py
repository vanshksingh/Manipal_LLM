import logging
from langchain.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

# Define the faculty availability function
@tool
def get_faculty_availability(faculty_name: str) -> str:
    """Returns the availability of a faculty member based on the name provided."""
    logger.debug(f"Calling get_faculty_availability with input: {faculty_name}")
    availability = f"Professor {faculty_name} is available from 10 AM to 2 PM today."
    logger.debug(f"Faculty availability result: {availability}")
    return availability

# Define the room info function
@tool
def get_room_info(room_number: str) -> str:
    """Returns information about a room."""
    logger.debug(f"Calling get_room_info with input: {room_number}")
    room_info = f"Room {room_number} is located on the 2nd floor and is available for booking."
    logger.debug(f"Room info result: {room_info}")
    return room_info
