"""
Utility tools for the Yes Human agent.
"""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional
import asyncio


class CalculatorInput(BaseModel):
    """Input for calculator tool."""
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    """Simple calculator tool for basic math operations."""
    
    name: str = "calculator"
    description: str = "Perform basic mathematical calculations. Input should be a valid mathematical expression."
    args_schema: type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str, run_manager: Optional = None) -> str:
        """Execute the calculator tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(expression, run_manager))
    
    async def _arun(self, expression: str, run_manager: Optional = None) -> str:
        """Execute the calculator tool asynchronously."""
        try:
            # Basic safety check - only allow basic math operations
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "Error: Only basic mathematical operations are allowed"
            
            # Use asyncio.sleep(0) to yield control in case of complex calculations
            await asyncio.sleep(0)
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"


class EchoInput(BaseModel):
    """Input for echo tool."""
    message: str = Field(description="Message to echo back")


class EchoTool(BaseTool):
    """Simple echo tool for testing."""
    
    name: str = "echo"
    description: str = "Echo back any message. Useful for testing and simple responses."
    args_schema: type[BaseModel] = EchoInput
    
    def _run(self, message: str, run_manager: Optional = None) -> str:
        """Execute the echo tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(message, run_manager))
    
    async def _arun(self, message: str, run_manager: Optional = None) -> str:
        """Execute the echo tool asynchronously."""
        await asyncio.sleep(0)  # Yield control
        return f"Echo: {message}"


class WeatherInput(BaseModel):
    """Input for weather tool."""
    location: str = Field(description="City name or location to get weather for")


class WeatherTool(BaseTool):
    """Mock weather tool for demonstration."""
    
    name: str = "weather"
    description: str = "Get current weather information for a location. Returns mock weather data for demonstration."
    args_schema: type[BaseModel] = WeatherInput
    
    def _run(self, location: str, run_manager: Optional = None) -> str:
        """Execute the weather tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(location, run_manager))
    
    async def _arun(self, location: str, run_manager: Optional = None) -> str:
        """Execute the weather tool asynchronously."""
        # Mock weather data for demonstration
        import random
        
        # Simulate API call delay
        await asyncio.sleep(0.1)
        
        weather_conditions = ["sunny", "cloudy", "rainy", "partly cloudy", "windy"]
        condition = random.choice(weather_conditions)
        temperature = random.randint(15, 35)  # Celsius
        
        return f"Weather in {location}: {condition}, {temperature}°C"


class TextAnalysisInput(BaseModel):
    """Input for text analysis tool."""
    text: str = Field(description="Text to analyze")
    analysis_type: str = Field(default="summary", description="Type of analysis: 'summary', 'sentiment', 'wordcount'")


class TextAnalysisTool(BaseTool):
    """Text analysis tool for various text operations."""
    
    name: str = "text_analysis"
    description: str = "Analyze text for various metrics like word count, sentiment, or generate summaries."
    args_schema: type[BaseModel] = TextAnalysisInput
    
    def _run(self, text: str, analysis_type: str = "summary", run_manager: Optional = None) -> str:
        """Execute the text analysis tool synchronously (wrapper for async version)."""
        import asyncio
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't be called
            return "Error: Synchronous tool execution not supported in async context"
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._arun(text, analysis_type, run_manager))
    
    async def _arun(self, text: str, analysis_type: str = "summary", run_manager: Optional = None) -> str:
        """Execute the text analysis tool asynchronously."""
        # Simulate processing time for analysis
        await asyncio.sleep(0.05)
        
        if analysis_type == "wordcount":
            word_count = len(text.split())
            char_count = len(text)
            return f"Word count: {word_count}, Character count: {char_count}"
        
        elif analysis_type == "sentiment":
            # Simple mock sentiment analysis
            positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic"]
            negative_words = ["bad", "terrible", "awful", "horrible", "disappointing"]
            
            text_lower = text.lower()
            positive_score = sum(1 for word in positive_words if word in text_lower)
            negative_score = sum(1 for word in negative_words if word in text_lower)
            
            if positive_score > negative_score:
                sentiment = "Positive"
            elif negative_score > positive_score:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
                
            return f"Sentiment: {sentiment} (Positive: {positive_score}, Negative: {negative_score})"
        
        elif analysis_type == "summary":
            # Simple mock summary
            sentences = text.split('.')
            first_sentence = sentences[0].strip() if sentences else text[:100]
            return f"Summary: {first_sentence}{'...' if len(text) > 100 else ''}"
        
        else:
            return f"Unknown analysis type: {analysis_type}. Available types: wordcount, sentiment, summary"


# Basic utility tools for ReAct agent (focused, practical tools only)
BASIC_TOOLS = [
    CalculatorTool(),
    WeatherTool(),
    TextAnalysisTool(),
]

# All tools including echo (for MCP/testing)
ALL_UTILITY_TOOLS = [
    CalculatorTool(),
    EchoTool(),
    WeatherTool(),
    TextAnalysisTool(),
]

# Import all application tools for the ReAct agent
try:
    from apps.applications.tools import APPLICATION_TOOLS
    from apps.evaluations.tools import EVALUATION_TOOLS
    from apps.opportunities.tools import OPPORTUNITY_TOOLS
    from apps.profiles.tools import PROFILE_TOOLS

    # Combine all tools for the agent
    ALL_APP_TOOLS = APPLICATION_TOOLS + EVALUATION_TOOLS + OPPORTUNITY_TOOLS + PROFILE_TOOLS

    print(f"✅ Loaded {len(ALL_APP_TOOLS)} application tools", file=__import__('sys').stderr)
except ImportError as e:
    print(f"⚠️ Application tools not loaded due to import error: {e}", file=__import__('sys').stderr)
    ALL_APP_TOOLS = []

# Export available tools for ReAct agent (user conversation tools only)
# Note: agent_chat and agent_capabilities are excluded as they're for MCP/A2A use
# Voice generation is now handled directly in the agent_node
AVAILABLE_TOOLS = BASIC_TOOLS + ALL_APP_TOOLS

# MCP/A2A tools - include agent tools for full functionality
try:
    from tools.agent_tools import AGENT_TOOLS
    MCP_TOOLS = ALL_UTILITY_TOOLS + AGENT_TOOLS + ALL_APP_TOOLS
    print(f"✅ Loaded {len(AGENT_TOOLS)} agent tools", file=__import__('sys').stderr)
except ImportError as e:
    # Fallback if circular import occurs
    print(f"⚠️ Agent tools not loaded due to import error: {e}", file=__import__('sys').stderr)
    MCP_TOOLS = ALL_UTILITY_TOOLS + ALL_APP_TOOLS
