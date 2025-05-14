from flask import Blueprint, render_template, redirect, url_for, flash, session, request, abort, jsonify, make_response
from flask_login import login_required, current_user
from models.user import User
from models.course import CourseWeight, CourseDirectory
from models.notification import Notification
from models.message import Message
from extensions import db
from sqlalchemy import func, distinct
import uuid
from datetime import datetime, time, timedelta
import pdfkit
import tempfile
import os
import platform
from werkzeug.security import check_password_hash, generate_password_hash
from utils.email_utils import send_email
from models.event import Event, EventType

main_bp = Blueprint('main', __name__)

# Helper functions for admin dashboard
def get_admin_stats():
    """Get statistics for the admin dashboard"""
    stats = {
        'user_count': User.query.filter(User.user_type != 'admin').count(),
        'department_count': db.session.query(func.count(distinct(CourseWeight.department))).scalar(),
        'new_message_count': Message.query.filter_by(is_read=False, parent_id=None).count()
    }
    return stats

# Time slots for the guest routine
def get_time_slots():
    """Get time slots for the routine"""
    return [
        {"id": 1, "label": "08:00 - 09:30", "start": "08:00", "end": "09:30"},
        {"id": 2, "label": "09:30 - 11:00", "start": "09:30", "end": "11:00"},
        {"id": 3, "label": "11:00 - 12:30", "start": "11:00", "end": "12:30"},
        {"id": 4, "label": "12:30 - 14:00", "start": "12:30", "end": "14:00"},
        {"id": 5, "label": "14:00 - 15:30", "start": "14:00", "end": "15:30"},
        {"id": 6, "label": "15:30 - 17:00", "start": "15:30", "end": "17:00"}
    ]

# Days of the week for the guest routine
def get_days():
    """Get days of the week for the routine"""
    return ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

# Guest routine theme colors
def get_themes():
    """Get color themes for the guest routine"""
    return {
        "blue": {
            "name": "Blue Theme",
            "primary": "#0d6efd",
            "secondary": "#cfe2ff",
            "text": "#0a58ca",
            "header": "#0a58ca",
            "header_text": "#ffffff"
        },
        "green": {
            "name": "Green Theme",
            "primary": "#198754",
            "secondary": "#d1e7dd",
            "text": "#0f5132",
            "header": "#0f5132",
            "header_text": "#ffffff"
        },
        "purple": {
            "name": "Purple Theme",
            "primary": "#6f42c1",
            "secondary": "#e2d9f3",
            "text": "#5a23c8",
            "header": "#5a23c8",
            "header_text": "#ffffff"
        }
    }

# Regular routes
@main_bp.route('/')
@main_bp.route('/home')
def home():
    return render_template('main/home.html')

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Redirect admin users to admin dashboard
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get user's courses
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    # Get time slots and days
    time_slots = get_time_slots()
    days = get_days()
    
    # Get user's theme preference or use default
    theme_name = session.get('user_theme', 'blue')
    themes = get_themes()
    theme = themes[theme_name]
    
    # Generate routine grid
    routine = {}
    for day in days:
        routine[day] = {}
        for slot in time_slots:
            routine[day][f"{slot['start']}-{slot['end']}"] = []
    
    # Fill the routine grid with courses
    for course in courses:
        course_days = course.course_day.split(',')
        for day in course_days:
            start_time = course.course_time_start.strftime('%H:%M')
            end_time = course.course_time_end.strftime('%H:%M')
            
            # Only add the course to the exact matching time slot
            for slot in time_slots:
                if start_time == slot['start'] and end_time == slot['end']:
                    routine[day][f"{slot['start']}-{slot['end']}"].append({
                        'course_code': course.course_code,
                        'start_time': start_time,
                        'end_time': end_time
                    })
                    break
    
    # Get upcoming events (placeholder for now)
    events = []
    
    return render_template('dashboard/dashboard.html', 
                          active_page='dashboard',
                          courses=courses,
                          routine=routine,
                          days=days,
                          time_slots=time_slots,
                          theme=theme,
                          events=events)

@main_bp.route('/profile')
@login_required
def profile():
    # Redirect admin users to admin dashboard
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get user's courses
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    # Get time slots and days for course management
    time_slots = get_time_slots()
    days = get_days()
    
    # Get available courses for the user's department
    available_courses = CourseWeight.query.filter_by(department=current_user.department).all()
    
    return render_template('dashboard/profile.html',
                          active_page='profile',
                          courses=courses,
                          days=days,
                          time_slots=time_slots,
                          available_courses=available_courses)

@main_bp.route('/guest')
def guest():
    # Set a session variable to indicate guest user status
    session['guest_user'] = True
    session['guest_theme'] = session.get('guest_theme', 'blue')  # Default theme
    
    # Redirect to the guest routine page
    return redirect(url_for('main.guest_routine_setup'))

@main_bp.route('/guest/routine/setup', methods=['GET', 'POST'])
def guest_routine_setup():
    # Check if user is in guest mode
    if not session.get('guest_user'):
        flash('You need to be in guest mode to access this page.', 'warning')
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        try:
            course_count = int(request.form.get('course_count', 0))
            if course_count < 1 or course_count > 10:
                flash('Please enter a number between 1 and 10.', 'danger')
                return redirect(url_for('main.guest_routine_setup'))
            
            session['guest_course_count'] = course_count
            return redirect(url_for('main.guest_course_input'))
        except ValueError:
            flash('Please enter a valid number.', 'danger')
    
    # Clear any existing course data
    if 'guest_courses' in session:
        session.pop('guest_courses')
    
    # If course count is already set, redirect to course input
    if 'guest_course_count' in session:
        return redirect(url_for('main.guest_course_input'))
    
    return render_template('guest/routine_setup.html')

