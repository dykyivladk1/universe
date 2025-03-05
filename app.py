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

CHAT_HISTORY_FILE = 'chat_histories.json'

chat_histories = {}

def load_chat_histories():
    global chat_histories
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r') as f:
                chat_histories = json.load(f)
            print(f"Chat histories loaded from {CHAT_HISTORY_FILE}")
    except Exception as e:
        print(f"Error loading chat histories: {str(e)}")
        chat_histories = {}

def save_chat_histories():
    try:
        if not isinstance(chat_histories, dict):
            print("Warning: chat_histories is not a dictionary. Initializing empty dictionary.")
            chat_histories = {}
            
        directory = os.path.dirname(CHAT_HISTORY_FILE)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        serializable_histories = json.dumps(chat_histories, default=str, indent=2)
        
        with open(CHAT_HISTORY_FILE, 'w') as f:
            f.write(serializable_histories)
            
        print(f"Chat histories saved to {CHAT_HISTORY_FILE}")
    except Exception as e:
        print(f"Error saving chat histories: {str(e)}")
        import traceback
        traceback.print_exc()

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

MODELS = {
    'gpt-4o': {'provider': 'openai', 'name': 'gpt-4o', 'stream': True},
    'gpt-4o-mini': {'provider': 'openai', 'name': 'gpt-4o-mini', 'stream': True},
    'o3-mini': {'provider': 'openai', 'name': 'o3-mini', 'stream': False},
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
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
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
        save_chat_histories()
    
    user_chats = chat_histories[user_id]
    
    return render_template('index.html', models=MODELS, chats=user_chats)

@app.route('/chat/new', methods=['POST'])
def new_chat():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
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
    
    save_chat_histories()
    
    return jsonify({
        'status': 'success',
        'chat_id': chat_id
    })

@app.route('/chat/rename/<chat_id>', methods=['POST'])
def rename_chat(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No session found'}), 401
    
    user_id = session['user_id']
    data = request.json
    new_title = data.get('title', 'Untitled Chat')
    
    if user_id not in chat_histories or chat_id not in chat_histories[user_id]:
        return jsonify({'error': 'Chat not found'}), 404
    
    chat_histories[user_id][chat_id]['title'] = new_title
    
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
    
    save_chat_histories()
    
    return jsonify({
        'status': 'success'
    })

@app.route('/chat', methods=['POST', 'GET'])
def chat():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    
    if request.method == 'GET':
        message = request.args.get('message', '')
        model_key = request.args.get('model', 'gpt-4o')
        chat_id = request.args.get('chat_id', 'default')
    else:
        data = request.json
        message = data.get('message', '')
        model_key = data.get('model', 'gpt-4o')
        chat_id = data.get('chat_id', 'default')
    
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
    
    chat_histories[user_id][chat_id]['messages'].append({
        'role': 'user',
        'content': message
    })
    
    if chat_histories[user_id][chat_id]['title'] == 'New Chat' and len(message) > 0:
        title = message[:30] + ('...' if len(message) > 30 else '')
        chat_histories[user_id][chat_id]['title'] = title
    
    save_chat_histories()
    
    model_info = MODELS.get(model_key)
    
    if not model_info:
        return jsonify({'error': 'Invalid model selection'})
    
    try:
        if model_info['provider'] == 'openai':
            if model_info.get('stream', True):
                return stream_openai_response(message, model_info['name'], user_id, chat_id)
            else:
                response = send_request_to_openai_no_stream(message, model_info['name'], user_id, chat_id)
                return jsonify({'response': response, 'done': True})
        else:
            response = send_request_to_anthropic(message, model_info['name'], user_id, chat_id)
            
            chat_histories[user_id][chat_id]['messages'].append({
                'role': 'assistant',
                'content': response
            })
            
            save_chat_histories()
            
            return jsonify({'response': response, 'done': True})
    
    except Exception as e:
        return jsonify({'error': str(e), 'done': True})

def stream_openai_response(content, model_name, user_id, chat_id, system_prompt=system_prompt):
    def generate():
        response_saved = False
        try:
            previous_messages = []
            for msg in chat_histories[user_id][chat_id]['messages']:
                role = "assistant" if msg['role'] == 'assistant' else "user"
                previous_messages.append({"role": role, "content": msg['content']})
            
            if previous_messages:
                previous_messages.pop()
            
            messages_to_send = [{"role": "system", "content": system_prompt}] + previous_messages + [{"role": "user", "content": content}]
            
            api_params = {
                "model": model_name,
                "messages": messages_to_send,
                "stream": True
            }
            
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
                
                chat_histories[user_id][chat_id]['messages'].append({
                    'role': 'assistant',
                    'content': full_content
                })
                
                save_chat_histories()
                response_saved = True
                
                yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"
            except Exception as e:
                if not response_saved and full_content:
                    chat_histories[user_id][chat_id]['messages'].append({
                        'role': 'assistant',
                        'content': full_content
                    })
                    save_chat_histories()
                
                yield f"data: {json.dumps({'error': f'Error processing stream: {str(e)}', 'done': True})}\n\n"
                
        except Exception as e:
            error_message = f'Error creating completion: {str(e)}'
            print(f"API Error: {error_message}")
            yield f"data: {json.dumps({'error': error_message, 'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

def send_request_to_openai_no_stream(content, model_name, user_id, chat_id, system_prompt=system_prompt):
    try:
        previous_messages = []
        for msg in chat_histories[user_id][chat_id]['messages']:
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        if previous_messages:
            previous_messages.pop()
        
        messages_to_send = [{"role": "system", "content": system_prompt}] + previous_messages + [{"role": "user", "content": content}]
        
        api_params = {
            "model": model_name,
            "messages": messages_to_send,
            "stream": False  
        }
        
        if model_name != 'o3-mini':
            api_params["temperature"] = 0.7
            
        response = openai_client.chat.completions.create(**api_params)
        
        response_content = response.choices[0].message.content
        
        chat_histories[user_id][chat_id]['messages'].append({
            'role': 'assistant',
            'content': response_content
        })
        
        save_chat_histories()
        
        return response_content
    
    except Exception as e:
        print(f"Error in non-streaming request: {str(e)}")
        raise

def send_request_to_anthropic(content, model_name, user_id=None, chat_id=None, system_prompt=system_prompt):
    messages_to_send = [{"role": "user", "content": content}]
    
    if user_id and chat_id and user_id in chat_histories and chat_id in chat_histories[user_id]:
        previous_messages = []
        for msg in chat_histories[user_id][chat_id]['messages'][:-1]: 
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        messages_to_send = previous_messages + messages_to_send
    
    if len(messages_to_send) > 10:
        messages_to_send = messages_to_send[-10:]
    
    message = anthropic_client.messages.create(
        max_tokens=4000,
        messages=messages_to_send,
        model=model_name,
        system=system_prompt
    )
    return message.content[0].text

if __name__ == '__main__':
    app.run(debug=True, port = 3000)
