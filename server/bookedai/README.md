# BookedAI

BookedAI is a travel assistant agent that uses language models to provide helpful responses about travel destinations, bookings, and recommendations.

## Features

- Natural language chat interface
- Integration with modern LLMs through a unified interface
- Tool-calling capabilities for tasks like calculations
- Experimental features that can be toggled on/off
- Streaming responses for a responsive UX

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bookedai.git
cd bookedai
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```

4. Set up your database:
```bash
python manage.py migrate
```

5. Run the development server:
```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/chat/

## Project Structure

- `agent/`: Core agent implementation
  - `agent.py`: Main BookedAI class
  - `llm_interface.py`: Unified interface for LLM backends
  - `react_agent.py`: Basic reAct agent for tool calling
- `chat/`: Django app for the chat interface
- `exploratory/`: Experimental features and prototypes
  - `react_agent.py`: Advanced reAct agent with tool calling
- `examples/`: Example usage scripts

## Configuration

BookedAI can be configured using the `AgentConfig` class. Key settings include:

- `model_name`: The LLM model to use (default: "gpt-3.5-turbo")
- `use_react_agent`: Whether to use tool calling capabilities (default: true)
- `experimental_mode`: Whether to use experimental features (default: false)

## Development

### Adding a new tool

1. Update the `tools` dictionary in `exploratory/react_agent.py`
2. Add detection logic in the `_needs_tool_calling` method in `agent/agent.py`
3. Implement the tool processing logic

### Adding a new LLM backend

1. Create a new class that inherits from `BaseLLM` in `agent/llm_interface.py`
2. Implement the required `generate_response` method
3. Update the `create_llm` factory function to return your new LLM class

## License

This project is licensed under the MIT License - see the LICENSE file for details.
