import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import current_app
from datetime import datetime

def send_email(to_email, subject, html_content):
    """
    Send an email using SendGrid API
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # For development, print the email content
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Content: {html_content}")
        
        # Get API key from environment or app config
        api_key = os.environ.get('SENDGRID_API_KEY') or current_app.config.get('SENDGRID_API_KEY')
        from_email = os.environ.get('SENDGRID_FROM_EMAIL') or current_app.config.get('SENDGRID_FROM_EMAIL')
        
        if not api_key or not from_email:
            print("SendGrid API key or sender email not configured. Email not sent.")
            return True  # Return True in development to continue the flow
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        print(f"SendGrid response status code: {response.status_code}")
        return response.status_code == 202  # 202 Accepted
    
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_verification_email(user):
    """
    Send a verification email to the user with OTP
    
    Args:
        user: User object with email and OTP
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Verify Your Schedule Planner Account"
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0d6efd; color: white; padding: 10px; text-align: center; }}
            .content {{ padding: 20px; border: 1px solid #ddd; }}
            .otp {{ font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; letter-spacing: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Schedule Planner</h1>
            </div>
            <div class="content">
                <h2>Welcome to Schedule Planner!</h2>
                <p>Hello {user.name},</p>
                <p>Thank you for registering with Schedule Planner. To complete your registration and access all features, please verify your account using the OTP below:</p>
                
                <div class="otp">{user.otp_secret}</div>
                
                <p>This OTP will expire in 10 minutes. If you did not request this verification, please ignore this email.</p>
                
                <p>Best regards,<br>The Schedule Planner Team</p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Schedule Planner. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html_content)

def send_welcome_email(user):
    """
    Send a welcome email to the user after verification
    
    Args:
        user: User object with email
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Welcome to Schedule Planner!"
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0d6efd; color: white; padding: 10px; text-align: center; }}
            .content {{ padding: 20px; border: 1px solid #ddd; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Schedule Planner</h1>
            </div>
            <div class="content">
                <h2>Account Verified Successfully!</h2>
                <p>Hello {user.name},</p>
                <p>Your account has been successfully verified. You now have full access to all features of Schedule Planner.</p>
                
                <p>Here's what you can do now:</p>
                <ul>
                    <li>Create and manage your class schedule</li>
                    <li>Track your course progress</li>
                    <li>Receive notifications about important deadlines</li>
                    <li>And much more!</li>
                </ul>
                
                <p>If you have any questions or need assistance, feel free to contact us.</p>
                
                <p>Best regards,<br>The Schedule Planner Team</p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Schedule Planner. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html_content)

def send_password_reset_email(user):
    """
    Send a password reset email to the user with OTP
    
    Args:
        user: User object with email and OTP
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    subject = "Reset Your Schedule Planner Password"
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0d6efd; color: white; padding: 10px; text-align: center; }}
            .content {{ padding: 20px; border: 1px solid #ddd; }}
            .otp {{ font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; letter-spacing: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Schedule Planner</h1>
            </div>
            <div class="content">
                <h2>Password Reset Request</h2>
                <p>Hello {user.name},</p>
                <p>We received a request to reset your password. To proceed with the password reset, please use the verification code below:</p>
                
                <div class="otp">{user.otp_secret}</div>
                
                <p>This code will expire in 10 minutes. If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                
                <p>Best regards,<br>The Schedule Planner Team</p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Schedule Planner. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html_content)

def send_event_reminder_email(event):
    """
    Send a reminder email for an upcoming event
    
    Args:
        event: Event object with all details
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Get user and course information
    user = event.student
    course = event.course
    
    # Format event date
    event_date_formatted = event.event_date.strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Determine event type display text
    event_type_display = event.event_type.capitalize()
    
    subject = f"Reminder: {event_type_display} for {course.course_code} Due Tomorrow"
    
    # Prepare the description part based on whether it exists
    description_html = ""
    if event.description:
        description_html = f'<p><strong>Description:</strong> {event.description}</p>'
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #0d6efd; color: white; padding: 10px; text-align: center; }}
            .content {{ padding: 20px; border: 1px solid #ddd; }}
            .event-details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .event-title {{ font-size: 18px; font-weight: bold; color: #0d6efd; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Schedule Planner</h1>
            </div>
            <div class="content">
                <h2>Event Reminder</h2>
                <p>Hello {user.name},</p>
                <p>This is a reminder that you have an upcoming {event.event_type} for your course {course.course_code} due tomorrow.</p>
                
                <div class="event-details">
                    <div class="event-title">{event.title}</div>
                    <p><strong>Type:</strong> {event_type_display}</p>
                    <p><strong>Course:</strong> {course.course_code}</p>
                    <p><strong>Due Date:</strong> {event_date_formatted}</p>
                    {description_html}
                </div>
                
                <p>Log in to your Schedule Planner account to mark this event as completed once you're done.</p>
                
                <p>Best regards,<br>The Schedule Planner Team</p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Schedule Planner. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html_content) 