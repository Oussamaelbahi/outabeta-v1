from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///outa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(200), nullable=True)  # URL to profile image
    hosting_limit = db.Column(db.Integer, default=5)  # Maximum number of hosted pages
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    first_sign_in = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='user', lazy=True)
    contact_messages = db.relationship('ContactMessage', backref='user', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    html_code = db.Column(db.Text, nullable=False)
    css_code = db.Column(db.Text, nullable=False)
    js_code = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Conversion tracking fields
    conversion_button_name = db.Column(db.String(100), nullable=True)
    conversion_tracking_enabled = db.Column(db.Boolean, default=False)
    # Product tracking fields
    product_name = db.Column(db.String(255), nullable=True)
    product_price = db.Column(db.String(100), nullable=True)
    # Customer tracking fields
    customer_name_placeholder = db.Column(db.String(255), nullable=True)
    customer_phone_placeholder = db.Column(db.String(255), nullable=True)
    customer_city_placeholder = db.Column(db.String(255), nullable=True)
    # Hosting duration in days
    duration_days = db.Column(db.Integer, default=30)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)

class Conversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    button_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', backref='conversions')
    user = db.relationship('User', backref='conversions')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    customer_city = db.Column(db.String(100), nullable=False)
    product_name = db.Column(db.String(255), nullable=True)
    product_price = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='Processing', nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', backref='orders')
    user = db.relationship('User', backref='orders')

class PageVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)  # desktop, mobile, tablet
    browser = db.Column(db.String(100), nullable=True)
    time_spent = db.Column(db.Integer, default=0)  # in seconds
    page_views = db.Column(db.Integer, default=1)
    is_live = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', backref='visits')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'new_order', 'page_expiring', 'page_expired'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    related_id = db.Column(db.Integer, nullable=True)  # order_id or project_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='notifications')

