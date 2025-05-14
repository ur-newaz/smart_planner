from app import create_app
from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash
from datetime import date

def create_admin_user():
    """
    Create an admin user in the database
    """
    app = create_app()
    
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(email='jshahnewazkhan@gmail.com').first()
        
        if existing_admin:
            print("Admin user already exists.")
            return
        
        # Create admin user
        admin = User(
            name='Admin1',
            email='jshahnewazkhan@gmail.com',
            student_id='ADMIN',  # Special value for admin
            department='Administration',
            # Using a placeholder date for admin
            date_of_birth=date(2000, 1, 1),
            password=generate_password_hash('admin12345'),
            is_verified=True,
            user_type='admin'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("Admin user created successfully.")

if __name__ == "__main__":
    create_admin_user() 