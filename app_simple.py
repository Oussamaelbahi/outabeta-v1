from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# File-based storage
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'users': [],
        'projects': [],
        'contact_messages': [],
        'user_sessions': []
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

# Initialize data
data = load_data()

# Create admin user if it doesn't exist
admin_exists = any(user['email'] == 'admin@gmail.com' for user in data['users'])
if not admin_exists:
    admin_user = {
        'id': 1,
        'email': 'admin@gmail.com',
        'name': 'Admin',
        'password_hash': generate_password_hash('20042004'),
        'is_admin': True,
        'is_blocked': False,
        'first_sign_in': datetime.now().isoformat(),
        'last_login': datetime.now().isoformat()
    }
    data['users'].append(admin_user)
    save_data(data)

# Helper functions
def is_logged_in():
    return 'user_id' in session

def is_admin():
    if not is_logged_in():
        return False
    user = next((u for u in data['users'] if u['id'] == session['user_id']), None)
    return user and user.get('is_admin', False)

def get_current_user():
    if not is_logged_in():
        return None
    return next((u for u in data['users'] if u['id'] == session['user_id']), None)

def update_user_activity():
    if is_logged_in():
        # Update last activity for user
        user = get_current_user()
        if user:
            user['last_login'] = datetime.now().isoformat()
            save_data(data)

def get_next_id(items):
    if not items:
        return 1
    return max(item['id'] for item in items) + 1

# Routes
@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('home'))
    return redirect(url_for('sign_in'))

@app.route('/sign')
def sign_in():
    if is_logged_in():
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    request_data = request.get_json()
    email = request_data.get('email')
    name = request_data.get('name')
    password = request_data.get('password')
    
    if any(user['email'] == email for user in data['users']):
        return jsonify({'success': False, 'message': 'Email already registered'})
    
    user = {
        'id': get_next_id(data['users']),
        'email': email,
        'name': name,
        'password_hash': generate_password_hash(password),
        'is_admin': False,
        'is_blocked': False,
        'first_sign_in': datetime.now().isoformat(),
        'last_login': datetime.now().isoformat()
    }
    data['users'].append(user)
    save_data(data)
    
    session['user_id'] = user['id']
    return jsonify({'success': True, 'redirect': url_for('home')})

@app.route('/signin', methods=['POST'])
def signin():
    request_data = request.get_json()
    email = request_data.get('email')
    password = request_data.get('password')
    
    user = next((u for u in data['users'] if u['email'] == email), None)
    
    if user and check_password_hash(user['password_hash'], password):
        if user.get('is_blocked', False):
            return jsonify({'success': False, 'message': 'Account is blocked'})
        
        session['user_id'] = user['id']
        user['last_login'] = datetime.now().isoformat()
        save_data(data)
        
        if user.get('is_admin', False):
            return jsonify({'success': True, 'redirect': url_for('superadmin')})
        else:
            return jsonify({'success': True, 'redirect': url_for('home')})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/home')
def home():
    if not is_logged_in():
        return redirect(url_for('sign_in'))
    
    user = get_current_user()
    if user.get('is_blocked', False):
        session.clear()
        flash('Your account has been blocked')
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('home.html', user=user)

@app.route('/main')
def main():
    if not is_logged_in():
        return redirect(url_for('sign_in'))
    
    user = get_current_user()
    if user.get('is_blocked', False):
        session.clear()
        flash('Your account has been blocked')
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('main.html', user=user)

@app.route('/host')
def host():
    if not is_logged_in():
        return redirect(url_for('sign_in'))
    
    user = get_current_user()
    if user.get('is_blocked', False):
        session.clear()
        flash('Your account has been blocked')
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('host.html', user=user)

@app.route('/superadmin')
def superadmin():
    if not is_logged_in() or not is_admin():
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('superadmin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('sign_in'))

# API Routes
@app.route('/api/user/profile')
def get_user_profile():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email']
        }
    })

@app.route('/api/projects')
def get_user_projects():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    user_projects = [p for p in data['projects'] if p['user_id'] == user['id']]
    
    project_list = []
    for project in user_projects:
        project_list.append({
            'id': project['id'],
            'name': project['name'],
            'created_at': project['created_at'],
            'updated_at': project['updated_at']
        })
    
    return jsonify({'success': True, 'projects': project_list})

