from extensions import db
from datetime import datetime, timedelta

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    identifier = db.Column(db.String(50), unique=True, nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    @property
    def is_expired(self):
        """
        Check if the notification is older than 24 hours
        """
        return (datetime.utcnow() - self.created_at) > timedelta(hours=24)
    
    @classmethod
    def remove_expired(cls):
        """
        Remove all notifications older than 24 hours
        """
        expiry_date = datetime.utcnow() - timedelta(hours=24)
        expired = cls.query.filter(cls.created_at < expiry_date).all()
        for notification in expired:
            db.session.delete(notification)
        db.session.commit()
    
    def __repr__(self):
        return f"Notification(user_id={self.user_id}, identifier='{self.identifier}', created={self.created_at})" 