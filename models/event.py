from datetime import datetime
from extensions import db

class EventType:
    ASSIGNMENT = 'assignment'
    QUIZ = 'quiz'
    MIDTERM = 'midterm'
    FINAL = 'final'
    
    @classmethod
    def get_weight_modifier(cls, event_type):
        """Get the weight modifier for a given event type"""
        modifiers = {
            cls.ASSIGNMENT: 1.5,
            cls.QUIZ: 2.5,
            cls.MIDTERM: 3.5,
            cls.FINAL: 4.0
        }
        return modifiers.get(event_type, 0)
    
    @classmethod
    def get_max_days_before(cls, event_type):
        """Get the maximum days before the event that it can be added"""
        days_before = {
            cls.ASSIGNMENT: 7,
            cls.QUIZ: 3,
            cls.MIDTERM: 5,
            cls.FINAL: 5
        }
        return days_before.get(event_type, 0)

class Event(db.Model):
    """Model for tracking course events like assignments, quizzes, exams"""
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_directory_id = db.Column(db.Integer, db.ForeignKey('course_directory.id'), nullable=False)
    
    event_type = db.Column(db.String(20), nullable=False)  # assignment, quiz, midterm, final
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_completed = db.Column(db.Boolean, default=False)
    is_expired = db.Column(db.Boolean, default=False)
    
    email_notification_sent = db.Column(db.Boolean, default=False)
    
    # Relationships
    student = db.relationship('User', backref=db.backref('events', lazy=True))
    course = db.relationship('CourseDirectory', backref=db.backref('events', lazy=True))
    
    def __repr__(self):
        return f'<Event {self.title} for {self.course.course_code}>'
    
    def mark_as_completed(self):
        """Mark the event as completed and adjust course weight"""
        if not self.is_completed and not self.is_expired:
            self.is_completed = True
            
            # Reduce the course weight
            weight_modifier = EventType.get_weight_modifier(self.event_type)
            completion_bonus = 0.5
            total_reduction = weight_modifier + completion_bonus
            
            # Ensure weight doesn't go below the original course weight
            original_weight = self.course.actual_weight
            current_weight = self.course.current_weight
            new_weight = max(original_weight, current_weight - total_reduction)
            
            self.course.current_weight = new_weight
            return True
        return False
    
    @classmethod
    def mark_expired_events(cls):
        """Mark events that have passed their date as expired"""
        now = datetime.utcnow()
        expired_events = cls.query.filter(
            cls.event_date < now,
            cls.is_expired == False,
            cls.is_completed == False
        ).all()
        
        for event in expired_events:
            event.is_expired = True
        
        if expired_events:
            db.session.commit()
        
        return len(expired_events)
    
    @classmethod
    def check_notifications_to_send(cls):
        """Check for notifications that need to be sent 1 day before the event"""
        from datetime import timedelta
        from utils.email_utils import send_event_reminder_email
        
        # Calculate the date range for events happening in the next 24 hours
        notification_time = datetime.utcnow() + timedelta(days=1)
        start_window = notification_time - timedelta(hours=1)
        end_window = notification_time + timedelta(hours=1)
        
        # Find events in the notification window that haven't had emails sent yet
        events_to_notify = cls.query.filter(
            cls.event_date.between(start_window, end_window),
            cls.email_notification_sent == False,
            cls.is_expired == False,
            cls.is_completed == False
        ).all()
        
        # Create notifications and send emails
        from models.notification import Notification
        
        notification_count = 0
        for event in events_to_notify:
            # Create in-app notification
            notification_id = f"event_{event.id}_{int(datetime.utcnow().timestamp())}"
            notification = Notification(
                user_id=event.student_id,
                identifier=notification_id,
                message=f"Reminder: {event.title} ({event.event_type}) for {event.course.course_code} is due tomorrow!"
            )
            db.session.add(notification)
            
            # Send email notification
            if event.student.email:
                try:
                    send_event_reminder_email(event)
                    event.email_notification_sent = True
                    notification_count += 1
                except Exception as e:
                    print(f"Error sending event reminder email: {str(e)}")
        
        if notification_count > 0:
            db.session.commit()
        
        return notification_count 