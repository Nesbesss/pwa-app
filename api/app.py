from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import asyncio
import aiohttp
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
GROQ_API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = "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"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def summarize_chunk(session, chunk):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-70b-Versatile",
        "messages": [
            {"role": "system", "content": "Summarize the following text concisely in English:"},
            {"role": "user", "content": chunk}
        ],
        "max_tokens": 250
    }
    retries = 5
    for attempt in range(retries):
        async with session.post(GROQ_API_ENDPOINT, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                summary = result['choices'][0]['message']['content']
                # Remove the unwanted prefix if it exists
                unwanted_prefix = "Below is a concise summary of the text in English:"
                if summary.startswith(unwanted_prefix):
                    summary = summary[len(unwanted_prefix):].strip()
                return summary
            elif response.status == 429:  # Rate limit error
                if attempt < retries - 1:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(retry_after)
                else:
                    return f"Error: {response.status} - {await response.text()}"
            else:
                return f"Error: {response.status} - {await response.text()}"

    return "Failed to summarize after several attempts."

def read_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        return "".join(page.extract_text() for page in reader.pages)

def chunk_text(text, chunk_size=8000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

async def process_pdf(file_path):
    text = read_pdf(file_path)
    chunks = chunk_text(text)
    summaries = []

    async with aiohttp.ClientSession() as session:
        tasks = [summarize_chunk(session, chunk) for chunk in chunks]
        for task in asyncio.as_completed(tasks):
            summary = await task
            summaries.append(summary)

    return "\n\n".join(summaries)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        summary = asyncio.run(process_pdf(file_path))
        os.remove(file_path)  # Remove the file after processing
        return jsonify({'summary': summary})
    return jsonify({'error': 'Invalid file type'})

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js')

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
