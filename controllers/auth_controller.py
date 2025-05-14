from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
from models.course import CourseWeight, CourseDirectory
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, distinct
from utils.email_utils import send_verification_email, send_welcome_email, send_password_reset_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    # Get all departments from the database
    departments = db.session.query(distinct(CourseWeight.department)).order_by(CourseWeight.department).all()
    departments = [dept[0] for dept in departments]
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        student_id = request.form.get('student_id')
        department = request.form.get('department')
        date_of_birth = request.form.get('date_of_birth')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if student_id already exists
        user = User.query.filter_by(student_id=student_id).first()
        if user:
            flash('Student ID already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Parse date of birth
        try:
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            student_id=student_id,
            department=department,
            date_of_birth=dob,
            password=hashed_password,
            is_verified=False,
            user_type='regular'  # Default user type is regular
        )
        
        # Generate OTP
        otp = new_user.generate_otp()
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send verification email
        send_verification_email(new_user)
        
        # Store user ID in session for verification
        session['verification_user_id'] = new_user.id
        
        flash('Account created successfully! Please check your email for the verification code.', 'success')
        return redirect(url_for('auth.verify'))
    
    return render_template('auth/register.html', departments=departments)

@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    # Check if there's a user to verify
    user_id = session.get('verification_user_id')
    if not user_id:
        flash('No verification in progress. Please register first.', 'warning')
        return redirect(url_for('auth.register'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please register again.', 'danger')
        session.pop('verification_user_id', None)
        return redirect(url_for('auth.register'))
    
    if user.is_verified:
        flash('Your account is already verified. Please login.', 'info')
        session.pop('verification_user_id', None)
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        # Check if OTP is valid
        if not user.otp_secret or not user.otp_created_at:
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.verify'))
        
        # Check if OTP is expired (10 minutes)
        if datetime.utcnow() > user.otp_created_at + timedelta(minutes=10):
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.verify'))
        
        # Check if OTP is correct
        if user.otp_secret != otp:
            user.otp_attempts += 1
            db.session.commit()
            
            # Too many attempts
            if user.otp_attempts >= 3:
                flash('Too many incorrect attempts. Please request a new OTP.', 'danger')
                return redirect(url_for('auth.resend_otp'))
            
            flash('Incorrect OTP. Please try again.', 'danger')
            return redirect(url_for('auth.verify'))
        
        # OTP is correct, verify the user
        user.is_verified = True
        user.otp_secret = None
        user.otp_created_at = None
        user.otp_attempts = 0
        db.session.commit()
        
        # Send welcome email
        send_welcome_email(user)
        
        # Remove verification session
        session.pop('verification_user_id', None)
        
        # Store user ID for course setup
        session['course_setup_user_id'] = user.id
        
        flash('Your account has been verified successfully!', 'success')
        return redirect(url_for('auth.setup_courses'))
    
    return render_template('auth/verify.html', email=user.email)

@auth_bp.route('/resend-otp')
def resend_otp():
    # Check if there's a user to verify
    user_id = session.get('verification_user_id')
    if not user_id:
        flash('No verification in progress. Please register first.', 'warning')
        return redirect(url_for('auth.register'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please register again.', 'danger')
        session.pop('verification_user_id', None)
        return redirect(url_for('auth.register'))
    
    # Generate new OTP
    otp = user.generate_otp()
    db.session.commit()
    
    # Send verification email
    send_verification_email(user)
    
    flash('A new verification code has been sent to your email.', 'info')
    return redirect(url_for('auth.verify'))

@auth_bp.route('/setup-courses', methods=['GET', 'POST'])
def setup_courses():
    # Check if there's a user for course setup
    user_id = session.get('course_setup_user_id')
    if not user_id:
        flash('Please verify your account first.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please register again.', 'danger')
        session.pop('course_setup_user_id', None)
        return redirect(url_for('auth.register'))
    
    # Get time slots
    from controllers.main_controller import get_time_slots, get_days
    time_slots = get_time_slots()
    days = get_days()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'set_count':
            course_count = int(request.form.get('course_count', 0))
            if course_count < 1 or course_count > 10:
                flash('Please enter a number between 1 and 10.', 'danger')
                return redirect(url_for('auth.setup_courses'))
            
            session['course_count'] = course_count
            
            # Get courses for the user's department
            department_courses = CourseWeight.query.filter_by(department=user.department).all()
            return render_template('auth/setup_courses.html', 
                                  user=user, 
                                  course_count=course_count, 
                                  department_courses=department_courses,
                                  time_slots=time_slots,
                                  days=days,
                                  show_courses=True)
        
        elif action == 'save_courses':
            course_count = session.get('course_count', 0)
            if course_count < 1:
                flash('Please set the number of courses first.', 'danger')
                return redirect(url_for('auth.setup_courses'))
            
            # First, collect all course data for conflict checking
            course_data = []
            for i in range(1, course_count + 1):
                course_code = request.form.get(f'course_code_{i}')
                course_days = request.form.getlist(f'course_days_{i}')
                slot_id = request.form.get(f'course_slot_{i}')
                
                if not course_code or not course_days or not slot_id:
                    continue
                
                # Get course weight
                course_weight = CourseWeight.query.filter_by(course_code=course_code).first()
                if not course_weight:
                    continue
                
                # Find the selected time slot
                selected_slot = next((slot for slot in time_slots if str(slot['id']) == slot_id), None)
                if not selected_slot:
                    continue
                
                course_data.append({
                    'course_code': course_code,
                    'days': course_days,
                    'slot_id': slot_id,
                    'start_time': selected_slot['start'],
                    'end_time': selected_slot['end'],
                    'weight': course_weight.weight
                })
            
            # Check for scheduling conflicts
            has_conflict = False
            for i, course1 in enumerate(course_data):
                for j, course2 in enumerate(course_data):
                    if i != j:  # Don't compare a course with itself
                        # Find common days between the two courses
                        common_days = set(course1['days']).intersection(set(course2['days']))
                        if common_days and course1['slot_id'] == course2['slot_id']:
                            flash(f"Schedule conflict: {course1['course_code']} and {course2['course_code']} on {', '.join(common_days)} at {course1['start_time']} - {course1['end_time']}", 'danger')
                            has_conflict = True
            
            if has_conflict:
                # Get courses for the user's department to redisplay the form
                department_courses = CourseWeight.query.filter_by(department=user.department).all()
                return render_template('auth/setup_courses.html', 
                                      user=user, 
                                      course_count=course_count, 
                                      department_courses=department_courses,
                                      time_slots=time_slots,
                                      days=days,
                                      show_courses=True)
            
            # No conflicts, proceed to save courses
            for course in course_data:
                # Create course directory entry
                course_dir = CourseDirectory(
                    student_id=user.id,
                    department=user.department,
                    course_code=course['course_code'],
                    actual_weight=course['weight'],
                    current_weight=course['weight'],
                    course_day=','.join(course['days']),
                    course_time_start=datetime.strptime(course['start_time'], '%H:%M').time(),
                    course_time_end=datetime.strptime(course['end_time'], '%H:%M').time()
                )
                
                db.session.add(course_dir)
            
            db.session.commit()
            
            # Clear session data
            session.pop('course_setup_user_id', None)
            session.pop('course_count', None)
            
            # Log in the user
            login_user(user)
            
            flash('Your courses have been set up successfully!', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('auth/setup_courses.html', user=user, show_courses=False)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.user_type == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(student_id=student_id).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_verified and user.user_type != 'admin':
                # Store user ID for verification
                session['verification_user_id'] = user.id
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('auth.verify'))
                
            login_user(user, remember=remember)
            
            # Redirect based on user type
            if user.user_type == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            else:
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Login unsuccessful. Please check your Student ID and password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        
        # Find the user by student ID
        user = User.query.filter_by(student_id=student_id).first()
        
        if not user:
            flash('No account found with that Student ID.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Generate OTP
        otp = user.generate_otp()
        db.session.commit()
        
        # Send password reset email
        send_password_reset_email(user)
        
        # Store user ID in session for verification
        session['reset_user_id'] = user.id
        
        flash('A password reset code has been sent to your email.', 'success')
        return redirect(url_for('auth.reset_verify'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-verify', methods=['GET', 'POST'])
def reset_verify():
    # Check if there's a user for password reset
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('No password reset in progress. Please start over.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please try again.', 'danger')
        session.pop('reset_user_id', None)
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        # Check if OTP is valid
        if not user.otp_secret or not user.otp_created_at:
            flash('Reset code has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Check if OTP is expired (10 minutes)
        if datetime.utcnow() > user.otp_created_at + timedelta(minutes=10):
            flash('Reset code has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        # Check if OTP is correct
        if user.otp_secret != otp:
            user.otp_attempts += 1
            db.session.commit()
            
            # Too many attempts
            if user.otp_attempts >= 3:
                flash('Too many incorrect attempts. Please request a new reset code.', 'danger')
                return redirect(url_for('auth.forgot_password'))
            
            flash('Incorrect reset code. Please try again.', 'danger')
            return redirect(url_for('auth.reset_verify'))
        
        # OTP is correct, allow password reset
        session['reset_verified'] = True
        
        flash('Reset code verified. Please set a new password.', 'success')
        return redirect(url_for('auth.reset_password'))
    
    return render_template('auth/reset_verify.html', email=user.email)

@auth_bp.route('/resend-reset-otp')
def resend_reset_otp():
    # Check if there's a user for password reset
    user_id = session.get('reset_user_id')
    if not user_id:
        flash('No password reset in progress. Please start over.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please try again.', 'danger')
        session.pop('reset_user_id', None)
        return redirect(url_for('auth.forgot_password'))
    
    # Generate new OTP
    otp = user.generate_otp()
    db.session.commit()
    
    # Send password reset email
    send_password_reset_email(user)
    
    flash('A new reset code has been sent to your email.', 'info')
    return redirect(url_for('auth.reset_verify'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Check if the user is verified for password reset
    user_id = session.get('reset_user_id')
    reset_verified = session.get('reset_verified')
    
    if not user_id or not reset_verified:
        flash('Please verify your reset code first.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found. Please try again.', 'danger')
        session.pop('reset_user_id', None)
        session.pop('reset_verified', None)
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.reset_password'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('auth.reset_password'))
        
        # Update password
        user.password = generate_password_hash(password)
        user.otp_secret = None
        user.otp_created_at = None
        user.otp_attempts = 0
        db.session.commit()
        
        # Clear session data
        session.pop('reset_user_id', None)
        session.pop('reset_verified', None)
        
        flash('Your password has been reset successfully! Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html') 