# Create database tables
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Database tables already exist or error creating: {e}")
    
    # Add missing columns if they don't exist
    try:
        from sqlalchemy import text
        # Check if profile_image column exists
        result = db.session.execute(text("PRAGMA table_info(user)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'profile_image' not in columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN profile_image VARCHAR(200)"))
            print("Added profile_image column to user table")
        
        if 'hosting_limit' not in columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN hosting_limit INTEGER DEFAULT 5"))
            print("Added hosting_limit column to user table")
        
        # Check if duration_days column exists in project table
        try:
            result = db.session.execute(text("PRAGMA table_info(project)"))
            project_columns = [row[1] for row in result.fetchall()]
            
            if 'duration_days' not in project_columns:
                db.session.execute(text("ALTER TABLE project ADD COLUMN duration_days INTEGER DEFAULT 30"))
                print("Added duration_days column to project table")
            else:
                print("duration_days column already exists in project table")
        except Exception as migration_error:
            print(f"Error checking/adding duration_days column: {migration_error}")
            # Continue without failing the entire app
        
        db.session.commit()
        print("Database schema updated successfully!")
    except Exception as e:
        print(f"Error updating database schema: {e}")
        db.session.rollback()
    
    # Create admin user if it doesn't exist
    try:
        admin_user = User.query.filter_by(email='admin@gmail.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@gmail.com',
                name='Admin',
                password_hash=generate_password_hash('20042004'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.session.rollback()

# Helper functions
def is_logged_in():
    return 'user_id' in session

def is_admin():
    if not is_logged_in():
        return False
    user = User.query.get(session['user_id'])
    return user and user.is_admin

def get_current_user():
    if not is_logged_in():
        return None
    return User.query.get(session['user_id'])

def create_notification(user_id, notification_type, title, message, related_id=None):
    """Create a new notification for a user"""
    try:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        print(f"Notification created: {title} for user {user_id}")
        return notification
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.session.rollback()
        return None

def update_user_activity():
    if is_logged_in():
        user_session = UserSession.query.filter_by(user_id=session['user_id']).first()
        if user_session:
            user_session.last_activity = datetime.utcnow()
            db.session.commit()

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
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'})
    
    user = User(
        email=email,
        name=name,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({'success': True, 'redirect': url_for('home')})

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        if user.is_blocked:
            return jsonify({'success': False, 'message': 'Account is blocked'})
        
        session['user_id'] = user.id
        user.last_login = datetime.utcnow()
        
        # Create or update session
        user_session = UserSession.query.filter_by(user_id=user.id).first()
        if user_session:
            user_session.session_id = session.sid if hasattr(session, 'sid') else str(user.id)
            user_session.last_activity = datetime.utcnow()
        else:
            user_session = UserSession(
                user_id=user.id,
                session_id=session.sid if hasattr(session, 'sid') else str(user.id)
            )
            db.session.add(user_session)
        
        db.session.commit()
        
        if user.is_admin:
            return jsonify({'success': True, 'redirect': url_for('superadmin')})
        else:
            return jsonify({'success': True, 'redirect': url_for('home')})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/home')
def home():
    if not is_logged_in():
        return redirect(url_for('sign_in'))
    
    user = get_current_user()
    if user.is_blocked:
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
    if user.is_blocked:
        session.clear()
        flash('Your account has been blocked')
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('main.html', user=user)

@app.route('/superadmin')
def superadmin():
    if not is_logged_in() or not is_admin():
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('superadmin.html')

@app.route('/host')
def host():
    if not is_logged_in():
        return redirect(url_for('sign_in'))
    
    update_user_activity()
    return render_template('host.html')

@app.route('/page/<int:project_id>')
def view_hosted_page(project_id):
    # Get the project
    project = Project.query.get(project_id)
    if not project:
        return "Page not found", 404
    
    # Check if user has access to this project (either owner or public)
    user = get_current_user()
    if not user or (project.user_id != user.id and not user.is_admin):
        return "Access denied", 403
    
    # Combine HTML, CSS, and JS into a complete page
    conversion_tracking_js = ""
    # Analytics tracking JavaScript
    analytics_tracking_js = f"""
        <script>
        // Analytics tracking
        let startTime = Date.now();
        let hasTrackedInitialVisit = false;
        let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Track initial page visit only once
        if (!hasTrackedInitialVisit) {{
            hasTrackedInitialVisit = true;
            fetch('/api/analytics/track', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    project_id: {project.id},
                    time_spent: 0,
                    page_views: 1,
                    session_id: sessionId,
                    is_initial_visit: true
                }})
            }});
        }}
        
        // Track time spent on page (less frequently)
        setInterval(function() {{
            const timeSpent = Math.floor((Date.now() - startTime) / 1000);
            fetch('/api/analytics/track', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    project_id: {project.id},
                    time_spent: timeSpent,
                    page_views: 0, // Don't increment page views on time updates
                    session_id: sessionId,
                    is_initial_visit: false
                }})
            }});
        }}, 60000); // Update every 60 seconds instead of 30
        
        // Track page visibility changes
        document.addEventListener('visibilitychange', function() {{
            if (document.hidden) {{
                const timeSpent = Math.floor((Date.now() - startTime) / 1000);
                fetch('/api/analytics/track', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        project_id: {project.id},
                        time_spent: timeSpent,
                        page_views: 0, // Don't increment page views on visibility changes
                        session_id: sessionId,
                        is_initial_visit: false
                    }})
                }});
            }} else {{
                startTime = Date.now();
            }}
        }});
        </script>
    """
    
    if project.conversion_tracking_enabled and project.conversion_button_name:
        conversion_tracking_js = f"""
        <script>
        // Conversion and order tracking
        document.addEventListener('DOMContentLoaded', function() {{
            const buttonName = '{project.conversion_button_name}';
            const projectId = {project.id};
            
            // Customer tracking placeholders
            const customerNamePlaceholder = '{project.customer_name_placeholder or ""}';
            const customerPhonePlaceholder = '{project.customer_phone_placeholder or ""}';
            const customerCityPlaceholder = '{project.customer_city_placeholder or ""}';
            
            // Find all buttons with the conversion button name
            const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"], a');
            
            buttons.forEach(button => {{
                if (button.textContent.trim() === buttonName || button.value === buttonName) {{
                    button.addEventListener('click', function(e) {{
                        // Get customer data from form inputs
                        let customerName = '';
                        let customerPhone = '';
                        let customerCity = '';
                        
                        // Find inputs by placeholder text
                        console.log('Looking for inputs with placeholders:', {{
                            name: customerNamePlaceholder,
                            phone: customerPhonePlaceholder,
                            city: customerCityPlaceholder
                        }});
                        
                        if (customerNamePlaceholder) {{
                            const nameInput = document.querySelector(`input[placeholder*="${{customerNamePlaceholder}}"]`);
                            if (nameInput) {{
                                customerName = nameInput.value.trim();
                                console.log('Found name input:', nameInput, 'Value:', customerName);
                            }} else {{
                                console.log('Name input not found with placeholder:', customerNamePlaceholder);
                            }}
                        }}
                        
                        if (customerPhonePlaceholder) {{
                            const phoneInput = document.querySelector(`input[placeholder*="${{customerPhonePlaceholder}}"]`);
                            if (phoneInput) {{
                                customerPhone = phoneInput.value.trim();
                                console.log('Found phone input:', phoneInput, 'Value:', customerPhone);
                            }} else {{
                                console.log('Phone input not found with placeholder:', customerPhonePlaceholder);
                            }}
                        }}
                        
                        if (customerCityPlaceholder) {{
                            const cityInput = document.querySelector(`input[placeholder*="${{customerCityPlaceholder}}"]`);
                            if (cityInput) {{
                                customerCity = cityInput.value.trim();
                                console.log('Found city input:', cityInput, 'Value:', customerCity);
                            }} else {{
                                console.log('City input not found with placeholder:', customerCityPlaceholder);
                            }}
                        }}
                        
                        // Track the conversion
                        fetch('/api/conversion/track', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                project_id: projectId,
                                button_name: buttonName
                            }})
                        }}).then(response => response.json())
                        .then(data => {{
                            console.log('Conversion tracked:', data);
                        }}).catch(error => {{
                            console.error('Error tracking conversion:', error);
                        }});
                        
                        // Create order if we have customer data
                        if (customerName || customerPhone || customerCity) {{
                            console.log('Creating order with data:', {{
                                project_id: projectId,
                                customer_name: customerName,
                                customer_phone: customerPhone,
                                customer_city: customerCity
                            }});
                            
                            fetch('/api/orders/create', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json'
                                }},
                                body: JSON.stringify({{
                                    project_id: projectId,
                                    customer_name: customerName,
                                    customer_phone: customerPhone,
                                    customer_city: customerCity
                                }})
                            }}).then(response => response.json())
                            .then(data => {{
                                console.log('Order created successfully:', data);
                                if (data.success) {{
                                    alert('Order placed successfully! Order ID: ' + data.order_id);
                                }} else {{
                                    console.error('Order creation failed:', data.message);
                                }}
                            }}).catch(error => {{
                                console.error('Error creating order:', error);
                            }});
                        }} else {{
                            console.log('No customer data found to create order');
                        }}
                    }});
                }}
            }});
        }});
        </script>
        """
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{project.name}</title>
        <style>
            {project.css_code}
        </style>
    </head>
    <body>
        {project.html_code}
        <script>
            {project.js_code}
        </script>
        {analytics_tracking_js}
        {conversion_tracking_js}
    </body>
    </html>
    """
    
    return full_html

@app.route('/logout')
def logout():
    if is_logged_in():
        # Remove user session
        user_session = UserSession.query.filter_by(user_id=session['user_id']).first()
        if user_session:
            db.session.delete(user_session)
            db.session.commit()
    
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
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'profile_image': user.profile_image,
            'is_admin': user.is_admin
        }
    })

@app.route('/api/user/profile-image', methods=['POST'])
def update_profile_image():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        data = request.get_json()
        image_url = data.get('image_url', '').strip()
        
        # Allow empty URL to remove profile image
        if image_url:
            if not (image_url.startswith('http://') or image_url.startswith('https://')):
                return jsonify({'success': False, 'message': 'Invalid image URL format. Must start with http:// or https://'})
            
            # Check for common image file extensions
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
            if not any(image_url.lower().endswith(ext) for ext in image_extensions):
                return jsonify({'success': False, 'message': 'URL does not appear to be an image. Please use URLs ending with .jpg, .png, .gif, .webp, or .svg'})
        
        user = get_current_user()
        user.profile_image = image_url
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile image updated successfully',
            'profile_image': user.profile_image
        })
        
    except Exception as e:
        print(f"Error updating profile image: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile image: {str(e)}'})

@app.route('/api/projects')
def get_user_projects():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    
    project_list = []
    for project in projects:
        project_list.append({
            'id': project.id,
            'name': project.name,
            'created_at': project.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': project.updated_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify({'success': True, 'projects': project_list})

@app.route('/api/projects', methods=['POST'])
def save_project():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.get_json()
    user = get_current_user()
    
    project = Project(
        name=data.get('name', 'Untitled Project'),
        html_code=data.get('html', ''),
        css_code=data.get('css', ''),
        js_code=data.get('js', ''),
        user_id=user.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({'success': True, 'project_id': project.id})

@app.route('/api/projects/<int:project_id>')
def get_project(project_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    project = Project.query.filter_by(id=project_id, user_id=user.id).first()
    
    if not project:
        return jsonify({'success': False, 'message': 'Project not found'})
    
    return jsonify({
        'success': True,
        'project': {
            'id': project.id,
            'name': project.name,
            'html': project.html_code,
            'css': project.css_code,
            'js': project.js_code
        }
    })

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Project deleted successfully'})
    except Exception as e:
        print(f"Error deleting project {project_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting project: {str(e)}'})

@app.route('/api/projects/host', methods=['POST'])
def create_hosted_project():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        data = request.get_json()
        
        print(f"Creating project for user {user.id}: {data}")
        
        # Check hosting limit
        current_hosted_count = Project.query.filter_by(user_id=user.id).filter(Project.html_code.isnot(None)).count()
        if current_hosted_count >= user.hosting_limit:
            return jsonify({
                'success': False, 
                'message': f'You have reached your hosting limit of {user.hosting_limit} pages. Please delete some hosted pages or contact an administrator to increase your limit.'
            })
        
        # Get form data
        title = data.get('title', 'Untitled Page')
        html_code = data.get('html_code', '')
        css_code = data.get('css_code', '')
        js_code = data.get('js_code', '')
        conversion_button_name = data.get('conversion_button_name', '')
        conversion_tracking_enabled = data.get('conversion_tracking_enabled', False)
        product_name = data.get('product_name', '')
        product_price = data.get('product_price', '')
        customer_name_placeholder = data.get('customer_name_placeholder', '')
        customer_phone_placeholder = data.get('customer_phone_placeholder', '')
        customer_city_placeholder = data.get('customer_city_placeholder', '')
        duration_days = data.get('duration_days', 30)
        
        # Create new project
        new_project = Project(
            name=title,
            html_code=html_code,
            css_code=css_code,
            js_code=js_code,
            user_id=user.id,
            conversion_button_name=conversion_button_name,
            conversion_tracking_enabled=conversion_tracking_enabled,
            product_name=product_name,
            product_price=product_price,
            customer_name_placeholder=customer_name_placeholder,
            customer_phone_placeholder=customer_phone_placeholder,
            customer_city_placeholder=customer_city_placeholder,
            duration_days=duration_days
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        print(f"Project created successfully with ID: {new_project.id}")
        
        return jsonify({
            'success': True, 
            'message': 'Project created successfully',
            'project': {
                'id': new_project.id,
                'name': new_project.name,
                'created_at': new_project.created_at.isoformat(),
                'conversion_button_name': new_project.conversion_button_name,
                'conversion_tracking_enabled': new_project.conversion_tracking_enabled,
                'product_name': new_project.product_name,
                'product_price': new_project.product_price
            }
        })
    except Exception as e:
        print(f"Error creating project: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating project: {str(e)}'})

@app.route('/api/conversion/track', methods=['POST'])
def track_conversion():
    data = request.get_json()
    project_id = data.get('project_id')
    button_name = data.get('button_name')
    
    if not project_id or not button_name:
        return jsonify({'success': False, 'message': 'Missing required data'})
    
    # Get the project
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'message': 'Project not found'})
    
    # Check if conversion tracking is enabled and button name matches
    if not project.conversion_tracking_enabled or project.conversion_button_name != button_name:
        return jsonify({'success': False, 'message': 'Conversion tracking not enabled for this button'})
    
    # Create conversion record
    conversion = Conversion(
        project_id=project_id,
        user_id=project.user_id,
        button_name=button_name,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    db.session.add(conversion)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Conversion tracked successfully',
        'conversion_id': conversion.id
    })

@app.route('/api/host/conversions')
def host_conversions():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    
    # Get conversions for user's projects
    conversions = db.session.query(Conversion).join(Project).filter(Project.user_id == user.id).order_by(Conversion.created_at.desc()).all()
    
    conversion_data = []
    for conversion in conversions:
        conversion_data.append({
            'id': conversion.id,
            'project_id': conversion.project_id,
            'project_name': conversion.project.name,
            'button_name': conversion.button_name,
            'ip_address': conversion.ip_address,
            'created_at': conversion.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'conversions': conversion_data
    })

@app.route('/api/orders/create', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        customer_city = data.get('customer_city', '')
        
        if not project_id:
            return jsonify({'success': False, 'message': 'Project ID is required'})
        
        # Get the project
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'})
        
        # Create order record
        order = Order(
            project_id=project_id,
            user_id=project.user_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_city=customer_city,
            product_name=project.product_name,
            product_price=project.product_price,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.add(order)
        db.session.commit()
        
        # Create notification for new order
        create_notification(
            user_id=project.user_id,
            notification_type='new_order',
            title='New Order Received!',
            message=f'New order from {customer_name} for {project.product_name} - ${project.product_price}',
            related_id=order.id
        )
        
        print(f"Order created successfully: {order.id}")
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'order_id': order.id
        })
    except Exception as e:
        print(f"Error creating order: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating order: {str(e)}'})

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json()
    user_id = session.get('user_id') if is_logged_in() else None
    
    message = ContactMessage(
        name=data.get('name'),
        email=data.get('email'),
        message=data.get('message'),
        user_id=user_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Message sent successfully'})

# Admin API Routes
@app.route('/api/admin/stats')
def admin_stats():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    total_users = User.query.count()
    active_sessions = UserSession.query.count()
    blocked_users = User.query.filter_by(is_blocked=True).count()
    
    # User registrations in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users = User.query.filter(User.first_sign_in >= thirty_days_ago).count()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'active_sessions': active_sessions,
            'blocked_users': blocked_users,
            'new_users_30_days': new_users
        }
    })

@app.route('/api/admin/registrations-by-hour')
def admin_registrations_by_hour():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    # Get registrations for the last 30 days, grouped by hour
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Create a list of all hours in the last 30 days
    hours_data = []
    current_time = datetime.utcnow()
    
    # Group by 6-hour intervals for better visualization (4 data points per day)
    for i in range(120):  # 30 days * 4 intervals per day
        interval_start = current_time - timedelta(hours=i*6)
        interval_end = interval_start + timedelta(hours=6)
        
        # Count users registered in this 6-hour interval
        count = User.query.filter(
            User.first_sign_in >= interval_start,
            User.first_sign_in < interval_end
        ).count()
        
        # Format the label (show date and time range)
        label = interval_start.strftime('%m/%d %H:00')
        hours_data.append({
            'label': label,
            'count': count,
            'timestamp': interval_start.isoformat()
        })
    
    # Reverse to show chronological order (oldest to newest)
    hours_data.reverse()
    
    return jsonify({
        'success': True,
        'data': hours_data
    })

@app.route('/api/admin/users')
def admin_users():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    users = User.query.all()
    user_list = []
    
    for user in users:
        user_list.append({
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'first_sign_in': user.first_sign_in.strftime('%Y-%m-%d %H:%M'),
            'status': 'Blocked' if user.is_blocked else 'Active',
            'is_admin': user.is_admin,
            'hosting_limit': user.hosting_limit
        })
    
    return jsonify({'success': True, 'users': user_list})

@app.route('/api/admin/users/<int:user_id>/toggle-block', methods=['POST'])
def admin_toggle_user_block(user_id):
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    if user.is_admin:
        return jsonify({'success': False, 'message': 'Cannot block admin users'})
    
    user.is_blocked = not user.is_blocked
    
    # Remove user session if blocking
    if user.is_blocked:
        user_session = UserSession.query.filter_by(user_id=user.id).first()
        if user_session:
            db.session.delete(user_session)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_blocked': user.is_blocked,
        'message': f'User {"blocked" if user.is_blocked else "unblocked"} successfully'
    })

@app.route('/api/admin/users/<int:user_id>/projects')
def admin_user_projects(user_id):
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    project_list = []
    
    for project in projects:
        project_list.append({
            'id': project.id,
            'name': project.name,
            'last_saved': project.updated_at.strftime('%Y-%m-%d %H:%M'),
            'code': f"{project.html_code}\n<style>{project.css_code}</style>\n<script>{project.js_code}</script>"
        })
    
    return jsonify({
        'success': True,
        'user_email': user.email,
        'projects': project_list
    })

@app.route('/api/admin/messages')
def admin_messages():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    messages = ContactMessage.query.order_by(ContactMessage.timestamp.desc()).all()
    message_list = []
    
    for msg in messages:
        message_list.append({
            'id': msg.id,
            'name': msg.name,
            'email': msg.email,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
            'user_id': msg.user_id
        })
    
    return jsonify({'success': True, 'messages': message_list})

@app.route('/api/admin/hosted-pages')
def admin_hosted_pages():
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    # Get all projects that are hosted (have html_code)
    projects = Project.query.filter(Project.html_code.isnot(None)).order_by(Project.updated_at.desc()).all()
    
    page_list = []
    for project in projects:
        page_list.append({
            'id': project.id,
            'title': project.name,
            'user_id': project.user_id,
            'user_email': project.user.email,
            'status': 'Live',
            'created_at': project.created_at.isoformat(),
            'expiration_date': (project.updated_at + timedelta(days=getattr(project, 'duration_days', 30))).isoformat(),
            'code': f"{project.html_code}\n<style>{project.css_code}</style>\n<script>{project.js_code}</script>"
        })
    
    # Get all users for the filter
    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'email': user.email,
            'hosting_limit': user.hosting_limit
        })
    
    return jsonify({'success': True, 'pages': page_list, 'users': user_list})

@app.route('/api/admin/users/<int:user_id>/hosting-limit', methods=['PUT'])
def admin_update_hosting_limit(user_id):
    if not is_admin():
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    data = request.get_json()
    new_limit = data.get('hosting_limit')
    
    if new_limit is None or new_limit < 0:
        return jsonify({'success': False, 'message': 'Invalid hosting limit'})
    
    user.hosting_limit = new_limit
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Hosting limit updated successfully'})

# Host Dashboard API Routes
@app.route('/api/host/pages')
def host_pages():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    projects = Project.query.filter_by(user_id=user.id).order_by(Project.updated_at.desc()).all()
    
    page_list = []
    for project in projects:
        page_list.append({
            'id': project.id,
            'title': project.name,
            'status': 'Live',
            'expirationDate': (project.updated_at + timedelta(days=getattr(project, 'duration_days', 30))).strftime('%Y-%m-%d'),
            'code': f"{project.html_code}\n<style>{project.css_code}</style>\n<script>{project.js_code}</script>",
            'tracking': {
                'productName': project.product_name or project.name,
                'productPrice': project.product_price or '$99.99'
            },
            'stock': 100,  # Default stock
            'product_name': project.product_name,
            'product_price': project.product_price
        })
    
    return jsonify({
        'success': True,
        'pages': page_list,
        'pageLimit': user.hosting_limit  # Use user's actual hosting limit
    })

@app.route('/api/host/orders')
def host_orders():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    
    # Get orders for user's projects
    orders = db.session.query(Order).join(Project).filter(Project.user_id == user.id).order_by(Order.created_at.desc()).all()
    
    order_data = []
    for order in orders:
        order_data.append({
            'id': f"ORD-{order.id:06d}",
            'customer': order.customer_name,
            'status': order.status or 'Processing',
            'amount': order.product_price or '$99.99',
            'date': order.created_at.strftime('%Y-%m-%d'),
            'phone': order.customer_phone,
            'city': order.customer_city,
            'product': order.product_name or order.project.name
        })
    
    return jsonify({'success': True, 'orders': order_data})

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'})
        
        # Valid statuses
        valid_statuses = ['Processing', 'Completed', 'Shipping', 'Cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'})
        
        # Get the order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        # Check if user owns this order (through project)
        if order.project.user_id != user.id and not user.is_admin:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        # Update status
        order.status = new_status
        db.session.commit()
        
        print(f"Order {order_id} status updated to {new_status}")
        
        return jsonify({
            'success': True,
            'message': 'Order status updated successfully',
            'new_status': new_status
        })
    except Exception as e:
        print(f"Error updating order status: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating order status: {str(e)}'})

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        if order.project.user_id != user.id and not user.is_admin:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        # Only allow deletion of cancelled orders
        if order.status != 'Cancelled':
            return jsonify({'success': False, 'message': 'Only cancelled orders can be deleted'})
        
        db.session.delete(order)
        db.session.commit()
        
        print(f"Order {order_id} deleted successfully")
        
        return jsonify({
            'success': True,
            'message': 'Order deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting order: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting order: {str(e)}'})

@app.route('/api/notifications')
def get_notifications():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(20).all()
        
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'is_read': notification.is_read,
                'related_id': notification.related_id,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': get_time_ago(notification.created_at)
            })
        
        return jsonify({
            'success': True,
            'notifications': notification_list
        })
        
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return jsonify({'success': False, 'message': f'Error fetching notifications: {str(e)}'})

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        notification = Notification.query.get(notification_id)
        
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'})
        
        if notification.user_id != user.id:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        print(f"Error marking notification as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error marking notification as read: {str(e)}'})

@app.route('/api/notifications/read-all', methods=['PUT'])
def mark_all_notifications_read():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        user = get_current_user()
        Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All notifications marked as read'
        })
        
    except Exception as e:
        print(f"Error marking all notifications as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error marking all notifications as read: {str(e)}'})

def get_time_ago(dt):
    """Get human readable time ago string"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def check_expiring_pages():
    """Check for pages that are expiring soon and create notifications"""
    try:
        # Get all projects and check their individual expiration dates
        all_projects = Project.query.filter(Project.html_code.isnot(None)).all()
        
        expiring_pages = []
        expired_pages = []
        
        for project in all_projects:
            days_since_created = (datetime.utcnow() - project.created_at).days
            duration_days = getattr(project, 'duration_days', 30)
            days_left = duration_days - days_since_created
            
            # Check if expiring soon (5 days or less remaining)
            if 0 < days_left <= 5:
                expiring_pages.append(project)
            # Check if expired
            elif days_left <= 0:
                expired_pages.append(project)
        
        # Create notifications for expiring pages
        for project in expiring_pages:
            days_since_created = (datetime.utcnow() - project.created_at).days
            duration_days = getattr(project, 'duration_days', 30)
            days_left = duration_days - days_since_created
            
            # Check if we already created a notification for this project
            existing_notification = Notification.query.filter_by(
                user_id=project.user_id,
                type='page_expiring',
                related_id=project.id
            ).first()
            
            if not existing_notification:
                create_notification(
                    user_id=project.user_id,
                    notification_type='page_expiring',
                    title='Page Expiring Soon!',
                    message=f'Your hosted page "{project.name}" will expire in {days_left} days. Consider renewing it.',
                    related_id=project.id
                )
        
        # Create notifications for expired pages
        for project in expired_pages:
            # Check if we already created a notification for this project
            existing_notification = Notification.query.filter_by(
                user_id=project.user_id,
                type='page_expired',
                related_id=project.id
            ).first()
            
            if not existing_notification:
                create_notification(
                    user_id=project.user_id,
                    notification_type='page_expired',
                    title='Page Expired!',
                    message=f'Your hosted page "{project.name}" has expired. You can create a new one anytime.',
                    related_id=project.id
                )
        
        print(f"Checked {len(expiring_pages)} expiring pages and {len(expired_pages)} expired pages")
        
    except Exception as e:
        print(f"Error checking expiring pages: {e}")

@app.route('/api/notifications/check-expiring')
def check_expiring_pages_endpoint():
    try:
        if not is_logged_in():
            return jsonify({'success': False, 'message': 'Not logged in'})
        
        check_expiring_pages()
        
        return jsonify({
            'success': True,
            'message': 'Expiring pages checked successfully'
        })
        
    except Exception as e:
        print(f"Error checking expiring pages: {e}")
        return jsonify({'success': False, 'message': f'Error checking expiring pages: {str(e)}'})

@app.route('/api/host/customers')
def host_customers():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    
    # Get all orders for this user and aggregate customer data
    orders = db.session.query(Order).join(Project).filter(Project.user_id == user.id).all()
    
    # Group orders by phone number (unique identifier) to get customer data
    customers_dict = {}
    
    for order in orders:
        phone = order.customer_phone
        if phone not in customers_dict:
            customers_dict[phone] = {
                'name': order.customer_name,
                'phone': order.customer_phone,
                'city': order.customer_city,
                'total_spent': 0,
                'order_count': 0
            }
        
        # Add to total spent (convert price to number)
        try:
            price_str = order.product_price or '0'
            # Remove currency symbols and convert to float
            price_clean = ''.join(c for c in price_str if c.isdigit() or c == '.')
            price_value = float(price_clean) if price_clean else 0
            customers_dict[phone]['total_spent'] += price_value
        except (ValueError, TypeError):
            pass
        
        customers_dict[phone]['order_count'] += 1
    
    # Convert to list and format
    customers = []
    for phone, customer_data in customers_dict.items():
        customers.append({
            'name': customer_data['name'],
            'phone': customer_data['phone'],
            'city': customer_data['city'],
            'totalSpent': f"${customer_data['total_spent']:.2f}",
            'orderCount': customer_data['order_count']
        })
    
    # Sort by total spent (descending)
    customers.sort(key=lambda x: float(x['totalSpent'].replace('$', '')), reverse=True)
    
    return jsonify({
        'success': True,
        'customers': customers
    })

@app.route('/api/analytics/track', methods=['POST'])
def track_page_visit():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        time_spent = data.get('time_spent', 0)
        page_views = data.get('page_views', 0)  # Changed default to 0
        session_id = data.get('session_id', '')
        is_initial_visit = data.get('is_initial_visit', False)
        
        if not project_id:
            return jsonify({'success': False, 'message': 'Project ID is required'})
        
        # Get visitor info
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Simple device detection
        device_type = 'desktop'
        if 'mobile' in user_agent.lower() or 'android' in user_agent.lower():
            device_type = 'mobile'
        elif 'tablet' in user_agent.lower() or 'ipad' in user_agent.lower():
            device_type = 'tablet'
        
        # Simple browser detection
        browser = 'Unknown'
        if 'chrome' in user_agent.lower():
            browser = 'Chrome'
        elif 'firefox' in user_agent.lower():
            browser = 'Firefox'
        elif 'safari' in user_agent.lower():
            browser = 'Safari'
        elif 'edge' in user_agent.lower():
            browser = 'Edge'
        
        # Check if this is an existing visit (same IP and project)
        existing_visit = PageVisit.query.filter_by(
            project_id=project_id, 
            ip_address=ip_address
        ).first()
        
        if existing_visit:
            # Update existing visit
            if is_initial_visit:
                # Only increment page views on initial visit
                existing_visit.page_views += page_views
            # Always update time spent and activity
            existing_visit.time_spent = max(existing_visit.time_spent, time_spent)
            existing_visit.last_activity = datetime.utcnow()
            existing_visit.is_live = True
        else:
            # Create new visit only if this is an initial visit
            if is_initial_visit:
                visit = PageVisit(
                    project_id=project_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_type=device_type,
                    browser=browser,
                    time_spent=time_spent,
                    page_views=page_views,
                    is_live=True
                )
                db.session.add(visit)
        
        db.session.commit()
        
        # Clean up old inactive visits (mark as not live if inactive for more than 5 minutes)
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        old_visits = PageVisit.query.filter(
            PageVisit.last_activity < five_minutes_ago,
            PageVisit.is_live == True
        ).all()
        
        for visit in old_visits:
            visit.is_live = False
        
        if old_visits:
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error tracking visit: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/host/analytics')
def host_analytics():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user = get_current_user()
    project_id = request.args.get('project_id')
    
    # Get all projects for this user
    if project_id:
        projects = Project.query.filter_by(id=project_id, user_id=user.id).all()
    else:
        projects = Project.query.filter_by(user_id=user.id).all()
    
    if not projects:
        return jsonify({
            'success': True,
            'analytics': {
                'totalViews': 0,
                'totalSales': 0,
                'conversionRate': 0,
                'revenue': 0,
                'liveVisitors': 0,
                'avgTimeSpent': 0,
                'visitorsByDay': {'labels': [], 'data': []},
                'visitorsByCity': {'labels': [], 'data': []},
                'visitorsByDevice': {'labels': [], 'data': []},
                'totalOrders': 0,
                'totalMoney': 0
            }
        })
    
    project_ids = [p.id for p in projects]
    
    # Get visits for these projects
    visits = PageVisit.query.filter(PageVisit.project_id.in_(project_ids)).all()
    orders = Order.query.filter(Order.project_id.in_(project_ids)).all()
    
    # Calculate analytics
    total_views = sum(v.page_views for v in visits)
    total_orders = len(orders)
    conversion_rate = (total_orders / total_views * 100) if total_views > 0 else 0
    
    # Calculate revenue
    total_revenue = 0
    for order in orders:
        try:
            price_str = order.product_price or '0'
            price_clean = ''.join(c for c in price_str if c.isdigit() or c == '.')
            total_revenue += float(price_clean) if price_clean else 0
        except (ValueError, TypeError):
            pass
    
    # Live visitors (active in last 5 minutes)
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    live_visitors = PageVisit.query.filter(
        PageVisit.project_id.in_(project_ids),
        PageVisit.last_activity >= five_minutes_ago,
        PageVisit.is_live == True
    ).count()
    
    # Average time spent
    avg_time_spent = sum(v.time_spent for v in visits) / len(visits) if visits else 0
    
    # Visitors by day (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_visits = PageVisit.query.filter(
        PageVisit.project_id.in_(project_ids),
        PageVisit.created_at >= seven_days_ago
    ).all()
    
    visitors_by_day = {}
    for visit in recent_visits:
        day = visit.created_at.strftime('%Y-%m-%d')
        visitors_by_day[day] = visitors_by_day.get(day, 0) + 1
    
    # Sort by date
    sorted_days = sorted(visitors_by_day.keys())
    visitors_by_day_data = {
        'labels': [datetime.strptime(day, '%Y-%m-%d').strftime('%a') for day in sorted_days],
        'data': [visitors_by_day[day] for day in sorted_days]
    }
    
    # Visitors by city
    city_counts = {}
    for visit in visits:
        if visit.city:
            city_counts[visit.city] = city_counts.get(visit.city, 0) + 1
    
    # Top 5 cities
    top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    visitors_by_city = {
        'labels': [city[0] for city in top_cities],
        'data': [city[1] for city in top_cities]
    }
    
    # Visitors by device
    device_counts = {'desktop': 0, 'mobile': 0, 'tablet': 0}
    for visit in visits:
        device = visit.device_type or 'desktop'
        if device in device_counts:
            device_counts[device] += 1
    
    visitors_by_device = {
        'labels': ['Desktop', 'Mobile', 'Tablet'],
        'data': [device_counts['desktop'], device_counts['mobile'], device_counts['tablet']]
    }
    
    return jsonify({
        'success': True,
        'analytics': {
            'totalViews': total_views,
            'totalSales': total_orders,
            'conversionRate': round(conversion_rate, 2),
            'revenue': round(total_revenue, 2),
            'liveVisitors': live_visitors,
            'avgTimeSpent': round(avg_time_spent, 1),
            'visitorsByDay': visitors_by_day_data,
            'visitorsByCity': visitors_by_city,
            'visitorsByDevice': visitors_by_device,
            'totalOrders': total_orders,
            'totalMoney': round(total_revenue, 2)
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
