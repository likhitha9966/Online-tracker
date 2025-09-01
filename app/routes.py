from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .forms import LoginForm, RegistrationForm, TaskForm
from .models import User, Task, TimeLog
from datetime import datetime, timedelta
from sqlalchemy import func
import io
import csv

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember.data)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html', title='Sign In', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(title=form.title.data, 
                    description=form.description.data, 
                    author=current_user)
        db.session.add(task)
        db.session.commit()
        flash('Your task has been created!', 'success')
        return redirect(url_for('main.dashboard'))
    
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.is_completed, Task.date_posted.desc()).all()
    return render_template('dashboard.html', 
                           name=current_user.username, 
                           form=form, 
                           tasks=tasks)

@main.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    db.session.delete(task)
    db.session.commit()
    flash('Your task has been deleted!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/task/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle_complete(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        abort(403)
    task.is_completed = not task.is_completed
    db.session.commit()
    flash('Task status has been updated!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/task/log_time/<int:task_id>', methods=['POST'])
@login_required
def log_time(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        return jsonify({'status': 'error', 'message': 'Forbidden'}), 403
    data = request.get_json()
    duration = data.get('duration')
    if duration and duration > 0:
        new_log = TimeLog(task_id=task.id, duration=duration, end_time=datetime.utcnow())
        db.session.add(new_log)
        task.total_time_spent = (task.total_time_spent or 0) + duration
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Time logged successfully.'})
    return jsonify({'status': 'error', 'message': 'Invalid duration.'}), 400

@main.route('/api/chart_data')
@login_required
def chart_data():
    seven_days_ago = datetime.utcnow() - timedelta(days=6)
    user_task_ids = [task.id for task in current_user.tasks]
    if not user_task_ids:
        return jsonify({'labels': [], 'data': []})
        
    logs_by_day = db.session.query(
        func.date(TimeLog.end_time).label('date'),
        func.sum(TimeLog.duration).label('total_duration')
    ).filter(
        TimeLog.task_id.in_(user_task_ids),
        TimeLog.end_time >= seven_days_ago
    ).group_by(func.date(TimeLog.end_time)).order_by(func.date(TimeLog.end_time)).all()
    
    time_data = { (datetime.utcnow().date() - timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7) }

    for log in logs_by_day:
        time_data[log.date] = log.total_duration / 60 

    sorted_dates = sorted(time_data.keys())
    labels = [datetime.strptime(d, '%Y-%m-%d').strftime('%a, %b %d') for d in sorted_dates]
    data = [time_data[d] for d in sorted_dates]
    
    return jsonify({'labels': labels, 'data': data})

@main.route('/export/csv')
@login_required
def export_csv():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.date_posted.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['Task ID', 'Title', 'Description', 'Status', 'Date Created', 'Total Time Spent (Minutes)']
    writer.writerow(header)
    for task in tasks:
        status = 'Completed' if task.is_completed else 'Incomplete'
        time_in_minutes = round((task.total_time_spent or 0) / 60, 2)
        row = [task.id, task.title, task.description, status, task.date_posted.strftime('%Y-%m-%d %H:%M:%S'), time_in_minutes]
        writer.writerow(row)
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=task_report.csv"}
    )