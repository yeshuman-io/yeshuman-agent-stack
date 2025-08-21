"""
Utility tools for the YesHuman agent.
"""
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


class CalculatorInput(BaseModel):
    """Input for calculator tool."""
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    """Simple calculator tool for basic math operations."""
    
    name: str = "calculator"
    description: str = "Perform basic mathematical calculations. Input should be a valid mathematical expression."
    args_schema: type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str, run_manager: Optional = None) -> str:
        """Execute the calculator tool."""
        try:
            # Basic safety check - only allow basic math operations
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "Error: Only basic mathematical operations are allowed"
            
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
        """Execute the echo tool."""
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
        """Execute the weather tool."""
        # Mock weather data for demonstration
        import random
        
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
        """Execute the text analysis tool."""
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


# Basic utility tools
BASIC_TOOLS = [
    CalculatorTool(),
    EchoTool(),
    WeatherTool(),
    TextAnalysisTool(),
]

# Export available tools (including agent tools if no circular import)
try:
    from tools.agent_tools import AGENT_TOOLS
    AVAILABLE_TOOLS = BASIC_TOOLS + AGENT_TOOLS
except ImportError:
    # Fallback if circular import
    AVAILABLE_TOOLS = BASIC_TOOLS