@main_bp.route('/guest/routine/courses', methods=['GET', 'POST'])
def guest_course_input():
    # Check if user is in guest mode and course count is set
    if not session.get('guest_user') or 'guest_course_count' not in session:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('main.guest_routine_setup'))
    
    course_count = session['guest_course_count']
    days = get_days()
    time_slots = get_time_slots()
    
    if request.method == 'POST':
        courses = []
        # First collect all course data
        for i in range(1, course_count + 1):
            course_code = request.form.get(f'course_code_{i}')
            course_days = request.form.getlist(f'course_days_{i}')
            slot_id = request.form.get(f'course_slot_{i}')
            
            # Validate input
            if not (course_code and course_days and slot_id):
                flash(f'Please fill all fields for Course {i}.', 'danger')
                return redirect(url_for('main.guest_course_input'))
            
            # Find the selected time slot
            selected_slot = next((slot for slot in time_slots if str(slot['id']) == slot_id), None)
            if not selected_slot:
                flash(f'Invalid time slot selected for Course {i}.', 'danger')
                return redirect(url_for('main.guest_course_input'))
            
            courses.append({
                'id': i,
                'course_code': course_code,
                'days': course_days,
                'start_time': selected_slot['start'],
                'end_time': selected_slot['end'],
                'slot_id': slot_id
            })
        
        # Check for scheduling conflicts
        schedule_conflicts = []
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses):
                if i != j:  # Don't compare a course with itself
                    # Find common days between the two courses
                    common_days = set(course1['days']).intersection(set(course2['days']))
                    if common_days and course1['slot_id'] == course2['slot_id']:
                        conflict = {
                            'day': next(iter(common_days)),
                            'time': f"{course1['start_time']} - {course1['end_time']}",
                            'courses': [course1['course_code'], course2['course_code']]
                        }
                        if conflict not in schedule_conflicts:
                            schedule_conflicts.append(conflict)
        
        if schedule_conflicts:
            for conflict in schedule_conflicts:
                flash(f"Schedule conflict: {', '.join(conflict['courses'])} on {conflict['day']} at {conflict['time']}", 'danger')
            return redirect(url_for('main.guest_course_input'))
        
        session['guest_courses'] = courses
        return redirect(url_for('main.guest_routine_view'))
    
    return render_template('guest/course_input.html', course_count=course_count, days=days, time_slots=time_slots)

@main_bp.route('/guest/routine/view')
def guest_routine_view():
    # Check if user is in guest mode and courses are set
    if not session.get('guest_user') or 'guest_courses' not in session:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('main.guest_routine_setup'))
    
    courses = session['guest_courses']
    days = get_days()
    time_slots = get_time_slots()
    theme = session.get('guest_theme', 'blue')
    themes = get_themes()
    
    # Generate routine grid
    routine = {}
    for day in days:
        routine[day] = {}
        for slot in time_slots:
            routine[day][f"{slot['start']}-{slot['end']}"] = []
    
    # Fill the routine grid with courses
    for course in courses:
        for day in course['days']:
            # Only add the course to the exact matching time slot
            for slot in time_slots:
                if course['start_time'] == slot['start'] and course['end_time'] == slot['end']:
                    routine[day][f"{slot['start']}-{slot['end']}"].append({
                        'course_code': course['course_code'],
                        'start_time': course['start_time'],
                        'end_time': course['end_time']
                    })
                    break
    
    return render_template('guest/routine_view.html', 
                          routine=routine, 
                          days=days, 
                          time_slots=time_slots,
                          theme=theme,
                          themes=themes)

@main_bp.route('/guest/theme/<theme>')
def guest_set_theme(theme):
    # Check if user is in guest mode
    if not session.get('guest_user'):
        flash('You need to be in guest mode to access this page.', 'warning')
        return redirect(url_for('main.home'))
    
    themes = get_themes()
    if theme in themes:
        session['guest_theme'] = theme
    
    return redirect(url_for('main.guest_routine_view'))

