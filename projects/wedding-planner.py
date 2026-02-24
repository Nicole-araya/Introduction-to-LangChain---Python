from langchain.tools import tool
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Dict, Any
from tavily import TavilyClient
from langchain.agents import AgentState
from pydantic import BaseModel
from langchain.tools import ToolRuntime
from langchain.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
import asyncio

# --- DATA MODELS ---

class WeddingState(AgentState):
    """State management for wedding planning conversation"""
    origin: str
    destination: str
    guest_count: str
    genre: str

# --- Web Search Tool --- 

@tool
def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information using Tavily."""
    return tavily_client.search(query)

# --- Agent Factory Functions ---

async def create_flight_agent () -> create_agent:
    '''
    Creates an MCP-based flight booking agent.
    '''
    flight_client = MultiServerMCPClient(
        {
            "travel_server": {
                    "transport": "streamable_http",
                    "url": "https://mcp.kiwi.com"
                }
        }
    )

    flight_tools = await flight_client.get_tools()
    
    agent = create_agent(
        model='gpt-5-nano',
        tools=flight_tools,
        system_prompt = 
        """
        You are a travel agent specializing in wedding flight bookings.
        
        Your job is to search for flights and present a maximum of 4 different flight options.
        
        CRITICAL INSTRUCTIONS:
        - Use the provided origin and destination to search for flights
        - Search for dates within the next 12 months
        - DO NOT ask for any additional information
        - DO NOT ask clarifying questions
        - Present multiple flight options (a maximum of 4 options) with:
          * Departure date
          * Airline name
          * Departure and arrival times
          * Price
          * Flight duration
        - Provide a variety of options at different price points (budget, mid-range, premium)
        - Format your response clearly with all flight details
        
        Simply search and present the options - nothing more.
        """
    )

    return agent


def create_venue_agent ()-> create_agent:
    
    agent = create_agent(
        model='gpt-5-nano',
        tools=[web_search],
        system_prompt="""
        You are a wedding venue specialist.
        
        Your job is to search and present a maximum of 4 different wedding venue options.
        
        CRITICAL INSTRUCTIONS:
        - Use the provided destination and guest capacity to search for wedding venues
        - DO NOT ask for any additional information
        - DO NOT ask about budget, style preferences, or other details
        - Search the web and present multiple venue options (a maximum of 4 options) with:
          * Venue name
          * Location/address
          * Guest capacity
          * Estimated price range
        - Provide a variety of options: outdoor/indoor, luxury/budget-friendly, traditional/modern
        - Be specific and detailed about each venue
        
        Simply search and present the options based on what you're given - nothing more.
        """
    )

    return agent

def create_playlist_agent () -> create_agent:

    agent = create_agent(
        model='gpt-5-nano',
        tools=[web_search],
        system_prompt="""
        You are a wedding music curator and DJ specialist.
        
        Your job is to create a wedding playlist with a maximum of 5 songs.
        
        CRITICAL INSTRUCTIONS:
        - Use the provided music genre to search for appropriate wedding songs
        - DO NOT ask for any additional information
        - DO NOT ask about specific moments (first dance, reception, etc.)
        - Search the web and create a diverse playlist with a maximum of 5 songs including:
          * Song title
          * Artist name
        - Ensure variety in tempo and mood while staying within the requested genre
        - Format as a clear numbered list
        
        Simply search and create the playlist based on the genre provided - nothing more.
        """
    )

    return agent


# --- Sub-Agent Search Tools ---

@tool
async def search_flights( runtime: ToolRuntime)->str:
    ''' Search for flights using the flight agent. '''
    
    origin = runtime.state["origin"]
    destination = runtime.state["destination"]
    response = await flight_agent.ainvoke({"messages": [HumanMessage(content=f"Find me flights from {origin} to {destination}")]})
    return response['messages'][-1].content

@tool
async def search_venues(runtime: ToolRuntime)->str:
    ''' Search for venues using the venue agent. '''
    guest_count = runtime.state["guest_count"]
    destination = runtime.state["destination"]
    response = await venue_agent.ainvoke({"messages": [HumanMessage(content=f"Find me wedding venues that can accommodate {guest_count} guests in {destination}")]},
                                         {"recursion_limit": 50} )
    return response['messages'][-1].content

@tool
async def search_playlist(runtime: ToolRuntime)->str:
    ''' Search for playlists using the playlist agent. '''
    genre = runtime.state["genre"]
    response = await playlist_agent.ainvoke({"messages": [HumanMessage(content=f"Find me wedding playlists that fit the {genre} genre")]},
                    {"recursion_limit": 50} )
    return response['messages'][-1].content


# --- State Update Tool ---

@tool
def update_wedding_state(date:str, origin:str, destination:str, guest_count:str, genre:str, runtime: ToolRuntime) -> str:
    """Update the wedding state with new information"""
    
    return Command(update= {
        "origin": origin, 
        "destination": destination, 
        "guest_count": guest_count, 
        "genre": genre, 
        "messages": [ToolMessage("Wedding state updated", tool_call_id=runtime.tool_call_id)]}
    )
  

# --- Display Function ---

def print_welcome_message() -> None:
    print("\n" + "=" * 50)
    print("💒 WELCOME TO WEDDING PLANNER 💒".center(50))
    print("=" * 50)
    print("\nI'll help you plan your dream wedding!")
    print("Just tell me about your preferences and I'll coordinate:")
    print("• Flight bookings")
    print("• Venue selection")
    print("• Music playlists")
    print("\nType '/bye' to end the conversation.\n")


# --- Main Application ---

async def main():

    global tavily_client, flight_agent, venue_agent, playlist_agent
    
    load_dotenv()
    
    tavily_client = TavilyClient()

    flight_agent = await create_flight_agent()
    venue_agent = create_venue_agent()
    playlist_agent = create_playlist_agent()

    coordinator_agent = create_agent(
        model="gpt-5-nano",
        system_prompt="""
        You are an expert wedding planner coordinator having a natural conversation with a client.
        
        YOUR ROLE:
        You help plan weddings by gathering information and coordinating flights, venues, and music.
        Be warm, enthusiastic, and conversational - like a friend helping plan their special day.
        
        INFORMATION YOU NEED (track what you already have):
        - origin: departure city for flights
        - destination: wedding location/city
        - guest_count: number of guests
        - genre: music genre preference
        
        HOW TO HANDLE CONVERSATIONS:
        
        1. FIRST MESSAGE / NEW INFORMATION:
        - If user provides wedding details, extract what they give you
        - Call update_wedding_state with ANY information you extract (even if incomplete)
        - If you have enough info for a search (origin + destination for flights, etc.), 
            offer to search immediately
        - If missing critical info, ask conversationally for what you need
        
        2. SUBSEQUENT MESSAGES:
        - Check the current state to see what information you already have
        - DON'T ask for information you already have in the state
        - DON'T repeat searches you've already done in this conversation
        - If user adds new details, update the state and offer new searches if relevant
        - If user changes their mind (new date, location, etc.), update state and re-search
        
        3. WHEN TO SEARCH:
        - search_flights: Only when you have origin AND destination
        - search_venues: Only when you have destination AND guest_count
        - search_playlist: Only when you have genre
        - DON'T search if you've already searched and nothing relevant changed
        - If user explicitly asks to search again, do it
        
        4. CONVERSATIONAL FLOW:
        - Start warm and welcoming
        - Extract info naturally from their messages
        - Summarize what you understand so far
        - Ask for missing pieces conversationally (not as a checklist)
        - When you have enough info, offer to search: "I can look up flights now if you'd like!"
        - After showing results, ask if they want to refine or explore other aspects
        
        EXAMPLES OF GOOD RESPONSES:
        
        User: "I'm getting married in Paris"
        You: "How exciting! A Paris wedding sounds absolutely beautiful! 
        A few quick questions to help me find the best options for you:
        - Where will you be flying from?
        - How many guests are you expecting?
        - Any music preferences for the reception?"
        
        User: "Coming from New York with about 100 guests. We love pop music."
        You: [calls update_wedding_state, then immediately] "Perfect! Let me find you some options..."
        [calls search_flights, search_venues, search_playlist]
        [presents results enthusiastically]
        clear
        User: "Actually, can we change it to 150 guests?"
        You: [calls update_wedding_state with guest_count: "150"]
        "Of course! Let me find venues that can accommodate 150 guests instead..."
        [calls search_venues only - no need to re-search flights or playlist]
        
        CRITICAL RULES:
        - Be conversational and natural, not robotic
        - Don't repeat information searches unless explicitly asked or something changed
        - Track conversation context using the state
        - Celebrate with the couple - this is a happy occasion!
        - If unsure about something, ask in a friendly way
        - After providing results, invite further conversation: "What do you think? Want to 
        explore other dates or locations?"
        
        Remember: You're not just a tool executor - you're their wedding planning partner!
        """,
        tools=[search_flights, search_venues, search_playlist, update_wedding_state],
        checkpointer=InMemorySaver(), 
        state_schema= WeddingState
    )

    config = {"configurable": {"thread_id": "1"}}

    print_welcome_message()
    
    while True:
        try:
            user_input = input("You: ")
            
            if not user_input:
                continue
            
            if user_input.lower() == '/bye':
                print("\n💒 Wedding Planner: Thank you for using Wedding Planner!")
                print("Best wishes for your special day! 💐\n")
                break
            
            # Process user input
            response = await coordinator_agent.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config
            )

            message = response["messages"][-1].content
            print("\n\n💒 Wedding Planner:", message)

        except KeyboardInterrupt:
            print("\n\n💒 Wedding Planner: Goodbye! 👋\n")
            break


if __name__ == "__main__":
    
    asyncio.run(main())

