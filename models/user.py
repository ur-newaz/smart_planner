from flask_login import UserMixin
from datetime import datetime
from extensions import db, login_manager
import secrets

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    user_type = db.Column(db.String(20), default='student')  # 'student', 'admin', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp_secret = db.Column(db.String(32), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, default=0)
    
    # Relationships
    notifications = db.relationship('Notification', backref='user', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    courses = db.relationship('CourseDirectory', backref='student', lazy=True)
    
    def __repr__(self):
        return f"User('{self.name}', '{self.email}', '{self.student_id}')"
        
    def generate_otp(self):
        """Generate a new OTP for the user"""
        self.otp_secret = secrets.token_hex(3).upper()  # 6-digit hex code
        self.otp_created_at = datetime.utcnow()
        self.otp_attempts = 0
        return self.otp_secret 