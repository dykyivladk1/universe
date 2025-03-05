from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session
import os
import openai
import anthropic
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-default-secret-key")

# File to store chat histories
CHAT_HISTORY_FILE = 'chat_histories.json'

# Initialize chat_histories
chat_histories = {}

# Load chat histories from file if it exists
def load_chat_histories():
    global chat_histories
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r') as f:
                chat_histories = json.load(f)
            print(f"Chat histories loaded from {CHAT_HISTORY_FILE}")
    except Exception as e:
        print(f"Error loading chat histories: {str(e)}")
        # Initialize empty dict if loading fails
        chat_histories = {}

# Save chat histories to file
def save_chat_histories():
    try:
        # Ensure we have a valid dictionary to serialize
        if not isinstance(chat_histories, dict):
            print("Warning: chat_histories is not a dictionary. Initializing empty dictionary.")
            chat_histories = {}
            
        # Create directory if it doesn't exist
        directory = os.path.dirname(CHAT_HISTORY_FILE)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # Serialize datetime objects if needed
        serializable_histories = json.dumps(chat_histories, default=str, indent=2)
        
        # Write to file
        with open(CHAT_HISTORY_FILE, 'w') as f:
            f.write(serializable_histories)
            
        print(f"Chat histories saved to {CHAT_HISTORY_FILE}")
    except Exception as e:
        print(f"Error saving chat histories: {str(e)}")
        # Print more detailed error information for debugging
        import traceback
        traceback.print_exc()

# Load chat histories at startup
load_chat_histories()

openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = anthropic.Anthropic(
    api_key = os.getenv('CLAUDE_API_KEY')
)


system_prompt = '''
Remember you are LORA.
Your task is to answer user requests. Usually in short way,
if not requested.
'''

# Available models
MODELS = {
    'gpt-4o': {'provider': 'openai', 'name': 'gpt-4o', 'stream': True},
    'gpt-4o-mini': {'provider': 'openai', 'name': 'gpt-4o-mini', 'stream': True},
    'o3-mini': {'provider': 'openai', 'name': 'o3-mini', 'stream': False},  # Set to non-streaming
    'gpt-4-turbo': {'provider': 'openai', 'name': 'gpt-4-turbo', 'stream': True},
    'gpt-3.5-turbo': {'provider': 'openai', 'name': 'gpt-3.5-turbo', 'stream': True},
    'claude-3-opus': {'provider': 'anthropic', 'name': 'claude-3-opus-20240229', 'stream': False},
    'claude-3-sonnet': {'provider': 'anthropic', 'name': 'claude-3-sonnet-20240229', 'stream': False},
    'claude-3-5-sonnet': {'provider': 'anthropic', 'name': 'claude-3-5-sonnet-20240620', 'stream': False},
    'claude-3-7-sonnet': {'provider': 'anthropic', 'name': 'claude-3-7-sonnet-20250219', 'stream': False},
    'claude-3-haiku': {'provider': 'anthropic', 'name': 'claude-3-haiku-20240307', 'stream': False}
}

