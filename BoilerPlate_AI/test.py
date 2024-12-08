from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, Tool, AgentType
from tool import get_faculty_availability, get_room_info  # Import tools
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish

# Create a callback handler to capture and print intermediate steps
class PrintCallbackHandler(BaseCallbackHandler):
    def on_agent_action(self, action: AgentAction, **kwargs):
        # Capture the agent's thought and the action it's taking
        #print(f"Thought: {action.log}")
        a=str(action.log).split('\n')
        print(a[0])

        #print(f"Action: {action.tool} with input {action.tool_input}")

    #def on_tool_end(self, output: str, **kwargs):
        # Capture the observation after the tool returns a result
        #print(f"Observation: {output}")

    #def on_agent_finish(self, finish: AgentFinish, **kwargs):
        # Capture the final answer once the agent completes the task
        #print(f"Final Answer: {finish.log}")

# Function to render a text description of available tools (mock implementation for illustration)
def render_text_description(tools):
    tool_descriptions = [f"{tool.name}: {tool.description}" for tool in tools]
    return "\n".join(tool_descriptions)

# Define tools available
tools = [get_faculty_availability, get_room_info]

# Configure the system prompts by rendering text descriptions for tools
rendered_tools = render_text_description(tools)
system_prompt = f"""
You are a helpful assistant who provides detailed and accurate information.
Ensure that you choose the correct tool based on the user's query and respond in a friendly, professional manner.
{rendered_tools}
If the query is unclear, ask for clarification.
"""

# Initialize the callback handler
callback_handler = PrintCallbackHandler()

# Initialize the Ollama model with the system prompt
model = Ollama(model="qwen2.5:3b-instruct", system=system_prompt)

# Initialize the agent with tools and callbacks
agent = initialize_agent(
    tools=tools,
    llm=model,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Dynamically choose the right tool based on user input
    system_prompt=system_prompt,  # Pass the system prompt
    # verbose=True,  # Enable verbose mode to print more detailed logs if needed
    #intermediate_steps=True,  # Note: Changed from 'intermediate_output' to 'intermediate_steps' if applicable
    callbacks=[callback_handler]  # Pass callbacks as a list
)

# Query the agent with a user input
query = "Can you tell me when Professor Smith is available and information about room 101?"

# Run the agent
response = agent.run(query)
print(f"\nAgent's Response:\n{response}")