@main_bp.route('/guest/routine/pdf')
def guest_routine_pdf():
    # Check if user is in guest mode and courses are set
    if not session.get('guest_user') or 'guest_courses' not in session:
        flash('Please start from the beginning.', 'warning')
        return redirect(url_for('main.guest_routine_setup'))
    
    courses = session['guest_courses']
    days = get_days()
    time_slots = get_time_slots()
    theme = session.get('guest_theme', 'blue')
    themes = get_themes()
    
    # Generate routine grid (same as in guest_routine_view)
    routine = {}
    for day in days:
        routine[day] = {}
        for slot in time_slots:
            routine[day][f"{slot['start']}-{slot['end']}"] = []
    
    # Fill the routine grid with courses
    for course in courses:
        for day in course['days']:
            # Only add the course to the exact matching time slot
            for slot in time_slots:
                if course['start_time'] == slot['start'] and course['end_time'] == slot['end']:
                    routine[day][f"{slot['start']}-{slot['end']}"].append({
                        'course_code': course['course_code'],
                        'start_time': course['start_time'],
                        'end_time': course['end_time']
                    })
                    break
    
    # Get the current theme colors
    theme_data = themes[theme]
    
    # Generate static HTML for PDF without template variables in CSS
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Class Routine</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                color: {theme_data['header']};
                text-align: center;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: {theme_data['header']};
                color: {theme_data['header_text']};
            }}
            .time-cell {{
                background-color: {theme_data['secondary']};
                color: {theme_data['text']};
                font-weight: bold;
            }}
            .course-cell {{
                background-color: {theme_data['secondary']};
            }}
            .course {{
                background-color: {theme_data['primary']};
                color: white;
                padding: 5px;
                margin-bottom: 5px;
                border-radius: 3px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Class Routine</h1>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Time</th>
    """
    
    # Add days to the header
    for day in days:
        html += f'<th style="width: 14%;">{day}</th>\n'
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    # Add the time slots and courses
    for slot in time_slots:
        html += f'<tr>\n<td class="time-cell">{slot["start"]} - {slot["end"]}</td>\n'
        
        for day in days:
            slot_key = f"{slot['start']}-{slot['end']}"
            courses_in_slot = routine[day].get(slot_key, [])
            
            if courses_in_slot:
                html += '<td class="course-cell">\n'
                for course in courses_in_slot:
                    html += f"""
                    <div class="course">
                        {course['course_code']}<br>
                        <small>{course['start_time']} - {course['end_time']}</small>
                    </div>
                    """
                html += '</td>\n'
            else:
                html += '<td></td>\n'
                
        html += '</tr>\n'
    
    html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            Generated by Schedule Planner - {theme_data['name']}
        </div>
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    try:
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
        }
        
        # Try to find wkhtmltopdf executable
        config = None
        if platform.system() == 'Windows':
            # Try common locations on Windows
            import os
            wkhtmltopdf_paths = [
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
            ]
            
            for path in wkhtmltopdf_paths:
                if os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
        elif os.environ.get('RENDER'):
            # For Render deployment
            if os.path.exists('/usr/bin/wkhtmltopdf'):
                config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
            elif os.path.exists('/tmp/bin/wkhtmltopdf-wrapper'):
                config = pdfkit.configuration(wkhtmltopdf='/tmp/bin/wkhtmltopdf-wrapper')
            else:
                # Simple fallback for Render free tier
                response = make_response("PDF generation is not available on this deployment. Please run the application locally for PDF features.")
                response.headers['Content-Type'] = 'text/plain'
                return response
        
        if config:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                pdfkit.from_string(html, f.name, options=options, configuration=config)
                pdf_path = f.name
            
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Cleanup the temporary file
            os.unlink(pdf_path)
            
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename=class_routine.pdf'
            return response
        else:
            flash('wkhtmltopdf executable not found. Please install wkhtmltopdf to enable PDF downloads.', 'warning')
            flash('Visit https://wkhtmltopdf.org/downloads.html to download and install.', 'info')
            return redirect(url_for('main.guest_routine_view'))
            
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        flash('To enable PDF downloads, please install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html', 'info')
        return redirect(url_for('main.guest_routine_view'))

@main_bp.route('/guest/reset')
def guest_reset():
    # Reset all guest session data
    for key in list(session.keys()):
        if key.startswith('guest_'):
            session.pop(key)
    
    session['guest_user'] = True
    flash('Your routine has been reset.', 'info')
    return redirect(url_for('main.guest_routine_setup'))

# Admin routes
@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access the admin dashboard.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get admin dashboard statistics
    stats = get_admin_stats()
    
    return render_template('admin/dashboard.html', stats=stats)

@main_bp.route('/admin/inquire-user', methods=['GET', 'POST'])
@login_required
def admin_inquire_user():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = None
    courses = None
    searched = False
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        user = User.query.filter_by(student_id=student_id).first()
        
        if user:
            # Get the user's courses
            courses = CourseDirectory.query.filter_by(student_id=user.id).all()
        
        searched = True
    
    return render_template('admin/inquire_user.html', user=user, courses=courses, searched=searched)

@main_bp.route('/admin/ban-user', methods=['GET', 'POST'])
@login_required
def admin_ban_user():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = None
    course_count = 0
    message_count = 0
    notification_count = 0
    searched = False
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        action = request.form.get('action', 'search')
        
        if action == 'search':
            user = User.query.filter_by(student_id=student_id).first()
            
            if user:
                # Get counts of related data
                course_count = CourseDirectory.query.filter_by(student_id=user.id).count()
                
                # Count messages sent or received by this user
                message_count = Message.query.filter(
                    (Message.sender_id == user.id) | (Message.receiver_id == user.id)
                ).count()
                
                # Count notifications for this user
                notification_count = Notification.query.filter_by(user_id=user.id).count()
            
            searched = True
        
        elif action == 'ban':
            user = User.query.filter_by(student_id=student_id).first()
            
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('main.admin_ban_user'))
            
            if user.user_type == 'admin':
                flash('Admin users cannot be banned.', 'danger')
                return redirect(url_for('main.admin_ban_user'))
            
            try:
                # Delete all related data
                
                # Delete course enrollments
                CourseDirectory.query.filter_by(student_id=user.id).delete()
                
                # Delete notifications
                Notification.query.filter_by(user_id=user.id).delete()
                
                # Delete messages
                Message.query.filter(
                    (Message.sender_id == user.id) | (Message.receiver_id == user.id)
                ).delete()
                
                # Delete the user
                db.session.delete(user)
                db.session.commit()
                
                flash(f'User {student_id} has been permanently banned and all associated data has been deleted.', 'success')
                return redirect(url_for('main.admin_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error banning user: {str(e)}', 'danger')
                return redirect(url_for('main.admin_ban_user'))
    
    return render_template('admin/ban_user.html', user=user, 
                           course_count=course_count, 
                           message_count=message_count, 
                           notification_count=notification_count, 
                           searched=searched)

@main_bp.route('/admin/check-queries')
@main_bp.route('/admin/check-queries/<int:thread_id>')
@login_required
def admin_check_queries(thread_id=None):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get all parent messages (threads)
    threads = Message.query.filter_by(parent_id=None).order_by(Message.created_at.desc()).all()
    
    current_thread = None
    thread_messages = []
    
    if thread_id:
        current_thread = Message.query.get_or_404(thread_id)
        
        # Make sure it's a parent message
        if current_thread.parent_id is not None:
            current_thread = current_thread.parent
        
        # Mark the thread as read if it wasn't
        if not current_thread.is_read:
            current_thread.is_read = True
            db.session.commit()
        
        # Get all messages in the thread
        thread_messages = current_thread.get_thread()
    
    return render_template('admin/check_queries.html', 
                           threads=threads, 
                           current_thread=current_thread, 
                           thread_messages=thread_messages)

@main_bp.route('/admin/reply-query/<int:thread_id>', methods=['POST'])
@login_required
def admin_reply_query(thread_id):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get the thread
    thread = Message.query.get_or_404(thread_id)
    
    # Make sure it's a parent message
    if thread.parent_id is not None:
        thread = thread.parent
    
    action = request.form.get('action')
    
    if action == 'reply':
        reply_content = request.form.get('reply')
        
        if not reply_content:
            flash('Reply cannot be empty.', 'danger')
            return redirect(url_for('main.admin_check_queries', thread_id=thread_id))
        
        # Create the reply
        reply = Message(
            sender_id=current_user.id,
            receiver_id=thread.sender_id,
            subject=f"RE: {thread.subject}",
            content=reply_content,
            parent_id=thread.id
        )
        
        db.session.add(reply)
        
        # Create a notification for the user
        notification_id = f"msg_{thread.id}_{int(datetime.utcnow().timestamp())}"
        notification = Notification(
            user_id=thread.sender_id,
            identifier=notification_id,
            message=f"An admin has replied to your query: {thread.subject}"
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Send email notification
        try:
            user = User.query.get(thread.sender_id)
            if user and user.email:
                email_subject = f"Admin Reply - Query ID: {thread.id}"
                email_body = f"""
                Hello {user.name},
                
                An admin has replied to your query: "{thread.subject}"
                
                Please log in to your account to view the reply.
                
                Regards,
                Schedule Planner Team
                """
                
                send_email(user.email, email_subject, email_body)
        except Exception as e:
            # Log the error but don't stop execution
            print(f"Error sending email: {str(e)}")
        
        flash('Your reply has been sent.', 'success')
    
    elif action == 'close':
        # Close the thread
        thread.is_closed = True
        db.session.commit()
        
        flash('The thread has been closed.', 'info')
    
    elif action == 'reopen':
        # Reopen the thread
        thread.is_closed = False
        db.session.commit()
        
        flash('The thread has been reopened.', 'info')
    
    return redirect(url_for('main.admin_check_queries', thread_id=thread_id))

@main_bp.route('/admin/departments')
@login_required
def admin_departments():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get all departments
    departments = db.session.query(distinct(CourseWeight.department)).order_by(CourseWeight.department).all()
    departments = [dept[0] for dept in departments]
    
    # Count courses in each department
    department_data = []
    for dept_name in departments:
        course_count = CourseWeight.query.filter_by(department=dept_name).count()
        department_data.append({
            'name': dept_name,
            'course_count': course_count
        })
    
    return render_template('admin/departments.html', departments=department_data)

@main_bp.route('/admin/department/add', methods=['GET', 'POST'])
@login_required
def admin_add_department():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    step2 = False
    department_name = None
    course_count = None
    
    if request.method == 'POST' and request.form.get('action') == 'step1':
        department_name = request.form.get('department_name')
        course_count = int(request.form.get('course_count', 0))
        
        if not department_name:
            flash('Department name is required.', 'danger')
            return redirect(url_for('main.admin_add_department'))
        
        if course_count < 1:
            flash('You must add at least one course.', 'danger')
            return redirect(url_for('main.admin_add_department'))
        
        # Check if department already exists
        existing_dept = db.session.query(CourseWeight.department).filter_by(department=department_name).first()
        if existing_dept:
            flash(f'Department "{department_name}" already exists. Please use a different name.', 'danger')
            return redirect(url_for('main.admin_add_department'))
        
        step2 = True
    
    return render_template('admin/add_department.html', 
                           step2=step2, 
                           department_name=department_name, 
                           course_count=course_count)

@main_bp.route('/admin/department/add-courses', methods=['POST'])
@login_required
def admin_add_department_courses():
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    department_name = request.form.get('department_name')
    course_count = int(request.form.get('course_count', 0))
    
    if not department_name or course_count < 1:
        flash('Invalid form data.', 'danger')
        return redirect(url_for('main.admin_departments'))
    
    try:
        # Add each course
        for i in range(1, course_count + 1):
            course_code = request.form.get(f'course_code_{i}')
            course_weight = float(request.form.get(f'course_weight_{i}', 0))
            
            if not course_code or course_weight <= 0:
                continue
            
            # Check if the course already exists
            existing_course = CourseWeight.query.filter_by(course_code=course_code).first()
            if existing_course:
                flash(f'Course {course_code} already exists. It has been skipped.', 'warning')
                continue
            
            # Create the course
            course = CourseWeight(
                course_code=course_code,
                department=department_name,
                weight=course_weight
            )
            
            db.session.add(course)
        
        db.session.commit()
        flash(f'Successfully added courses to the {department_name} department.', 'success')
        return redirect(url_for('main.admin_departments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding courses: {str(e)}', 'danger')
        return redirect(url_for('main.admin_departments'))

@main_bp.route('/admin/department/<department_name>')
@login_required
def admin_view_department(department_name):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get all courses in the department
    courses = CourseWeight.query.filter_by(department=department_name).order_by(CourseWeight.course_code).all()
    
    if not courses:
        flash(f'Department "{department_name}" not found or has no courses.', 'warning')
        return redirect(url_for('main.admin_departments'))
    
    return render_template('admin/view_department.html', department_name=department_name, courses=courses)

@main_bp.route('/admin/department/<department_name>/add-course', methods=['GET', 'POST'])
@login_required
def admin_add_course(department_name):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        course_code = request.form.get('course_code')
        course_weight = float(request.form.get('course_weight', 0))
        
        if not course_code or course_weight <= 0:
            flash('Please provide a valid course code and weight.', 'danger')
            return redirect(url_for('main.admin_add_course', department_name=department_name))
        
        # Check if the course already exists
        existing_course = CourseWeight.query.filter_by(course_code=course_code).first()
        if existing_course:
            flash(f'Course {course_code} already exists.', 'danger')
            return redirect(url_for('main.admin_add_course', department_name=department_name))
        
        try:
            # Create the course
            course = CourseWeight(
                course_code=course_code,
                department=department_name,
                weight=course_weight
            )
            
            db.session.add(course)
            db.session.commit()
            
            flash(f'Successfully added course {course_code} to {department_name}.', 'success')
            return redirect(url_for('main.admin_view_department', department_name=department_name))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'danger')
            return redirect(url_for('main.admin_add_course', department_name=department_name))
    
    return render_template('admin/add_course.html', department_name=department_name)

@main_bp.route('/admin/department/edit-course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_course(course_id):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    course = CourseWeight.query.get_or_404(course_id)
    department_name = course.department
    
    if request.method == 'POST':
        course_code = request.form.get('course_code')
        course_weight = float(request.form.get('course_weight', 0))
        
        if not course_code or course_weight <= 0:
            flash('Please provide a valid course code and weight.', 'danger')
            return redirect(url_for('main.admin_edit_course', course_id=course_id))
        
        # Check if the new course code already exists (if changed)
        if course_code != course.course_code:
            existing_course = CourseWeight.query.filter_by(course_code=course_code).first()
            if existing_course:
                flash(f'Course {course_code} already exists.', 'danger')
                return redirect(url_for('main.admin_edit_course', course_id=course_id))
        
        try:
            # Update the course
            course.course_code = course_code
            course.weight = course_weight
            course.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Successfully updated course {course_code}.', 'success')
            return redirect(url_for('main.admin_view_department', department_name=department_name))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'danger')
            return redirect(url_for('main.admin_edit_course', course_id=course_id))
    
    return render_template('admin/edit_course.html', course=course)

@main_bp.route('/admin/department/delete-course/<int:course_id>', methods=['POST'])
@login_required
def admin_delete_course(course_id):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    course = CourseWeight.query.get_or_404(course_id)
    department_name = course.department
    course_code = course.course_code
    
    try:
        # Check if any students are enrolled in this course
        enrollments = CourseDirectory.query.filter_by(course_code=course_code).count()
        if enrollments > 0:
            flash(f'Cannot delete course {course_code} because {enrollments} students are enrolled in it.', 'danger')
            return redirect(url_for('main.admin_view_department', department_name=department_name))
        
        # Delete the course
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Successfully deleted course {course_code}.', 'success')
        return redirect(url_for('main.admin_view_department', department_name=department_name))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
        return redirect(url_for('main.admin_view_department', department_name=department_name))

@main_bp.route('/admin/department/delete/<department_name>', methods=['GET', 'POST'])
@login_required
def admin_delete_department(department_name):
    # Check if the user is an admin
    if current_user.user_type != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        confirm = request.form.get('confirm')
        
        if confirm != department_name:
            flash('Department name confirmation does not match.', 'danger')
            return redirect(url_for('main.admin_delete_department', department_name=department_name))
        
        try:
            # Check if any students are enrolled in courses from this department
            courses = CourseWeight.query.filter_by(department=department_name).all()
            course_codes = [course.course_code for course in courses]
            
            if course_codes:
                enrollments = CourseDirectory.query.filter(CourseDirectory.course_code.in_(course_codes)).count()
                if enrollments > 0:
                    flash(f'Cannot delete department {department_name} because {enrollments} students are enrolled in its courses.', 'danger')
                    return redirect(url_for('main.admin_departments'))
            
            # Delete all courses in the department
            CourseWeight.query.filter_by(department=department_name).delete()
            db.session.commit()
            
            flash(f'Successfully deleted department {department_name} and all its courses.', 'success')
            return redirect(url_for('main.admin_departments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting department: {str(e)}', 'danger')
            return redirect(url_for('main.admin_departments'))
    
    # Get all courses in the department
    courses = CourseWeight.query.filter_by(department=department_name).all()
    
    if not courses:
        flash(f'Department "{department_name}" not found or has no courses.', 'warning')
        return redirect(url_for('main.admin_departments'))
    
    return render_template('admin/delete_department.html', department_name=department_name, courses=courses)

@main_bp.route('/set-theme/<theme>')
@login_required
def set_theme(theme):
    themes = get_themes()
    if theme in themes:
        session['user_theme'] = theme
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    
    if not name or not email:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Check if email is already in use by another user
    if email != current_user.email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already in use by another user.', 'danger')
            return redirect(url_for('main.profile'))
    
    # Update user information
    current_user.name = name
    current_user.email = email
    db.session.commit()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required.', 'danger')
        return redirect(url_for('main.profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('main.profile'))
    
    if len(new_password) < 8:
        flash('New password must be at least 8 characters long.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Check if current password is correct
    if not check_password_hash(current_user.password, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Update password
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/add-course', methods=['POST'])
@login_required
def add_course():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    course_code = request.form.get('course_code')
    course_days = request.form.getlist('course_days')
    course_time = request.form.get('course_time')
    
    if not course_code or not course_days or not course_time:
        flash('All fields are required.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Get course weight
    course_weight = CourseWeight.query.filter_by(course_code=course_code).first()
    if not course_weight:
        flash('Course not found.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Get time slot
    time_slots = get_time_slots()
    selected_slot = next((slot for slot in time_slots if str(slot['id']) == course_time), None)
    if not selected_slot:
        flash('Invalid time slot.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Check if course is already added
    existing_course = CourseDirectory.query.filter_by(
        student_id=current_user.id,
        course_code=course_code
    ).first()
    
    if existing_course:
        flash(f'Course {course_code} is already in your schedule.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Check for scheduling conflicts
    user_courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    for user_course in user_courses:
        user_course_days = user_course.course_day.split(',')
        common_days = set(course_days).intersection(set(user_course_days))
        
        if common_days:
            start_time = datetime.strptime(selected_slot['start'], '%H:%M').time()
            end_time = datetime.strptime(selected_slot['end'], '%H:%M').time()
            
            if (start_time == user_course.course_time_start and 
                end_time == user_course.course_time_end):
                flash(f"Schedule conflict: {course_code} and {user_course.course_code} on {', '.join(common_days)} at {selected_slot['start']} - {selected_slot['end']}", 'danger')
                return redirect(url_for('main.profile'))
    
    # Create new course
    new_course = CourseDirectory(
        student_id=current_user.id,
        department=current_user.department,
        course_code=course_code,
        actual_weight=course_weight.weight,
        current_weight=course_weight.weight,
        course_day=','.join(course_days),
        course_time_start=datetime.strptime(selected_slot['start'], '%H:%M').time(),
        course_time_end=datetime.strptime(selected_slot['end'], '%H:%M').time()
    )
    
    db.session.add(new_course)
    db.session.commit()
    
    flash(f'Course {course_code} added successfully!', 'success')
    flash(f'Remember to re-optimize your routine to reflect the updated course weights.', 'info')
    return redirect(url_for('main.profile'))

@main_bp.route('/update-course/<int:course_id>', methods=['POST'])
@login_required
def update_course(course_id):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    course = CourseDirectory.query.get_or_404(course_id)
    
    # Ensure the course belongs to the current user
    if course.student_id != current_user.id:
        flash('You do not have permission to update this course.', 'danger')
        return redirect(url_for('main.profile'))
    
    course_weight = float(request.form.get('course_weight', 0))
    course_days = request.form.getlist('course_days')
    course_time = request.form.get('course_time')
    
    if not course_days or not course_time or course_weight <= 0:
        flash('All fields are required and weight must be positive.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Get time slot
    time_slots = get_time_slots()
    selected_slot = next((slot for slot in time_slots if str(slot['id']) == course_time), None)
    if not selected_slot:
        flash('Invalid time slot.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Check for scheduling conflicts with other courses
    user_courses = CourseDirectory.query.filter(
        CourseDirectory.student_id == current_user.id,
        CourseDirectory.id != course_id
    ).all()
    
    for user_course in user_courses:
        user_course_days = user_course.course_day.split(',')
        common_days = set(course_days).intersection(set(user_course_days))
        
        if common_days:
            start_time = datetime.strptime(selected_slot['start'], '%H:%M').time()
            end_time = datetime.strptime(selected_slot['end'], '%H:%M').time()
            
            if (start_time == user_course.course_time_start and 
                end_time == user_course.course_time_end):
                flash(f"Schedule conflict: {course.course_code} and {user_course.course_code} on {', '.join(common_days)} at {selected_slot['start']} - {selected_slot['end']}", 'danger')
                return redirect(url_for('main.profile'))
    
    # Update course
    course.current_weight = course_weight
    course.course_day = ','.join(course_days)
    course.course_time_start = datetime.strptime(selected_slot['start'], '%H:%M').time()
    course.course_time_end = datetime.strptime(selected_slot['end'], '%H:%M').time()
    
    db.session.commit()
    
    flash(f'Course {course.course_code} updated successfully!', 'success')
    flash(f'Remember to re-optimize your routine to reflect the updated course weights.', 'info')
    return redirect(url_for('main.profile'))

@main_bp.route('/delete-course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    course = CourseDirectory.query.get_or_404(course_id)
    
    # Ensure the course belongs to the current user
    if course.student_id != current_user.id:
        flash('You do not have permission to delete this course.', 'danger')
        return redirect(url_for('main.profile'))
    
    course_code = course.course_code
    
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course {course_code} deleted successfully!', 'success')
    flash(f'Remember to re-optimize your routine to reflect the updated course weights.', 'info')
    return redirect(url_for('main.profile'))

@main_bp.route('/download-routine-pdf')
@login_required
def download_routine_pdf():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get user's courses
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    # Get time slots and days
    time_slots = get_time_slots()
    days = get_days()
    
    # Get user's theme preference or use default
    theme_name = session.get('user_theme', 'blue')
    themes = get_themes()
    theme = themes[theme_name]
    
    # Generate routine grid
    routine = {}
    for day in days:
        routine[day] = {}
        for slot in time_slots:
            routine[day][f"{slot['start']}-{slot['end']}"] = []
    
    # Fill the routine grid with courses
    for course in courses:
        course_days = course.course_day.split(',')
        for day in course_days:
            start_time = course.course_time_start.strftime('%H:%M')
            end_time = course.course_time_end.strftime('%H:%M')
            
            # Only add the course to the exact matching time slot
            for slot in time_slots:
                if start_time == slot['start'] and end_time == slot['end']:
                    routine[day][f"{slot['start']}-{slot['end']}"].append({
                        'course_code': course.course_code,
                        'start_time': start_time,
                        'end_time': end_time
                    })
                    break
    
    # Generate static HTML for PDF without template variables in CSS
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Class Routine - {current_user.name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                color: {theme['header']};
                text-align: center;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: {theme['header']};
                color: {theme['header_text']};
            }}
            .time-cell {{
                background-color: {theme['secondary']};
                color: {theme['text']};
                font-weight: bold;
            }}
            .course-cell {{
                background-color: {theme['secondary']};
            }}
            .course {{
                background-color: {theme['primary']};
                color: white;
                padding: 5px;
                margin-bottom: 5px;
                border-radius: 3px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Class Routine - {current_user.name}</h1>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Time</th>
    """
    
    # Add days to the header
    for day in days:
        html += f'<th style="width: 14%;">{day}</th>\n'
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    # Add the time slots and courses
    for slot in time_slots:
        html += f'<tr>\n<td class="time-cell">{slot["start"]} - {slot["end"]}</td>\n'
        
        for day in days:
            slot_key = f"{slot['start']}-{slot['end']}"
            courses_in_slot = routine[day].get(slot_key, [])
            
            if courses_in_slot:
                html += '<td class="course-cell">\n'
                for course in courses_in_slot:
                    html += f"""
                    <div class="course">
                        {course['course_code']}<br>
                        <small>{course['start_time']} - {course['end_time']}</small>
                    </div>
                    """
                html += '</td>\n'
            else:
                html += '<td></td>\n'
                
        html += '</tr>\n'
    
    html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            Generated by Schedule Planner - {current_user.department} - {theme['name']}
        </div>
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    try:
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
        }
        
        # Try to find wkhtmltopdf executable
        config = None
        if platform.system() == 'Windows':
            # Try common locations on Windows
            import os
            wkhtmltopdf_paths = [
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
            ]
            
            for path in wkhtmltopdf_paths:
                if os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
        elif os.environ.get('RENDER'):
            # For Render deployment
            if os.path.exists('/usr/bin/wkhtmltopdf'):
                config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
            elif os.path.exists('/tmp/bin/wkhtmltopdf-wrapper'):
                config = pdfkit.configuration(wkhtmltopdf='/tmp/bin/wkhtmltopdf-wrapper')
            else:
                # Simple fallback for Render free tier
                response = make_response("PDF generation is not available on this deployment. Please run the application locally for PDF features.")
                response.headers['Content-Type'] = 'text/plain'
                return response
        
        if config:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                pdfkit.from_string(html, f.name, options=options, configuration=config)
                pdf_path = f.name
            
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Cleanup the temporary file
            os.unlink(pdf_path)
            
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=class_routine_{current_user.student_id}.pdf'
            return response
        else:
            flash('wkhtmltopdf executable not found. Please install wkhtmltopdf to enable PDF downloads.', 'warning')
            flash('Visit https://wkhtmltopdf.org/downloads.html to download and install.', 'info')
            return redirect(url_for('main.dashboard'))
            
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        flash('To enable PDF downloads, please install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html', 'info')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/optimized-routine')
@login_required
def optimized_routine():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get user's courses
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    if not courses:
        flash('You need to add courses before generating an optimized routine.', 'warning')
        return redirect(url_for('main.profile'))
    
    # Get theme and days
    theme_name = session.get('user_theme', 'blue')
    themes = get_themes()
    theme = themes[theme_name]
    days = get_days()
    
    # Get current algorithm and dinner hour from session, or use defaults
    algorithm = session.get('optimization_algorithm', 'genetic')
    dinner_hour = session.get('dinner_hour', 8)
    
    # Get optimized routine from session if it exists
    optimized_routine = session.get('optimized_routine', {})
    fitness_score = session.get('fitness_score')
    
    # Get upcoming events for the user
    upcoming_events = Event.query.filter_by(
        student_id=current_user.id,
        is_completed=False,
        is_expired=False
    ).order_by(Event.event_date).limit(5).all()
    
    return render_template('dashboard/optimized_routine.html',
                          active_page='optimized',
                          courses=courses,
                          days=days,
                          theme=theme,
                          theme_name=theme_name,
                          algorithm=algorithm,
                          dinner_hour=dinner_hour,
                          optimized_routine=optimized_routine,
                          fitness_score=fitness_score,
                          upcoming_events=upcoming_events)

@main_bp.route('/generate-optimized-routine', methods=['POST'])
@login_required
def generate_optimized_routine():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get form data
    algorithm = request.form.get('algorithm', 'genetic')
    dinner_hour = int(request.form.get('dinner_hour', 8))
    
    # Save preferences to session
    session['optimization_algorithm'] = algorithm
    session['dinner_hour'] = dinner_hour
    
    # Get a FRESH copy of user's courses directly from database to ensure up-to-date weights
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    if not courses:
        flash('You need to add courses before generating an optimized routine.', 'warning')
        return redirect(url_for('main.optimized_routine'))
    
    # Get the days to optimize (starting from current day)
    days = get_days()
    
    try:
        # Choose the appropriate optimizer
        if algorithm == 'genetic':
            from utils.genetic_optimizer import GeneticOptimizer
            optimizer = GeneticOptimizer(courses, dinner_hour=dinner_hour, days=days)
            optimized_routine, fitness_score = optimizer.optimize(population_size=50, generations=40)
        else:  # ant_colony
            from utils.ant_colony_optimizer import AntColonyOptimizer
            optimizer = AntColonyOptimizer(courses, dinner_hour=dinner_hour, days=days)
            optimized_routine, fitness_score = optimizer.optimize(iterations=30)
        
        # Store the result in session
        session['optimized_routine'] = optimized_routine
        session['fitness_score'] = fitness_score
        
        flash(f'Optimized routine generated successfully using {algorithm.replace("_", " ").title()} algorithm!', 'success')
    except Exception as e:
        flash(f'Error generating optimized routine: {str(e)}', 'danger')
    
    return redirect(url_for('main.optimized_routine'))

@main_bp.route('/download-optimized-routine-pdf')
@login_required
def download_optimized_routine_pdf():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get optimized routine from session
    optimized_routine = session.get('optimized_routine', {})
    
    if not optimized_routine:
        flash('No optimized routine to download. Please generate one first.', 'warning')
        return redirect(url_for('main.optimized_routine'))
    
    # Get theme and days
    theme_name = session.get('user_theme', 'blue')
    themes = get_themes()
    theme = themes[theme_name]
    days = get_days()
    
    # Get dinner hour
    dinner_hour = session.get('dinner_hour', 8)
    
    # Generate static HTML for PDF
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Optimized Study Routine - {current_user.name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                color: {theme['header']};
                text-align: center;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 30px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: {theme['header']};
                color: {theme['header_text']};
            }}
            .time-cell {{
                background-color: {theme['secondary']};
                color: {theme['text']};
                font-weight: bold;
            }}
            .course-cell {{
                background-color: {theme['primary']};
                color: white;
                padding: 5px;
                border-radius: 3px;
            }}
            .dinner-cell {{
                background-color: #fff3cd;
                color: #664d03;
                font-weight: 500;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Optimized Study Routine - {current_user.name}</h1>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 16%;">Time</th>
    """
    
    # Add days to the header
    for day in days:
        html += f'<th style="width: 14%;">{day}</th>\n'
    
    html += """
                </tr>
            </thead>
            <tbody>
    """
    
    # Add the time slots and courses
    for hour in range(6, 12):
        html += f'<tr>\n<td class="time-cell">{hour}:00 PM - {hour+1 if hour < 11 else 12}:00 {"PM" if hour < 11 else "AM"}</td>\n'
        
        for day in days:
            if hour == dinner_hour:
                html += '<td class="dinner-cell">Dinner Time</td>\n'
            else:
                slot_key = f"{day}_{hour}"
                course_code = optimized_routine.get(slot_key, '')
                
                if course_code:
                    html += f'<td><div class="course-cell">{course_code}</div></td>\n'
                else:
                    html += '<td></td>\n'
                
        html += '</tr>\n'
    
    html += f"""
            </tbody>
        </table>
        
        <div class="footer">
            Generated by Schedule Planner - {current_user.department} - {theme['name']}
        </div>
    </body>
    </html>
    """
    
    # Convert HTML to PDF using the same code as in download_routine_pdf
    try:
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
        }
        
        # Try to find wkhtmltopdf executable
        config = None
        if platform.system() == 'Windows':
            # Try common locations on Windows
            import os
            wkhtmltopdf_paths = [
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
            ]
            
            for path in wkhtmltopdf_paths:
                if os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
        elif os.environ.get('RENDER'):
            # For Render deployment
            if os.path.exists('/usr/bin/wkhtmltopdf'):
                config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
            elif os.path.exists('/tmp/bin/wkhtmltopdf-wrapper'):
                config = pdfkit.configuration(wkhtmltopdf='/tmp/bin/wkhtmltopdf-wrapper')
            else:
                # Simple fallback for Render free tier
                response = make_response("PDF generation is not available on this deployment. Please run the application locally for PDF features.")
                response.headers['Content-Type'] = 'text/plain'
                return response
        
        if config:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                pdfkit.from_string(html, f.name, options=options, configuration=config)
                pdf_path = f.name
            
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Cleanup the temporary file
            os.unlink(pdf_path)
            
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=optimized_routine_{current_user.student_id}.pdf'
            return response
        else:
            flash('wkhtmltopdf executable not found. Please install wkhtmltopdf to enable PDF downloads.', 'warning')
            flash('Visit https://wkhtmltopdf.org/downloads.html to download and install.', 'info')
            return redirect(url_for('main.optimized_routine'))
            
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        flash('To enable PDF downloads, please install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html', 'info')
        return redirect(url_for('main.optimized_routine'))

@main_bp.route('/add-event')
@login_required
def add_event():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Mark any expired events
    Event.mark_expired_events()
    
    # Get user's courses
    courses = CourseDirectory.query.filter_by(student_id=current_user.id).all()
    
    if not courses:
        flash('You need to add courses before creating events.', 'warning')
        return redirect(url_for('main.profile'))
    
    # Get active (not completed, not expired) events
    active_events = Event.query.filter_by(
        student_id=current_user.id,
        is_completed=False,
        is_expired=False
    ).order_by(Event.event_date).all()
    
    # Get completed events
    completed_events = Event.query.filter_by(
        student_id=current_user.id,
        is_completed=True
    ).order_by(Event.event_date.desc()).limit(5).all()
    
    # Get expired events
    expired_events = Event.query.filter_by(
        student_id=current_user.id,
        is_expired=True
    ).order_by(Event.event_date.desc()).limit(5).all()
    
    return render_template('dashboard/add_event.html',
                          active_page='add_event',
                          courses=courses,
                          active_events=active_events,
                          completed_events=completed_events,
                          expired_events=expired_events)

@main_bp.route('/save-event', methods=['POST'])
@login_required
def save_event():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get form data
    course_id = request.form.get('course_id')
    event_type = request.form.get('event_type')
    title = request.form.get('title')
    description = request.form.get('description', '')
    event_date_str = request.form.get('event_date')
    
    # Validate inputs
    if not all([course_id, event_type, title, event_date_str]):
        flash('Please fill all required fields.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Parse event date
    try:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Check if the course belongs to the user
    course = CourseDirectory.query.filter_by(id=course_id, student_id=current_user.id).first()
    if not course:
        flash('Course not found or access denied.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Check if the event date is in the future
    now = datetime.utcnow()
    if event_date < now:
        flash('Event date must be in the future.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Check if the event date is within the allowed range
    max_days_before = EventType.get_max_days_before(event_type)
    max_future_date = now + timedelta(days=max_days_before)
    
    if event_date > max_future_date:
        flash(f'{event_type.capitalize()} can only be added up to {max_days_before} days before the event.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Create the event
    event = Event(
        student_id=current_user.id,
        course_directory_id=course.id,
        event_type=event_type,
        title=title,
        description=description,
        event_date=event_date
    )
    
    # Update course weight based on event type
    weight_modifier = EventType.get_weight_modifier(event_type)
    course.current_weight += weight_modifier
    
    # Save to database
    db.session.add(event)
    db.session.commit()
    
    flash(f'{event_type.capitalize()} event added successfully! Course weight updated.', 'success')
    flash(f'Remember to re-optimize your routine to reflect the updated course weights.', 'info')
    return redirect(url_for('main.add_event'))

@main_bp.route('/complete-event/<int:event_id>', methods=['POST'])
@login_required
def complete_event(event_id):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get the event
    event = Event.query.filter_by(id=event_id, student_id=current_user.id).first()
    
    if not event:
        flash('Event not found or access denied.', 'danger')
        return redirect(url_for('main.add_event'))
    
    # Check if the event is already completed or expired
    if event.is_completed:
        flash('This event is already completed.', 'warning')
        return redirect(url_for('main.add_event'))
    
    if event.is_expired:
        flash('This event has expired and cannot be completed.', 'warning')
        return redirect(url_for('main.add_event'))
    
    # Mark the event as completed (this also updates the course weight)
    event.mark_as_completed()
    
    # Update event timestamp
    event.updated_at = datetime.utcnow()
    
    # Save to database
    db.session.commit()
    
    # Create a notification
    notification_id = f"event_complete_{event.id}_{int(datetime.utcnow().timestamp())}"
    notification = Notification(
        user_id=current_user.id,
        identifier=notification_id,
        message=f"You've completed: {event.title} ({event.event_type}) for {event.course.course_code}!"
    )
    
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Event marked as completed! Course weight has been reduced.', 'success')
    flash(f'Remember to re-optimize your routine to reflect the updated course weights.', 'info')
    return redirect(url_for('main.add_event'))

@main_bp.route('/notifications')
@login_required
def notifications():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get user's notifications
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Remove expired notifications
    Notification.remove_expired()
    
    return render_template('dashboard/notifications.html', 
                           active_page='notifications',
                           notifications=notifications)

@main_bp.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    notification = Notification.query.get_or_404(notification_id)
    
    # Make sure the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('You do not have permission to mark this notification as read.', 'danger')
        return redirect(url_for('main.notifications'))
    
    notification.is_read = True
    db.session.commit()
    
    flash('Notification marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/mark-all-notifications-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Mark all user's notifications as read
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    
    for notification in notifications:
        notification.is_read = True
    
    db.session.commit()
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/contact-admin')
@main_bp.route('/contact-admin/<int:thread_id>')
@login_required
def contact_admin(thread_id=None):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get all parent messages (threads) where the user is either sender or receiver
    threads = Message.query.filter(
        (Message.parent_id == None) &
        ((Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.desc()).all()
    
    current_thread = None
    thread_messages = []
    
    if thread_id:
        current_thread = Message.query.get_or_404(thread_id)
        
        # Make sure it's a parent message
        if current_thread.parent_id is not None:
            current_thread = current_thread.parent
        
        # Make sure the user is part of this thread
        if current_thread.sender_id != current_user.id and current_thread.receiver_id != current_user.id:
            flash('You do not have permission to view this thread.', 'danger')
            return redirect(url_for('main.contact_admin'))
        
        # Mark the thread as read if user is the receiver and it wasn't read
        if current_thread.receiver_id == current_user.id and not current_thread.is_read:
            current_thread.is_read = True
            db.session.commit()
        
        # Get all messages in the thread
        thread_messages = current_thread.get_thread()
    
    return render_template('dashboard/contact_admin.html', 
                           active_page='contact',
                           threads=threads, 
                           current_thread=current_thread, 
                           thread_messages=thread_messages)

@main_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    subject = request.form.get('subject')
    message_content = request.form.get('message')
    
    if not subject or not message_content:
        flash('Please fill in all fields.', 'danger')
        return redirect(url_for('main.contact_admin'))
    
    # Find an admin to send the message to (first admin in the system)
    admin = User.query.filter_by(user_type='admin').first()
    
    if not admin:
        flash('No admin found in the system. Please try again later.', 'danger')
        return redirect(url_for('main.contact_admin'))
    
    # Create the message
    message = Message(
        sender_id=current_user.id,
        receiver_id=admin.id,
        subject=subject,
        content=message_content
    )
    
    db.session.add(message)
    db.session.commit()
    
    flash('Your message has been sent.', 'success')
    return redirect(url_for('main.contact_admin', thread_id=message.id))

@main_bp.route('/reply-message/<int:thread_id>', methods=['POST'])
@login_required
def reply_message(thread_id):
    if current_user.user_type == 'admin':
        return redirect(url_for('main.admin_dashboard'))
    
    # Get the thread
    thread = Message.query.get_or_404(thread_id)
    
    # Make sure it's a parent message
    if thread.parent_id is not None:
        thread = thread.parent
    
    # Make sure the user is part of this thread
    if thread.sender_id != current_user.id and thread.receiver_id != current_user.id:
        flash('You do not have permission to reply to this thread.', 'danger')
        return redirect(url_for('main.contact_admin'))
    
    # Make sure the thread is not closed
    if thread.is_closed:
        flash('This thread is closed. You cannot reply to it.', 'danger')
        return redirect(url_for('main.contact_admin', thread_id=thread_id))
    
    action = request.form.get('action')
    
    if action == 'reply':
        reply_content = request.form.get('reply')
        
        if not reply_content:
            flash('Reply cannot be empty.', 'danger')
            return redirect(url_for('main.contact_admin', thread_id=thread_id))
        
        # Determine the receiver (if current user is sender, then receiver is the same as thread receiver)
        receiver_id = thread.receiver_id if thread.sender_id == current_user.id else thread.sender_id
        
        # Create the reply
        reply = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            subject=f"RE: {thread.subject}",
            content=reply_content,
            parent_id=thread.id
        )
        
        db.session.add(reply)
        
        # Create a notification for the admin if the receiver is an admin
        receiver = User.query.get(receiver_id)
        if receiver and receiver.user_type == 'admin':
            notification_id = f"msg_{thread.id}_{int(datetime.utcnow().timestamp())}"
            notification = Notification(
                user_id=receiver_id,
                identifier=notification_id,
                message=f"User {current_user.name} replied to: {thread.subject}"
            )
            db.session.add(notification)
        
        db.session.commit()
        
        flash('Your reply has been sent.', 'success')
    
    elif action == 'close':
        # Close the thread
        thread.is_closed = True
        db.session.commit()
        
        flash('The thread has been closed.', 'info')
    
    return redirect(url_for('main.contact_admin', thread_id=thread_id)) 