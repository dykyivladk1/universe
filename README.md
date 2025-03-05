# Universe - Multi-Model Chat Interface

![Universe](https://img.shields.io/badge/Universe-Chat_Interface-blue)
![Flask](https://img.shields.io/badge/Flask-Web_Framework-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT_Models-orange)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude_Models-purple)

Universe is a versatile web application that provides a unified interface to interact with multiple AI language models from OpenAI and Anthropic, including GPT-4o, Claude 3.7 Sonnet, and more. This application allows users to have persistent conversations with different AI models and seamlessly switch between them.

## Features

- **Multi-model support**: Access to various AI models from OpenAI and Anthropic
  - OpenAI models: GPT-4o, GPT-4o mini, GPT-4 Turbo, GPT-3.5 Turbo, O3-mini
  - Anthropic models: Claude 3 Opus, Claude 3 Sonnet, Claude 3.5 Sonnet, Claude 3.7 Sonnet, Claude 3 Haiku
- **Persistent chat history**: All conversations are saved to a JSON file and persist across server restarts
- **Multiple chat sessions**: Create and manage multiple conversations
- **Session management**: Each user gets their own set of conversations
- **Streaming responses**: Real-time streaming for supported models
- **Clean, simple interface**: Easy-to-use chat interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/universe.git
cd universe
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install flask openai anthropic python-dotenv
```

4. Create a `.env` file in the project root with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_anthropic_api_key
FLASK_SECRET_KEY=your_secret_key_for_flask_sessions
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:3000
```

3. Start chatting with any of the available AI models by selecting them from the dropdown menu.

## File Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates for the web interface
- `chat_histories.json`: Persistent storage for all chat histories

## Key Features Explained

### Chat History Persistence

All chat histories are automatically saved to a JSON file (`chat_histories.json`) after every interaction. This ensures that conversations persist even if the server is restarted. The chat histories are organized by user ID and chat ID.

### Model Selection

Users can select different AI models from the dropdown menu. Each model has its own configuration, including provider (OpenAI or Anthropic) and streaming capability.

### Multiple Chat Sessions

Users can create multiple chat sessions and switch between them. Each chat session has its own history and can use different AI models.

## Customization

### System Prompt

You can customize the system prompt in the `app.py` file. The system prompt defines the AI assistant's behavior and is sent with every request to the AI models.

```python
system_prompt = '''
Remember you are LORA.
Your task is to answer user requests. Usually in short way,
if not requested.
'''
```

### Adding New Models

To add new models, update the `MODELS` dictionary in the `app.py` file:

```python
MODELS = {
    'new-model': {
        'provider': 'openai',  # or 'anthropic'
        'name': 'actual-model-name', 
        'stream': True  # or False
    },
    # ...
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [OpenAI](https://openai.com/) for providing the GPT models
- [Anthropic](https://www.anthropic.com/) for providing the Claude models
- [Flask](https://flask.palletsprojects.com/) for the web framework
