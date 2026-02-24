from dotenv import load_dotenv
from langchain.agents import create_agent
from pydantic import BaseModel
from langchain.tools import tool
from typing import Dict, Any
from tavily import TavilyClient
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage  

class RecipeInfo(BaseModel):
    title: str
    duration: str
    ingredients: str
    steps: str

@tool
def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    return tavily_client.search(query)


if __name__ == "__main__":

    load_dotenv()
    tavily_client = TavilyClient()

    agent = create_agent(
        model="gpt-5-nano",
        system_prompt="" \
        "You are a expert personal chef that provides detailed recipes based on user given ingredients." \
        "Return the recipe in clean format whith line breaks for better readability.",
        response_format=RecipeInfo,
        tools=[web_search],
        checkpointer=InMemorySaver(), 
    )

    config = {"configurable": {"thread_id": "1"}}
    print("Welcome to Personal Chef! \nType '/bye' to end the conversation.")
    
    while True:
        user_input = input("\nUser:  ")

        if user_input.lower() == '/bye':
            print("\n\nPersonal Chef: See you later!")
            break
        
        response = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config
            )

        message = response["structured_response"]
        
        print("\n" + "="*50)
        print(f"🍳 RECIPE: {message.title}")
        print("="*50)
        print("Duration: ", message.duration)
        print("Ingredients:\n", message.ingredients, "\n")
        print("Steps:\n", message.steps, "\n")
        print("="*50)
