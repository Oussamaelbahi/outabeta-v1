# OUTA - Visual Page Builder

A modern web application for building landing pages with a visual drag-and-drop interface, built with Python Flask backend.

## Features

- **User Authentication**: Sign up, sign in, and user management
- **Visual Page Builder**: Drag-and-drop interface for creating landing pages
- **Pre-built Sections**: Welcome bars, product pages, video promotions, and more
- **Custom Liquid Sections**: Add your own custom code sections
- **Project Management**: Save, edit, and manage your projects
- **Admin Panel**: Comprehensive admin dashboard for user and project management
- **Responsive Design**: Mobile and desktop preview modes
- **Contact System**: Built-in contact form for user feedback

## Admin Access

- **Email**: admin@gmail.com
- **Password**: 20042004

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Option 1: Simplified Version (Recommended for Windows)

The simplified version uses JSON file storage instead of SQLite, avoiding compilation issues on Windows.

1. **Install dependencies**
   ```bash
   py -m pip install -r requirements_simple.txt
   ```

2. **Run the application**
   ```bash
   py app_simple.py
   ```

3. **Or use the batch file (Windows)**
   ```bash
   start_simple.bat
   ```

### Option 2: Full Version with SQLite

The full version includes SQLite database support but may require C++ build tools on Windows.

1. **Install dependencies**
   ```bash
   py -m pip install -r requirements.txt
   ```

2. **Run the application**
   ```bash
   py app.py
   ```

3. **Or use the batch file (Windows)**
   ```bash
   start.bat
   ```

### Access the Application

- Open your web browser and go to: `http://localhost:5000`
- The application will automatically redirect you to the sign-in page

### Database

- **Simplified Version**: Uses `data.json` file for storage
- **Full Version**: Uses SQLite database (`outa.db`)
- Database/files are automatically created on first run
- Admin user is automatically created with the credentials above

## Usage

### For Regular Users

1. **Sign Up**: Create a new account with your email and password
2. **Sign In**: Access your dashboard and saved projects
3. **Build Pages**: Use the visual builder to create landing pages
4. **Save Projects**: Save your work with custom names
5. **Export Code**: Get clean HTML, CSS, and JavaScript code

### For Admins

1. **Sign In**: Use admin credentials to access the super admin panel
2. **Dashboard**: View statistics including total users, active sessions, and blocked users
3. **User Management**: View all users, block/unblock accounts, and manage user status
4. **Project Overview**: View projects saved by all users
5. **Contact Messages**: Monitor contact form submissions

## File Structure

```
outa-v4/
├── app.py                 # Full Flask application with SQLite
├── app_simple.py          # Simplified Flask application (JSON storage)
├── requirements.txt       # Full version dependencies
├── requirements_simple.txt # Simplified version dependencies
├── README.md             # This file
├── start.bat             # Windows startup script (full version)
├── start_simple.bat      # Windows startup script (simplified version)
├── start.sh              # Unix startup script (full version)
├── start_simple.sh       # Unix startup script (simplified version)
├── templates/            # HTML templates
│   ├── home.html        # User dashboard
│   ├── main.html        # Visual page builder
│   ├── index.html       # Sign in/up page
│   └── superadmin.html  # Admin panel
├── outa.db              # SQLite database (full version only)
└── data.json            # JSON data file (simplified version only)
```

## API Endpoints

### Authentication
- `POST /signup` - User registration
- `POST /signin` - User login
- `GET /logout` - User logout

### User Management
- `GET /api/user/profile` - Get current user profile
- `GET /api/projects` - Get user's projects
- `POST /api/projects` - Save new project
- `GET /api/projects/<id>` - Get specific project

### Contact
- `POST /api/contact` - Submit contact form

### Admin (Admin only)
- `GET /api/admin/stats` - Get admin statistics
- `GET /api/admin/users` - Get all users
- `POST /api/admin/users/<id>/toggle-block` - Block/unblock user
- `GET /api/admin/users/<id>/projects` - Get user's projects
- `GET /api/admin/messages` - Get contact messages

## Security Features

- Password hashing using Werkzeug
- Session management
- User blocking system
- Admin-only access to sensitive endpoints
- Input validation and sanitization

## Browser Support

- Modern browsers with ES6+ support
- Chrome, Firefox, Safari, Edge (latest versions)

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change the port in the Python files
   - Or kill the process using the port

2. **Database/File errors**
   - Delete `outa.db` or `data.json` file and restart the application
   - Check file permissions in the project directory

3. **Import errors**
   - Ensure all dependencies are installed: `py -m pip install -r requirements_simple.txt`
   - Check Python version compatibility

4. **C++ compilation errors (full version)**
   - Use the simplified version instead
   - Or install Microsoft Visual C++ Build Tools

### Getting Help

- Check the browser console for JavaScript errors
- Check the Python console for backend errors
- Ensure all files are in the correct directory structure

## Development

### Adding New Features

1. **Backend**: Add new routes in the Python files
2. **Frontend**: Modify HTML templates in `templates/` directory
3. **Storage**: Modify the data structure in the appropriate file

### Testing

- Test user registration and login
- Test page building functionality
- Test admin panel features
- Test contact form submission

## License

This project is for educational and development purposes.

## Support

For issues or questions, check the troubleshooting section above or review the code comments for implementation details.
