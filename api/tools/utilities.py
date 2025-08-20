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


# Export available tools
AVAILABLE_TOOLS = [
    CalculatorTool(),
    EchoTool(),
]
