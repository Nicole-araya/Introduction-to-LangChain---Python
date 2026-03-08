
# AUNTENTIFICACION DE USUARIO
# SI ES EL USUARIO PUEDE LEER Y ENVIAR CORREOS
# PARA ENVIAR NECESITA APROBACION DEL USUARIO

from dotenv import load_dotenv
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelRequest, ModelResponse, wrap_model_call, dynamic_prompt 
from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage, ToolMessage
from langgraph.types import Command
from dataclasses import dataclass
from typing import Callable

@dataclass
class UserContext:
    email: str = "user@example.com"
    password: str = "1234"

class EmailState(AgentState):
    sender: str
    recipient: str
    subject: str
    body: str
    authenticated: bool = False


@tool
def read_email() -> str:
    """Read an email from the given address."""

    return f"From: John@example.com\nTo: user@example.com\n{"Hi Seán, I'm going to be late for our meeting tomorrow. Can we reschedule? Best, John."}"

@tool
def send_email(body: str, runtime: ToolRuntime) -> str:
    """Send an email to the given address with the given subject and body."""

    # fake email sending
    emisor = runtime.state.get("sender", "Unknown")
    receptor = runtime.state.get("recipient", "Unknown")
    subject = runtime.state.get("subject", "Unknown")
    return f"Email sent to {receptor} with subject '{subject}' and body '{body}' from {emisor}."

@tool
def update_email_state(sender:str, recipient:str, subject:str, body:str, runtime: ToolRuntime) -> str:
    """Update the email state with new information"""
    
    return Command(update= {
        "sender": sender, 
        "recipient": recipient, 
        "subject": subject, 
        "body": body, 
        "messages": [ToolMessage("Email state updated", tool_call_id=runtime.tool_call_id)]}
    )

@tool
def update_authenticated_state(email: str, password: str, runtime: ToolRuntime) -> str:
    """Update the authenticated state"""

    if email == runtime.context.email and password == runtime.context.password:
        return Command(update={
            "authenticated": True, 
            "messages": [ToolMessage("User authenticated", tool_call_id=runtime.tool_call_id)]})
    else:
        return Command(update={
            "authenticated": False, 
            "messages": [ToolMessage("Authentication failed", tool_call_id=runtime.tool_call_id)]})
    


@wrap_model_call
async def dynamic_tool_call(request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:

    """Dynamically call tools based on the runtime context"""

    authenticated = request.state.get("authenticated", False)
    
    if authenticated:
        tools=[read_email, send_email, update_email_state]
    else:
        tools=[update_authenticated_state]
    
    request = request.override(tools=tools) 

    return await handler(request)


@dynamic_prompt
def dynamic_prompt(request: ModelRequest) -> str:
    """Generate system prompt based on authentication status"""

    authenticated = request.state.get("authenticated")

    if authenticated:
        return "You are a helpful assistant that can read emails and send emails." \
        "Before sending an email, first update the email status with the sender, recipient, subject and body of the message to be sent"
    else:
        return "When you start, ask for the user's email and password to authenticate. " \
        "Say : 'WELCOME! Please provide your email and password to authenticate.'"



 
load_dotenv()

agent = create_agent(
    model="gpt-5-nano",
    tools=[update_authenticated_state, update_email_state, read_email, send_email],
    state_schema=EmailState,
    context_schema=UserContext,
    middleware=[
    dynamic_tool_call,
    dynamic_prompt,
    HumanInTheLoopMiddleware(
        interrupt_on={
            "update_authenticated_state": False,
            "read_email": False,
            "send_email": True,
        },
        description_prefix="Tool execution requires approval",),
    ],
)