@app.route('/api/projects', methods=['POST'])
def save_project():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    request_data = request.get_json()
    user = get_current_user()
    
    project = {
        'id': get_next_id(data['projects']),
        'name': request_data.get('name', 'Untitled Project'),
        'html_code': request_data.get('html', ''),
        'css_code': request_data.get('css', ''),
        'js_code': request_data.get('js', ''),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'user_id': user['id']
    }
    
    data['projects'].append(project)
    save_data(data)
    
    return jsonify({'success': True, 'project_id': project['id']})

@app.route('/api/projects/<int:project_id>')
def get_project(project_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    project = next((p for p in data['projects'] if p['id'] == project_id and p['user_id'] == user['id']), None)
    
    if not project:
        return jsonify({'success': False, 'message': 'Project not found'})
    
    return jsonify({
        'success': True,
        'project': {
            'id': project['id'],
            'name': project['name'],
            'html': project['html_code'],
            'css': project['css_code'],
            'js': project['js_code']
        }
    })

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    request_data = request.get_json()
    user_id = session.get('user_id') if is_logged_in() else None
    
    message = {
        'id': get_next_id(data['contact_messages']),
        'name': request_data.get('name'),
        'email': request_data.get('email'),
        'message': request_data.get('message'),
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id
    }
    
    data['contact_messages'].append(message)
    save_data(data)
    
    return jsonify({'success': True, 'message': 'Message sent successfully'})

# Admin API Routes
@app.route('/api/admin/stats')
def admin_stats():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    total_users = len(data['users'])
    active_sessions = len([u for u in data['users'] if not u.get('is_blocked', False)])
    blocked_users = len([u for u in data['users'] if u.get('is_blocked', False)])
    
    # User registrations in last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_users = len([u for u in data['users'] if datetime.fromisoformat(u['first_sign_in']) >= thirty_days_ago])
    
    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'active_sessions': active_sessions,
            'blocked_users': blocked_users,
            'new_users_30_days': new_users
        }
    })

@app.route('/api/admin/users')
def admin_users():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user_list = []
    for user in data['users']:
        user_list.append({
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'first_sign_in': user['first_sign_in'],
            'status': 'Blocked' if user.get('is_blocked', False) else 'Active',
            'is_admin': user.get('is_admin', False)
        })
    
    return jsonify({'success': True, 'users': user_list})

@app.route('/api/admin/users/<int:user_id>/toggle-block', methods=['POST'])
def admin_toggle_user_block(user_id):
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = next((u for u in data['users'] if u['id'] == user_id), None)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    if user.get('is_admin', False):
        return jsonify({'success': False, 'message': 'Cannot block admin users'})
    
    user['is_blocked'] = not user.get('is_blocked', False)
    save_data(data)
    
    return jsonify({
        'success': True,
        'is_blocked': user['is_blocked'],
        'message': f'User {"blocked" if user["is_blocked"] else "unblocked"} successfully'
    })

@app.route('/api/admin/users/<int:user_id>/projects')
def admin_user_projects(user_id):
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = next((u for u in data['users'] if u['id'] == user_id), None)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    user_projects = [p for p in data['projects'] if p['user_id'] == user_id]
    project_list = []
    
    for project in user_projects:
        project_list.append({
            'id': project['id'],
            'name': project['name'],
            'last_saved': project['updated_at'],
            'code': f"{project['html_code']}\n<style>{project['css_code']}</style>\n<script>{project['js_code']}</script>"
        })
    
    return jsonify({
        'success': True,
        'user_email': user['email'],
        'projects': project_list
    })

@app.route('/api/admin/messages')
def admin_messages():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    message_list = []
    for msg in data['contact_messages']:
        message_list.append({
            'id': msg['id'],
            'name': msg['name'],
            'email': msg['email'],
            'message': msg['message'],
            'timestamp': msg['timestamp'],
            'user_id': msg['user_id']
        })
    
    return jsonify({'success': True, 'messages': message_list})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
