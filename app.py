from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from pymongo import MongoClient
import random
import json
from datetime import datetime
from bson import ObjectId
import os
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Use a SECRET from env in production. Falling back to a value here only for local dev.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-please-change')

# Simple admin credentials (change for production). Prefer setting secure secrets in environment.
ADMIN_USERNAME = os.environ.get('CYBER_ADMIN_USER', 'admin')
_raw_admin_pass = os.environ.get('CYBER_ADMIN_PASS', 'admin123')
# If the provided admin password looks already hashed (werkzeug PBKDF2), accept it; otherwise hash it in-memory.
if isinstance(_raw_admin_pass, str) and _raw_admin_pass.startswith('pbkdf2:'):
    ADMIN_PASSWORD_HASH = _raw_admin_pass
else:
    ADMIN_PASSWORD_HASH = generate_password_hash(_raw_admin_pass)

# Session and security settings
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in {'1', 'true', 'yes'}

app.config.update({
    'SESSION_COOKIE_SECURE': SESSION_COOKIE_SECURE,      # rely on env so local HTTP logins continue to work
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'PERMANENT_SESSION_LIFETIME': timedelta(minutes=30)
})

# Simple in-memory login attempt tracker (per-IP). For production use a shared store like Redis.
LOGIN_ATTEMPTS = {}
LOGIN_WINDOW = 600  # seconds to track (10 minutes)
LOGIN_MAX_ATTEMPTS = 6
ALLOWED_VERSIONS = ["12"]  # Currently only Version 12 is active; expand when new sets are ready


def validate_question_form(form, current_id=None):
    """Validate admin question form input and build document for insert/update."""
    version = (form.get('version') or '').strip()
    question_text = (form.get('question') or '').strip()
    raw_opts = [form.get('opt1'), form.get('opt2'), form.get('opt3'), form.get('opt4')]
    options = [opt.strip() for opt in raw_opts if opt and opt.strip()]
    correct = (form.get('correct') or '').strip()
    topic = (form.get('topic') or '').strip()

    if not version or version not in ALLOWED_VERSIONS:
        return None, 'Please select a valid version.'
    if not question_text or len(question_text) < 10:
        return None, 'Please provide a longer question text (at least 10 characters).'
    if len(options) < 2:
        return None, 'Please provide at least two non-empty options.'
    if not correct:
        return None, 'Please select the correct option.'
    if correct not in options:
        return None, 'The correct option must match one of the provided options.'

    query = {'version': version, 'question': question_text}
    if current_id:
        query['_id'] = {'$ne': current_id}
    if collection.find_one(query):
        return None, 'A question with the same text already exists for this version.'

    doc = {
        'version': version,
        'question': question_text,
        'options': options,
        'correct': correct,
        'topic': topic
    }
    return doc, None

# MongoDB Atlas Connection
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise RuntimeError('MONGO_URI environment variable is not set. Please define it before starting the app.')

DB_NAME = os.environ.get('MONGO_DB_NAME', 'cybertest_db')
QUESTIONS_COLLECTION = os.environ.get('MONGO_QUESTIONS_COLLECTION', 'questions')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[QUESTIONS_COLLECTION]

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


# ---------- Admin auth and question add routes ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()

        # simple rate limit per IP
        ip = request.remote_addr or 'unknown'
        now = time.time()
        attempts = LOGIN_ATTEMPTS.get(ip, [])
        # purge old
        attempts = [t for t in attempts if now - t < LOGIN_WINDOW]
        if len(attempts) >= LOGIN_MAX_ATTEMPTS:
            flash('Too many login attempts. Try again later.', 'error')
            return redirect(url_for('admin_login'))

        # validate credentials using hashed password
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.permanent = True
            session['admin'] = True
            # reset attempts on success
            LOGIN_ATTEMPTS.pop(ip, None)
            flash('Logged in as admin', 'success')
            return redirect(url_for('add_question'))
        else:
            # record failed attempt
            attempts.append(now)
            LOGIN_ATTEMPTS[ip] = attempts
            flash('Invalid credentials', 'error')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out', 'info')
    return redirect(url_for('index'))


@app.route('/admin/add_question', methods=['GET', 'POST'])
def add_question():
    # require admin
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        doc, error = validate_question_form(request.form)
        if error:
            flash(error, 'error')
            return redirect(url_for('add_question'))

        doc['_id'] = str(ObjectId())
        collection.insert_one(doc)
        flash('Question added', 'success')
        return redirect(url_for('add_question'))

    return render_template('admin_add_question.html', versions=ALLOWED_VERSIONS)


@app.route('/admin/questions')
def admin_questions():
    # require admin
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    # Fetch questions (limit to 1000 for safety)
    docs = list(collection.find().sort([('version', -1)]).limit(1000))
    # render template
    return render_template('admin_questions.html', questions=docs)


@app.route('/admin/questions/<question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    question = collection.find_one({'_id': question_id})
    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('admin_questions'))

    if request.method == 'POST':
        updated_fields, error = validate_question_form(request.form, current_id=question_id)
        if error:
            flash(error, 'error')
            return redirect(url_for('edit_question', question_id=question_id))

        collection.update_one({'_id': question_id}, {'$set': updated_fields})
        flash('Question updated.', 'success')
        return redirect(url_for('admin_questions'))

    return render_template('admin_edit_question.html', question=question, versions=ALLOWED_VERSIONS)

@app.route('/start_exam', methods=['POST'])
def start_exam():
    # Get form data
    num_questions = int(request.form.get('num_questions', 125))
    versions = request.form.getlist('version')
    
    # Create a filter for selected versions
    version_filter = {'version': {'$in': versions}} if versions else {}
    
    # Get random questions for selected versions
    questions = list(collection.aggregate([
        {'$match': version_filter},
        {'$sample': {'size': num_questions}}
    ]))
    
    # Initialize session data
    session['exam_started'] = datetime.now().isoformat()
    session['total_questions'] = len(questions)
    session['answered'] = []
    
    return render_template('exam.html', questions=questions)

@app.route('/verify_answer', methods=['POST'])
def verify_answer():
    data = request.get_json()
    qid = data['question_id']
    user_answer = data['user_answer']
    
    # Get question from database
    question = collection.find_one({'_id': qid})
    
    # Check answer and update session
    if question and question['correct'] == user_answer:
        result = 'correct'
    else:
        result = 'wrong'
    
    # Track answered questions if not already answered
    if qid not in session.get('answered', []):
        session['answered'] = session.get('answered', []) + [qid]
        session.modified = True

    return jsonify({
        'result': result,
        'progress': {
            'answered': len(session.get('answered', [])),
            'total': session.get('total_questions', 0)
        }
    })

@app.route('/exam_status')
def exam_status():
    if 'exam_started' not in session:
        return jsonify({'active': False})
    
    return jsonify({
        'active': True,
        'started': session['exam_started'],
        'progress': {
            'answered': len(session.get('answered', [])),
            'total': session.get('total_questions', 0)
        }
    })

@app.route('/clear_exam')
def clear_exam():
    session.clear()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
