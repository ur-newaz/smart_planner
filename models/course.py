from extensions import db
from datetime import datetime

class CourseWeight(db.Model):
    __tablename__ = 'course_weight'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('CourseDirectory', backref='course', lazy=True)
    
    def __repr__(self):
        return f"CourseWeight('{self.course_code}', '{self.department}', weight={self.weight})"

class CourseDirectory(db.Model):
    __tablename__ = 'course_directory'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), db.ForeignKey('course_weight.course_code'), nullable=False)
    actual_weight = db.Column(db.Float, nullable=False)
    current_weight = db.Column(db.Float, nullable=False)
    course_day = db.Column(db.String(20), nullable=False)  # e.g., "Monday,Wednesday"
    course_time_start = db.Column(db.Time, nullable=False)
    course_time_end = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"CourseDirectory('{self.course_code}', student_id={self.student_id}, current_weight={self.current_weight})" 