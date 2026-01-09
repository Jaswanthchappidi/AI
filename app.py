import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
  
app = Flask(__name__)
# IMPORTANT: This allows your React app to talk to Flask
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'minibot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/api/chat/', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        user_id = data.get('user_id', 'anonymous')

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Mini Bot, a helpful AI."},
                {"role": "user", "content": user_message}
            ],
        )
        bot_response = completion.choices[0].message.content

        new_chat = ChatHistory(user_id=user_id, message=user_message, response=bot_response)
        db.session.add(new_chat)
        db.session.commit()

        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"response": f"Mini Bot Error: {str(e)}"}), 500

# NEW ROUTE: Fetch specific chat content when clicked in sidebar
@app.route('/api/chat/<int:chat_id>', methods=['GET'])
def get_single_chat(chat_id):
    try:
        chat = ChatHistory.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        # Return as a list of messages for the frontend ChatWindow
        return jsonify([
            {"sender": "user", "text": chat.message},
            {"sender": "bot", "text": chat.response}
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<user_id>', methods=['GET'])
def get_user_history(user_id):
    try:
        history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).all()
        formatted = [{"id": c.id, "title": c.message[:30]+"...", "user_message": c.message, "bot_response": c.response} for c in history]
        return jsonify(formatted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8000, debug=True)