@app.route('/')
def index():
    # Generate a unique session ID if not already present
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    # Initialize user's chat history if not exists
    if user_id not in chat_histories:
        chat_histories[user_id] = {
            'default': {
                'title': 'New Chat',
                'messages': [
                    {
                        'role': 'assistant',
                        'content': '👋 Hello! I\'m your AI assistant. How can I help you today?'
                    }
                ],
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        # Save the new user's chat history
        save_chat_histories()
    
    # Get all chats for the user
    user_chats = chat_histories[user_id]
    
    return render_template('index.html', models=MODELS, chats=user_chats)

@app.route('/chat/new', methods=['POST'])
def new_chat():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    # Create a new chat
    chat_id = str(uuid.uuid4())
    
    if user_id not in chat_histories:
        chat_histories[user_id] = {}
    
    chat_histories[user_id][chat_id] = {
        'title': 'New Chat',
        'messages': [
            {
                'role': 'assistant',
                'content': '👋 Hello! I\'m your AI assistant. How can I help you today?'
            }
        ],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save the updated chat histories
    save_chat_histories()
    
    return jsonify({
        'status': 'success',
        'chat_id': chat_id,
        'chat': chat_histories[user_id][chat_id]
    })

@app.route('/chat/history/<chat_id>', methods=['GET'])
def get_chat_history(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No session found'}), 401
    
    user_id = session['user_id']
    
    if user_id not in chat_histories or chat_id not in chat_histories[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    return jsonify({
        'status': 'success',
        'chat': chat_histories[user_id][chat_id]
    })

@app.route('/chat/update/<chat_id>', methods=['POST'])
def update_chat_title(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No session found'}), 401
    
    user_id = session['user_id']
    data = request.json
    new_title = data.get('title', 'Untitled Chat')
    
    if user_id not in chat_histories or chat_id not in chat_histories[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    chat_histories[user_id][chat_id]['title'] = new_title
    
    # Save the updated chat histories
    save_chat_histories()
    
    return jsonify({
        'status': 'success',
        'chat_id': chat_id
    })

@app.route('/chat/rename/<chat_id>', methods=['POST'])
def rename_chat(chat_id):
    """New endpoint specifically for renaming chats to match frontend expectations"""
    if 'user_id' not in session:
        return jsonify({'error': 'No session found'}), 401
    
    user_id = session['user_id']
    data = request.json
    new_title = data.get('title', 'Untitled Chat')
    
    if user_id not in chat_histories or chat_id not in chat_histories[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    chat_histories[user_id][chat_id]['title'] = new_title
    
    # Save the updated chat histories
    save_chat_histories()
    
    return jsonify({
        'status': 'success',
        'chat_id': chat_id,
        'title': new_title
    })

@app.route('/chat/delete/<chat_id>', methods=['POST'])
def delete_chat(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No session found'}), 401
    
    user_id = session['user_id']
    
    if user_id not in chat_histories or chat_id not in chat_histories[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    del chat_histories[user_id][chat_id]
    
    # Save the updated chat histories
    save_chat_histories()
    
    return jsonify({
        'status': 'success'
    })

@app.route('/chat', methods=['POST', 'GET'])
def chat():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    # Handle both GET (for streaming) and POST requests
    if request.method == 'GET':
        message = request.args.get('message', '')
        model_key = request.args.get('model', 'gpt-4o')
        chat_id = request.args.get('chat_id', 'default')
    else:
        data = request.json
        message = data.get('message', '')
        model_key = data.get('model', 'gpt-4o')
        chat_id = data.get('chat_id', 'default')
    
    # Ensure chat exists
    if user_id not in chat_histories:
        chat_histories[user_id] = {}
    
    if chat_id not in chat_histories[user_id]:
        chat_histories[user_id][chat_id] = {
            'title': 'New Chat',
            'messages': [
                {
                    'role': 'assistant',
                    'content': '👋 Hello! I\'m your AI assistant. How can I help you today?'
                }
            ],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # Add user message to history
    chat_histories[user_id][chat_id]['messages'].append({
        'role': 'user',
        'content': message
    })
    
    # Update chat title from first user message if it's still "New Chat"
    if chat_histories[user_id][chat_id]['title'] == 'New Chat' and len(message) > 0:
        # Use the first 30 chars of message as title
        title = message[:30] + ('...' if len(message) > 30 else '')
        chat_histories[user_id][chat_id]['title'] = title
    
    # Save chat histories after adding user message
    save_chat_histories()
    
    # Get model information
    model_info = MODELS.get(model_key)
    
    if not model_info:
        return jsonify({'error': 'Invalid model selection'})
    
    try:
        if model_info['provider'] == 'openai':
            # Check if streaming is enabled for this model
            if model_info.get('stream', True):
                # Use streaming response
                return stream_openai_response(message, model_info['name'], user_id, chat_id)
            else:
                # Use non-streaming response
                response = send_request_to_openai_no_stream(message, model_info['name'], user_id, chat_id)
                return jsonify({'response': response, 'done': True})
        else:
            # For Anthropic, we're not using streaming
            response = send_request_to_anthropic(message, model_info['name'], user_id, chat_id)
            
            # Add assistant response to history
            chat_histories[user_id][chat_id]['messages'].append({
                'role': 'assistant',
                'content': response
            })
            
            # Save chat histories after adding assistant response
            save_chat_histories()
            
            return jsonify({'response': response, 'done': True})
    
    except Exception as e:
        return jsonify({'error': str(e), 'done': True})

def stream_openai_response(content, model_name, user_id, chat_id, system_prompt=system_prompt):
    def generate():
        # Flag to track if we've saved the chat history
        response_saved = False
        try:
            # Get previous messages for context
            previous_messages = []
            for msg in chat_histories[user_id][chat_id]['messages']:
                role = "assistant" if msg['role'] == 'assistant' else "user"
                previous_messages.append({"role": role, "content": msg['content']})
            
            # Remove the last message (current user query) as we'll add it explicitly
            if previous_messages:
                previous_messages.pop()
            
            # Add the system message at the beginning and the current user query
            messages_to_send = [{"role": "system", "content": system_prompt}] + previous_messages + [{"role": "user", "content": content}]
            
            # Create API parameters based on model
            api_params = {
                "model": model_name,
                "messages": messages_to_send,
                "stream": True
            }
            
            # Don't add temperature parameter for o3-mini
            if model_name != 'o3-mini':
                api_params["temperature"] = 0.7
            
            response = openai_client.chat.completions.create(**api_params)
            
            full_content = ""
            
            try:
                for chunk in response:
                    if chunk.choices and hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                        content_chunk = chunk.choices[0].delta.content
                        if content_chunk:
                            full_content += content_chunk
                            yield f"data: {json.dumps({'chunk': content_chunk, 'done': False})}\n\n"
                
                # Add assistant response to history
                chat_histories[user_id][chat_id]['messages'].append({
                    'role': 'assistant',
                    'content': full_content
                })
                
                # Save chat histories after adding assistant response
                save_chat_histories()
                response_saved = True
                
                # Signal completion
                yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"
            except Exception as e:
                # If we haven't saved the response yet and have accumulated some content
                if not response_saved and full_content:
                    # Add whatever we have to the history
                    chat_histories[user_id][chat_id]['messages'].append({
                        'role': 'assistant',
                        'content': full_content
                    })
                    # Try to save
                    save_chat_histories()
                
                yield f"data: {json.dumps({'error': f'Error processing stream: {str(e)}', 'done': True})}\n\n"
                
        except Exception as e:
            error_message = f'Error creating completion: {str(e)}'
            print(f"API Error: {error_message}")
            yield f"data: {json.dumps({'error': error_message, 'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

def send_request_to_openai_no_stream(content, model_name, user_id, chat_id, system_prompt=system_prompt):
    """Send request to OpenAI without streaming for models that don't support it"""
    try:
        # Get previous messages for context
        previous_messages = []
        for msg in chat_histories[user_id][chat_id]['messages']:
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        # Remove the last message (current user query) as we'll add it explicitly
        if previous_messages:
            previous_messages.pop()
        
        # Add the system message at the beginning and the current user query
        messages_to_send = [{"role": "system", "content": system_prompt}] + previous_messages + [{"role": "user", "content": content}]
        
        # Create API parameters based on model
        api_params = {
            "model": model_name,
            "messages": messages_to_send,
            "stream": False  # Explicitly set to False for non-streaming
        }
        
        # Don't add temperature parameter for o3-mini
        if model_name != 'o3-mini':
            api_params["temperature"] = 0.7
            
        response = openai_client.chat.completions.create(**api_params)
        
        # Extract the response content
        response_content = response.choices[0].message.content
        
        # Add assistant response to history
        chat_histories[user_id][chat_id]['messages'].append({
            'role': 'assistant',
            'content': response_content
        })
        
        # Save chat histories after adding assistant response
        save_chat_histories()
        
        return response_content
    
    except Exception as e:
        print(f"Error in non-streaming request: {str(e)}")
        raise

def send_request_to_anthropic(content, model_name, user_id=None, chat_id=None, system_prompt=system_prompt):
    # For Anthropic, system prompt is handled differently
    # Get previous messages for context if user_id and chat_id are provided
    messages_to_send = [{"role": "user", "content": content}]
    
    if user_id and chat_id and user_id in chat_histories and chat_id in chat_histories[user_id]:
        previous_messages = []
        for msg in chat_histories[user_id][chat_id]['messages'][:-1]:  # Exclude the last message (current query)
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        # Add previous messages for context
        messages_to_send = previous_messages + messages_to_send
    
    # For simplicity, we'll limit to just the last 10 messages
    if len(messages_to_send) > 10:
        messages_to_send = messages_to_send[-10:]
    
    # Anthropic uses a system parameter instead of a system message in the messages array
    message = anthropic_client.messages.create(
        max_tokens=4000,
        messages=messages_to_send,
        model=model_name,
        system=system_prompt
    )
    return message.content[0].text

if __name__ == '__main__':
    app.run(debug=True, port = 3000)