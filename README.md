# Manipal_LLM
 Intelligent Database Query System with LLM and Streamlit

![WhatsApp Image 2024-12-01 at 19 36 18 (1)](https://github.com/user-attachments/assets/79739b6b-d653-4f55-bab5-6e7fc85b67ff)

# AI-Powered Offline Database Query System

## Overview

This repository contains the code and documentation for an offline, AI-powered database query system tailored for Manipal University Jaipur's IoT Department. The system enables natural language querying to retrieve departmental information like:

- Phone numbers
- Email addresses
- Timetables
- Free slots
- Workstations
- Research domains

The solution leverages cutting-edge AI technologies for high accuracy, while ensuring complete offline functionality for data security.

## Features

### 1. **AI-Powered Natural Language Interface**

- Uses state-of-the-art instruct models like Qwen2.5-0.5B, 1.0B, 1.5B Instruct, and Mistral-Instruct from Ollama.
- Processes user queries contextually, optimizing for speed and accuracy.

### 2. **Dynamic Tool Chaining**

- Powered by LangChain to dynamically select tools based on query intent.
- Uses Tool Chaining and Agent Executors for seamless query resolution, including error correction.

### 3. **Fuzzy Matching for Enhanced Search**

- Integrates FuzzyWuzzy to handle typos and name mismatches.
- Ensures closest valid database entries are matched.

### 4. **Secure Offline Operation**

- Operates entirely offline using a database hosted on an XAMPP server.
- Interacts with the database via SQL Connector for precise query handling.

### 5. **Timestamp-Based Context Matching**

- Automatically generates timestamps to enhance the accuracy of time-sensitive queries.

### 6. **Interactive Front-End**

- Built using Streamlit for an intuitive and dynamic user interface.
- Displays the system’s "thought process," including tool selection and retrieval steps.

### 7. **Scalability**

- Modular design supports future integration of larger models or cloud-based processing.

## Installation

### Prerequisites

- Python 3.10+
- XAMPP Server
- Libraries:
  - LangChain
  - Streamlit
  - FuzzyWuzzy
  - SQL Connector

### Steps
 Run the Streamlit app:
   ```bash
   streamlit run main.py
   ```

## Usage

1. Launch the Streamlit app in your browser.
2. Input natural language queries to retrieve information (e.g., "Who is available now?" or "Show email addresses of staff in IoT department").
3. View results along with the system’s reasoning process.

## Folder Structure

```
├── app.py                # Main application file
├── database              # Database schema and example data
├── models                # AI models and configurations
├── utils                 # Utility scripts for tool chaining and query processing
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Future Enhancements

### 1. Integration of Larger Models

- Incorporate cloud-based or larger offline models for handling complex queries.

### 2. Expansion to Other Departments

- Modify database schemas and logic to support other university departments.

### 3. Enhanced Front-End Features

- Add voice input or chat-based interaction for improved usability.

### 4. Data Analytics

- Implement analytics for tracking usage patterns and optimizing departmental operations.

## Contribution Guidelines

1. Fork the repository.
2. Create a new branch for your feature/bugfix.
3. Commit your changes with clear messages.
4. Submit a pull request detailing your contributions.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Acknowledgments

Special thanks to Manipal University Jaipur for the opportunity to develop this solution and to the creators of the AI models and tools integrated into the system.

## Contact

For queries or feedback, please contact the repository maintainer.

