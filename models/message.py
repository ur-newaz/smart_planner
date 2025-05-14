from extensions import db
from datetime import datetime

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
    
    # Self-referential relationship for message threads
    replies = db.relationship('Message', 
                              backref=db.backref('parent', remote_side=[id]),
                              lazy='dynamic')
    
    def get_thread(self):
        """
        Get all messages in the same thread
        """
        # If this is a parent message
        if self.parent_id is None:
            return [self] + list(self.replies.all())
        # If this is a reply
        else:
            parent = self.parent
            return parent.get_thread()
    
    def __repr__(self):
        return f"Message(from={self.sender_id}, to={self.receiver_id}, created={self.created_at})" 