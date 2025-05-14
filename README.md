# Schedule Planner

A comprehensive web application for managing academic schedules, optimizing study routines, and tracking course events.

## Features

- **Class Schedule Management**: Add, edit, and delete courses with customizable time slots
- **Study Routine Optimization**: Generate optimized study schedules using:
  - Genetic Algorithm
  - Ant Colony Optimization
- **Event Management System**: Track assignments, quizzes, midterms, and finals
  - Automatic weight adjustments based on event types
  - Email notifications for upcoming events
- **Dashboard**: Visualize your weekly schedule at a glance
- **PDF Export**: Download your schedule as a PDF file
- **User Authentication**: Secure login and registration system
- **Profile Management**: Update personal details and password
- **Admin Dashboard**: Manage departments, courses, and users (admin only)

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- wkhtmltopdf (for PDF generation)

### Step 1: Clone the repository

```bash
git clone https://github.com/yourusername/schedule-planner.git
cd schedule-planner
```

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

Activate the virtual environment:

- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set up environment variables

Create a `.env` file in the project root with the following variables:

```
SECRET_KEY=your_secret_key_here
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=your_verified_email@example.com
```

### Step 5: Initialize the database

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Step 6: Run the application

```bash
python app.py
```

The application will be available at http://127.0.0.1:5000/

## Project Structure

```
schedule-planner/
├── app.py                 # Main application entry point
├── extensions.py          # Flask extensions
├── controllers/           # Route handlers
│   ├── auth_controller.py # Authentication routes
│   └── main_controller.py # Main application routes
├── models/                # Database models
│   ├── user.py
│   ├── course.py
│   ├── event.py
│   ├── notification.py
│   └── message.py
├── static/                # Static assets
│   ├── css/
│   └── js/
├── templates/             # HTML templates
│   ├── auth/
│   ├── dashboard/
│   ├── admin/
│   └── main/
├── utils/                 # Utility functions
│   ├── email_utils.py
│   ├── genetic_optimizer.py
│   └── ant_colony_optimizer.py
└── instance/              # Instance-specific files (e.g., database)
```

## Development

### Database Migrations

When you make changes to the database models, run:

```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Running with Debug Mode

```bash
python app.py
```

## Technologies Used

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Bootstrap 5, JavaScript
- **Optimization Algorithms**: DEAP (Genetic Algorithm), ACO-Pants (Ant Colony Optimization)
- **PDF Generation**: wkhtmltopdf
- **Email Notifications**: SendGrid

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Bootstrap](https://getbootstrap.com/) - Frontend framework
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [DEAP](https://github.com/DEAP/deap) - Distributed Evolutionary Algorithms in Python
- [ACO-Pants](https://github.com/rhgrant10/pants) - Ant Colony Optimization 