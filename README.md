# Universe - Multi-Model Chat Interface

Universe is a versatile web application that provides a unified interface to interact with multiple AI language models from OpenAI and Anthropic, including GPT-4o, Claude 3.7 Sonnet, and more. This application allows users to have persistent conversations with different AI models and seamlessly switch between them.

## Features
* **Multi-model support**: Access to various AI models from OpenAI and Anthropic
   * OpenAI models: GPT-4o, GPT-4o mini, O1, O3-mini
   * Anthropic models: Claude 3.5 Sonnet, Claude 3.7 Sonnet
* **Persistent chat history**: All conversations are saved to a JSON file and persist across server restarts
* **Multiple chat sessions**: Create and manage multiple conversations
* **Session management**: Each user gets their own set of conversations
* **Streaming responses**: Real-time streaming for supported models
* **Clean, simple interface**: Elegant and responsive UI with dark/light mode
* **Keyboard shortcuts**: Improve productivity with keyboard navigation

## Installation
1. Clone the repository:
```
git clone https://github.com/yourusername/universe.git
cd universe
```

2. Create a virtual environment and activate it:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```
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
```
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:3000
```

3. Start chatting with any of the available AI models by selecting them from the dropdown menu.

## File Structure
* `app.py`: Main Flask application
* `templates/index.html`: Main HTML template for the web interface
* `chat_histories.json`: Persistent storage for all chat histories

## Key Features Explained

### Chat History Persistence
All chat histories are automatically saved to a JSON file (`chat_histories.json`) after every interaction. This ensures that conversations persist even if the server is restarted. The chat histories are organized by user ID and chat ID.

### Message History Limit
By default, the application only sends the last 5 messages from the conversation history to the AI model. This helps control token usage and response times. If you want to change this limit, modify the `MESSAGE_HISTORY_LIMIT` variable in `app.py`:

```python
# Change this value to increase or decrease the number of messages sent to the AI model
MESSAGE_HISTORY_LIMIT = 5  
```

Increasing this value will provide more context to the AI model but may increase API costs and response times. Decreasing it will reduce context but may save on costs.

### Model Selection
Users can select different AI models from the dropdown menu. Each model has its own configuration, including provider (OpenAI or Anthropic) and streaming capability.

### Multiple Chat Sessions
Users can create multiple chat sessions and switch between them. Each chat session has its own history and can use different AI models.

### Keyboard Shortcuts
- `/` (Forward slash): Focus the input field
- `Alt+Enter`: Focus the input field
- `Ctrl+N` or `Cmd+N`: Create a new chat
- `Shift+Cmd+S`: Toggle sidebar
- `Ctrl+D` or `Cmd+D`: Toggle dark/light mode
- Arrow keys for message navigation

## Customization

### System Prompt
You can customize the system prompt in the `app.py` file. The system prompt defines the AI assistant's behavior and is sent with every request to the AI models.

```python
basic_system_prompt = '''
You are AI coding Assistant. Imagine you are a GOD of programming
and you can do basically everything user request to do.
Answer shortly always, if not requested for long response.
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
* OpenAI for providing the GPT models
* Anthropic for providing the Claude models
* Flask for the web framework
