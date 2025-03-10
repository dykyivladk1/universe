
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session
import os
import openai
from anthropic import Anthropic  
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-default-secret-key")

CHAT_HISTORY_FILE = 'chat_histories.json'

MESSAGE_HISTORY_LIMIT = 5  

chat_histories = {}

def get_limited_message_history(messages, limit=5):
    
    if len(messages) <= limit:
        return messages.copy()
    
    return messages[-limit:]

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

openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('CLAUDE_API_KEY')

openai_client = openai.OpenAI(api_key=openai_api_key)
anthropic_client = Anthropic(api_key=anthropic_api_key)

basic_system_prompt = '''
You are AI coding Assistant. Imagine you are a GOD of programming
and you can do basically everything user request to do.
Answer shortly always, if not requested for long response.
'''

MODELS = {
    'gpt-4o': {'provider': 'openai', 'name': 'gpt-4o', 'stream': True},
    'gpt-4o-mini': {'provider': 'openai', 'name': 'gpt-4o-mini', 'stream': True},
    'o1': {'provider': 'openai', 'name': 'o1', 'stream': False},
    'o3-mini': {'provider': 'openai', 'name': 'o3-mini', 'stream': False},  
    'claude-3-5-sonnet': {'provider': 'anthropic', 'name': 'claude-3-5-sonnet-20240620', 'stream': True},
    'claude-3-7-sonnet': {'provider': 'anthropic', 'name': 'claude-3-7-sonnet-20250219', 'stream': True},
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
        return jsonify({'error': 'Invalid model selection', 'done': True})
    
    try:
        
        if model_info['provider'] == 'openai':
            if model_info.get('stream', True):
                return stream_openai_response(message, model_info['name'], user_id, chat_id, 
                                            history_limit=MESSAGE_HISTORY_LIMIT)
            else:
                
                try:
                    response_content = send_request_to_openai_no_stream(message, model_info['name'], user_id, chat_id,
                                                              history_limit=MESSAGE_HISTORY_LIMIT)
                    
                    return jsonify({
                        'response': response_content,
                        'done': True
                    })
                except Exception as e:
                    print(f"Error in non-streaming OpenAI request: {str(e)}")
                    error_msg = f"Sorry, there was an error: {str(e)}"
                    
                    if chat_histories[user_id][chat_id]['messages'][-1]['role'] != 'assistant':
                        chat_histories[user_id][chat_id]['messages'].append({
                            'role': 'assistant',
                            'content': error_msg
                        })
                        save_chat_histories()
                    return jsonify({'error': error_msg, 'done': True})
                    
        else:
            if model_info.get('stream', True):
                return stream_anthropic_response(message, model_info['name'], user_id, chat_id,
                                               history_limit=MESSAGE_HISTORY_LIMIT)
            else:
                response = send_request_to_anthropic(message, model_info['name'], user_id, chat_id,
                                                   history_limit=MESSAGE_HISTORY_LIMIT)
                return jsonify({'response': response, 'done': True})
    
    except Exception as e:
        error_msg = f"Sorry, there was an error processing your request: {str(e)}"
        print(f"General error in chat route: {str(e)}")
        
        if chat_histories[user_id][chat_id]['messages'][-1]['role'] != 'assistant':
            chat_histories[user_id][chat_id]['messages'].append({
                'role': 'assistant',
                'content': error_msg
            })
            save_chat_histories()
        return jsonify({'error': error_msg, 'done': True})

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

def stream_openai_response(content, model_name, user_id, chat_id, system_prompt=basic_system_prompt, history_limit=5):
    def generate():
        response_saved = False
        try:
            all_messages = chat_histories[user_id][chat_id]['messages']
            
            limited_messages = get_limited_message_history(all_messages, history_limit)
            
            previous_messages = []
            for msg in limited_messages:
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

def send_request_to_openai_no_stream(content, model_name, user_id, chat_id, system_prompt=basic_system_prompt, history_limit=5):
    try:
        all_messages = chat_histories[user_id][chat_id]['messages']
        
        limited_messages = get_limited_message_history(all_messages, history_limit)
        
        previous_messages = []
        for msg in limited_messages:
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        if previous_messages:
            previous_messages.pop()
        
        messages_to_send = [{"role": "system", "content": system_prompt}] + previous_messages + [{"role": "user", "content": content}]
        
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=messages_to_send,
        )
        
        response_content = response.choices[0].message.content
        
        chat_histories[user_id][chat_id]['messages'].append({
            'role': 'assistant',
            'content': response_content
        })
        
        save_chat_histories()
        
        return response_content
    
    except Exception as e:
        error_msg = f"Error in non-streaming request: {str(e)}"
        print(error_msg)
        
        chat_histories[user_id][chat_id]['messages'].append({
            'role': 'assistant',
            'content': f"Sorry, an error occurred: {str(e)}"
        })
        save_chat_histories()
        raise

def stream_anthropic_response(content, model_name, user_id, chat_id, system_prompt=basic_system_prompt, history_limit=5):
    def generate():
        response_saved = False
        full_content = ""
        
        try:
            all_messages = chat_histories[user_id][chat_id]['messages']
            
            limited_messages = get_limited_message_history(all_messages, history_limit)
            
            previous_messages = []
            for msg in limited_messages:
                role = "assistant" if msg['role'] == 'assistant' else "user"
                previous_messages.append({"role": role, "content": msg['content']})
            
            if previous_messages:
                previous_messages.pop()
            
            messages = previous_messages + [{"role": "user", "content": content}]
            
            with anthropic_client.messages.stream(
                model=model_name,
                system=system_prompt,
                messages=messages,
                max_tokens=4096,
                temperature=0.7
            ) as stream:
                for text in stream.text_stream:
                    full_content += text
                    yield f"data: {json.dumps({'chunk': text, 'done': False})}\n\n"
            
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
                
            error_message = f'Error processing stream: {str(e)}'
            print(f"API Error: {error_message}")
            yield f"data: {json.dumps({'error': error_message, 'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

def send_request_to_anthropic(content, model_name, user_id, chat_id, system_prompt=basic_system_prompt, history_limit=5):
    try:
        all_messages = chat_histories[user_id][chat_id]['messages']
        
        limited_messages = get_limited_message_history(all_messages, history_limit)
        
        previous_messages = []
        for msg in limited_messages:
            role = "assistant" if msg['role'] == 'assistant' else "user"
            previous_messages.append({"role": role, "content": msg['content']})
        
        if previous_messages:
            previous_messages.pop()
        
        messages = previous_messages + [{"role": "user", "content": content}]
        
        response = anthropic_client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )
        
        response_content = response.content[0].text
        
        chat_histories[user_id][chat_id]['messages'].append({
            'role': 'assistant',
            'content': response_content
        })
        
        save_chat_histories()
        
        return response_content
    
    except Exception as e:
        print(f"Error in Anthropic request: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
