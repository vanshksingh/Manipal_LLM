import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, Tool, AgentType

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish
from timetable_db_fetch import *
from faculty_detail_db import *

class PrintCallbackHandler(BaseCallbackHandler):
    def on_agent_action(self, action: AgentAction, **kwargs):
        # Capture the agent's thought and the action it's taking
        #print(f"Thought: {action.log}")
        a=str(action.log).split('\n')
        print(a[0])

        placeholder = st.empty()
        placeholder.status(a[0])


# Function to render a text description of available tools (mock implementation for illustration)
def render_text_description(tools):
    tool_descriptions = [f"{tool.name}: {tool.description}" for tool in tools]
    return "\n".join(tool_descriptions)

# Define tools available (first faculty detail and second is timetable)
tools = [get_faculty_by_research_area , search_faculty_info_by_name , find_best_match_tool ,
         check_if_free_now,get_weekly_timetable,get_daily_timetable,get_free_teachers,get_busy_teachers,get_next_free_slot,get_faculty_availability,]

# Configure the system prompts by rendering text descriptions for tools
rendered_tools = render_text_description(tools)
system_prompt = f"""
You are a helpful assistant who provides detailed, with accurate information .
Ensure that you choose the correct tool based on the user's query and respond in a friendly, professional manner.
{rendered_tools}
If the query is unclear, ask for clarification , if none is listed say no data found , insure names passed are accurate.
Refuse potentially bad requests.
"""


# Initialize the callback handler
callback_handler = PrintCallbackHandler()

# Initialize the Qwen2.5:3b-instruct model with the system prompt

model = Ollama(model="qwen2.5:3b-instruct", system=system_prompt)

# Initialize the agent with tools

agent = initialize_agent(
    tools=tools,
    llm=model,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Dynamically choose the right tool based on user input
    system_prompt=system_prompt,  # Pass the system prompt
    verbose=True,  # Enable verbose mode to print more detailed logs
    callbacks = [callback_handler] # Pass callbacks as a list
)
# Function to save chat history

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

        st.chat_message("assistant").write("Chat history cleared.")

        st.toast("Data Cleared")
    else:


        st.chat_message("user").write(input_text)
        msgs.add_user_message(input_text)

        response = agent.invoke(input_text)



        # Display and save the response
        st.chat_message("assistant").write(str(response['output']))
        msgs.add_ai_message(response['output'])


        st.toast("Finished processing user input")

