from flask import Flask
import os
from dotenv import load_dotenv
from extensions import db, login_manager
from flask_migrate import Migrate
import threading
import time
from datetime import datetime

# Load environment variables
load_dotenv()

def check_events_worker(app):
    """Background worker to check for events needing notification"""
    with app.app_context():
        from models import Event
        
        while True:
            try:
                # Mark expired events
                expired_count = Event.mark_expired_events()
                if expired_count > 0:
                    print(f"{datetime.utcnow()}: Marked {expired_count} events as expired")
                
                # Send notifications for upcoming events
                notification_count = Event.check_notifications_to_send()
                if notification_count > 0:
                    print(f"{datetime.utcnow()}: Sent {notification_count} event notifications")
                
            except Exception as e:
                print(f"Error in background worker: {str(e)}")
            
            # Check every 30 minutes
            time.sleep(1800)

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email configuration
    app.config['SENDGRID_API_KEY'] = os.getenv('SENDGRID_API_KEY')
    app.config['SENDGRID_FROM_EMAIL'] = os.getenv('SENDGRID_FROM_EMAIL')
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Import all models to ensure they're tracked by Flask-Migrate
    from models import User, CourseWeight, CourseDirectory, Notification, Message, Event
    
    # Import and register blueprints
    from controllers.auth_controller import auth_bp
    from controllers.main_controller import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    return app

# Create the application instance for Gunicorn
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create tables
        db.create_all()
        print("Database tables created successfully")
    
    # Start background worker for event notifications
    worker_thread = threading.Thread(target=check_events_worker, args=(app,), daemon=True)
    worker_thread.start()
    print("Background worker started")
    
    app.run(debug=True) 