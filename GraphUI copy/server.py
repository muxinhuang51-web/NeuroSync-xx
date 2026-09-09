from flask import Flask, jsonify, request, send_from_directory
from markupsafe import Markup 
from flask_cors import CORS
from Interface import save_chat_history, graph_extension, GraphCallFunction, graph_update, call_LLM, modify
import markdown
import os

print("This is test massage from wenshuo, the Server started")
os.environ["CUDA_VISIBLE_DEVICES"] = "2" 

# 指定静态文件目录为 GraphUI，URL 路径为根目录
app = Flask(__name__, static_folder='.', static_url_path='/')

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8001"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Render markdown text using Python's markdown library
@app.route('/api/render_markdown', methods=['POST'])
def render_markdown():
    if request.method == 'POST':
        data = request.json
        markdown_text = data.get('text', '')
        
        # Configure markdown extensions
        extensions = [
            'extra',           # includes tables, attr_list, etc.
            'codehilite',      # code highlighting
            'fenced_code',     # fenced code blocks
            'nl2br'            # newlines become <br>
        ]
        
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_text, extensions=extensions)
        
        # Wrap with Markup to prevent escaping
        html_content = Markup(html_content)
        
        return jsonify({
            "status": "success",
            "html": html_content
        })
    
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

# 直接使用 Flask 内置方法提供 index.html
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/api/modify', methods=['POST'])
def handle_modify():
    if request.method == 'POST':
        data = request.json
        result = modify(
            data.get('userInput'),
            data.get('newGraph')
        )
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/api/call_llm', methods=['POST'])
def handle_call_llm():
    if request.method == 'POST':
        data = request.json
        result = call_LLM(
            data.get('chatHistory', []),
            data.get('newGraph', {})
        )
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/api/graph_update', methods=['POST'])
def handle_graph_update():
    if request.method == 'POST':
        data = request.json
        result = graph_update(
            data.get('modifiedSimGraph'),
            data.get('newGraph')
        )
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/api/graph_extension', methods=['POST'])
def handle_graph_extension():
    if request.method == 'POST':
        data = request.json
        result = graph_extension(data.get('nodeId'))
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/api/graph_call', methods=['POST'])
def graph_call():
    if request.method == 'POST':
        data = request.json
        result = GraphCallFunction(
            data.get('oldGraph'),
            data.get('userPrompt')
        )
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/api/save_history', methods=['POST'])  # Add methods=['POST']
def save_history():
    if request.method == 'POST':
        data = request.json
        result = save_chat_history(
            data.get('userMessage'),
            data.get('aiResponse')
        )
        return jsonify(result)
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

if __name__ == '__main__':
    app.run(debug=False, port=5001, use_reloader=False)