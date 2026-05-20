import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, deepgram, silero

# Load from backend/.env which has the real credentials
# override=True ensures we overwrite any existing env vars from root .env
env_path = Path(__file__).parent / "backend" / ".env"
load_dotenv(env_path, override=True)

# Debug: verify we loaded the correct credentials
print(f"🔑 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
print(f"🔑 Groq API Key: {'✅ Set' if os.getenv('GROQ_API_KEY') else '❌ Missing'}")

# Tool: Calculator (HAS PARAMETERS - Groq should handle this!)
@function_tool
async def calculate(operation: str, a: float, b: float) -> str:
    """
    Perform a mathematical calculation.
    
    Args:
        operation: The operation to perform: 'add', 'subtract', 'multiply', or 'divide'
        a: First number
        b: Second number
    """
    if operation == "add":
        result = a + b
        return f"{a} + {b} = {result}"
    elif operation == "subtract":
        result = a - b
        return f"{a} - {b} = {result}"
    elif operation == "multiply":
        result = a * b
        return f"{a} × {b} = {result}"
    elif operation == "divide":
        if b == 0:
            return "Error: Cannot divide by zero"
        result = a / b
        return f"{a} ÷ {b} = {result}"
    else:
        return f"Unknown operation: {operation}"

        return f"Unknown operation: {operation}"

# Tool: Temperature converter (HAS PARAMETERS)
@function_tool
async def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert temperature between Celsius, Fahrenheit, and Kelvin.
    
    Args:
        value: The temperature value to convert
        from_unit: The source unit: 'celsius', 'fahrenheit', or 'kelvin'
        to_unit: The target unit: 'celsius', 'fahrenheit', or 'kelvin'
    """
    # Convert to Celsius first
    if from_unit.lower() == "celsius":
        celsius = value
    elif from_unit.lower() == "fahrenheit":
        celsius = (value - 32) * 5/9
    elif from_unit.lower() == "kelvin":
        celsius = value - 273.15
    else:
        return f"Unknown unit: {from_unit}"
    
    # Convert from Celsius to target
    if to_unit.lower() == "celsius":
        result = celsius
    elif to_unit.lower() == "fahrenheit":
        result = celsius * 9/5 + 32
    elif to_unit.lower() == "kelvin":
        result = celsius + 273.15
    else:
        return f"Unknown unit: {to_unit}"
    
    return f"{value}° {from_unit} = {result:.2f}° {to_unit}"

# Tool: Text case converter (HAS PARAMETERS)
@function_tool
async def convert_text_case(text: str, case_type: str) -> str:
    """
    Convert text to different cases.
    
    Args:
        text: The text to convert
        case_type: Type of case: 'upper', 'lower', 'title', or 'reverse'
    """
    if case_type.lower() == "upper":
        return f"Uppercase: {text.upper()}"
    elif case_type.lower() == "lower":
        return f"Lowercase: {text.lower()}"
    elif case_type.lower() == "title":
        return f"Title case: {text.title()}"
    elif case_type.lower() == "reverse":
        return f"Reversed: {text[::-1]}"
    else:
        return f"Unknown case type: {case_type}"

# Tool: Time information (HAS PARAMETER - required for Groq!)
@function_tool
async def get_time_info(format_type: str = "full") -> str:
    """
    Get current time and date information.
    
    Args:
        format_type: Type of time info: 'time', 'date', 'full', or 'short'
    """
    from datetime import datetime
    now = datetime.now()
    
    if format_type.lower() == "time":
        return f"The time is {now.strftime('%I:%M %p')}"
    elif format_type.lower() == "date":
        return f"Today is {now.strftime('%A, %B %d, %Y')}"
    elif format_type.lower() == "full":
        return now.strftime("It's %I:%M %p on %A, %B %d, %Y")
    elif format_type.lower() == "short":
        return now.strftime("%I:%M %p, %m/%d/%Y")
    else:
        return now.strftime("It's %I:%M %p on %A, %B %d, %Y")

async def entrypoint(ctx: JobContext):
    print(f"Connecting to room: {ctx.room.name}")

    # Use Groq - Testing with PARAMETERIZED tools
    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile"
    )

    session = AgentSession(
        stt=deepgram.STT(),
        tts=deepgram.TTS(model="aura-luna-en"),  # Warm, friendly voice
        vad=silero.VAD.load(),
        llm=groq_llm,
    )

    # Create agent with 4 parameterized tools (all work with Groq!)
    agent = Agent(
        instructions="""You are a helpful, friendly voice assistant with calculator, temperature, text, and time tools.
        Keep your responses short and conversational.
        Use the appropriate tool based on what users ask for:
        - Calculator for math
        - Temperature converter for temperature conversions
        - Text converter for text manipulation
        - Time info for current time/date
        Be warm and engaging.""",
        tools=[calculate, convert_temperature, convert_text_case, get_time_info]
    )

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"Participant connected: {participant.identity}")

    # Start session with both room AND agent
    await session.start(room=ctx.room, agent=agent)
    print("✅ Groq Agent with 4 tools is live!")
    print("🧮 Tools: calculate, convert_temperature, convert_text_case, get_time_info")
    print("💬 Try asking:")
    print("   - 'What is 25 times 4?'")
    print("   - 'Convert 100 fahrenheit to celsius'")
    print("   - 'Make hello world uppercase'")
    print("   - 'What time is it?'")

    # Keep the script running
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
        await asyncio.sleep(1)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="campus-greeting-agent"  # Must match frontend AGENT_NAME
    ))