from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change in production

DB_PATH = os.path.join(os.path.dirname(__file__), 'college_event.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Home page
@app.route('/')
def home():
    db = get_db()
    # Get upcoming events (limit to 3 for display)
    events = db.execute('SELECT * FROM events ORDER BY date LIMIT 3').fetchall()
    db.close()
    return render_template('index.html', events=events)

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        department = request.form['department']
        year = request.form['year']
        mobile = request.form['mobile']

        # Validation
        if not name or not username or not password or not department or not year or not mobile:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

        db = get_db()
        try:
            db.execute(
                'INSERT INTO students (name, username, password, department, year, mobile) VALUES (?, ?, ?, ?, ?, ?)',
                (name, username, hashed_pw, department, year, mobile)
            )
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
        finally:
            db.close()

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        student = db.execute('SELECT * FROM students WHERE username = ?', (username,)).fetchone()
        db.close()

        if student and check_password_hash(student['password'], password):
            session['student_id'] = student['student_id']
            session['username'] = student['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    db = get_db()

    # Total events
    total_events = db.execute('SELECT COUNT(*) FROM events').fetchone()[0]

    # Student's registrations count
    my_reg_count = db.execute(
        'SELECT COUNT(*) FROM registrations WHERE student_id = ? AND status = "Registered"',
        (student_id,)
    ).fetchone()[0]

    # Upcoming events (for display)
    upcoming_events = db.execute('SELECT * FROM events ORDER BY date LIMIT 3').fetchall()

    db.close()
    return render_template('dashboard.html',
                           total_events=total_events,
                           my_reg_count=my_reg_count,
                           upcoming_events=upcoming_events)

# Events listing
@app.route('/events')
def events():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    events = db.execute('SELECT * FROM events ORDER BY date').fetchall()
    db.close()
    return render_template('events.html', events=events)

# Event details
@app.route('/events/<int:event_id>')
def event_details(event_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    event = db.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()

    # Check if student is registered for this event
    registration = db.execute(
        'SELECT * FROM registrations WHERE student_id = ? AND event_id = ?',
        (session['student_id'], event_id)
    ).fetchone()

    db.close()
    return render_template('event_details.html', event=event, registration=registration)

# Event registration
@app.route('/events/<int:event_id>/register', methods=['POST'])
def register_event(event_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    db = get_db()

    # Check if event exists
    event = db.execute('SELECT * FROM events WHERE event_id = ?', (event_id,)).fetchone()
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('events'))

    # Check existing registration
    existing = db.execute(
        'SELECT * FROM registrations WHERE student_id = ? AND event_id = ?',
        (student_id, event_id)
    ).fetchone()

    if existing:
        if existing['status'] == 'Cancelled':
            # Re-register by updating status
            db.execute(
                'UPDATE registrations SET status = "Registered", registration_date = CURRENT_TIMESTAMP WHERE registration_id = ?',
                (existing['registration_id'],)
            )
            db.commit()
            flash('Registration restored successfully!', 'success')
            # Create notification
            db.execute(
                'INSERT INTO notifications (student_id, event_id, message) VALUES (?, ?, ?)',
                (student_id, event_id, f'You have successfully registered for {event["event_name"]}.')
            )
            db.commit()
        else:
            flash('You are already registered for this event', 'error')
    else:
        # New registration
        db.execute(
            'INSERT INTO registrations (student_id, event_id) VALUES (?, ?)',
            (student_id, event_id)
        )
        db.commit()
        flash('Registration successful!', 'success')
        # Create notification
        db.execute(
            'INSERT INTO notifications (student_id, event_id, message) VALUES (?, ?, ?)',
            (student_id, event_id, f'You have successfully registered for {event["event_name"]}.')
        )
        db.commit()

    db.close()
    return redirect(url_for('event_details', event_id=event_id))

# My registrations
@app.route('/my-registrations')
def my_registrations():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    db = get_db()
    registrations = db.execute('''
        SELECT r.registration_id, r.status, r.registration_date, e.event_name, e.date, e.time, e.venue
        FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        WHERE r.student_id = ?
        ORDER BY r.registration_date DESC
    ''', (student_id,)).fetchall()
    db.close()
    return render_template('my_registrations.html', registrations=registrations)

# Cancel registration
@app.route('/registration/<int:registration_id>/cancel', methods=['POST'])
def cancel_registration(registration_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    db = get_db()

    # Verify ownership
    registration = db.execute(
        'SELECT r.*, e.event_name FROM registrations r JOIN events e ON r.event_id = e.event_id WHERE r.registration_id = ? AND r.student_id = ?',
        (registration_id, student_id)
    ).fetchone()

    if not registration:
        flash('Registration not found or unauthorized', 'error')
        return redirect(url_for('my_registrations'))

    if registration['status'] == 'Cancelled':
        flash('Registration already cancelled', 'info')
    else:
        db.execute(
            'UPDATE registrations SET status = "Cancelled" WHERE registration_id = ?',
            (registration_id,)
        )
        db.commit()
        flash('Registration cancelled successfully', 'success')
        # Create notification
        db.execute(
            'INSERT INTO notifications (student_id, event_id, message) VALUES (?, ?, ?)',
            (student_id, registration['event_id'], f'Your registration for {registration["event_name"]} has been cancelled.')
        )
        db.commit()

    db.close()
    return redirect(url_for('my_registrations'))

# Notifications
@app.route('/notifications')
def notifications():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student_id = session['student_id']
    db = get_db()
    notifications = db.execute('''
        SELECT n.*, e.event_name
        FROM notifications n
        JOIN events e ON n.event_id = e.event_id
        WHERE n.student_id = ?
        ORDER BY n.notification_date DESC
    ''', (student_id,)).fetchall()
    db.close()
    return render_template('notifications.html', notifications=notifications)

# Participation statistics
@app.route('/participation')
def participation():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    db = get_db()

    # Department-wise
    dept_stats = db.execute('''
        SELECT s.department, COUNT(r.registration_id) as count
        FROM students s
        JOIN registrations r ON s.student_id = r.student_id
        WHERE r.status = "Registered"
        GROUP BY s.department
        ORDER BY s.department
    ''').fetchall()

    # Year-wise
    year_stats = db.execute('''
        SELECT s.year, COUNT(r.registration_id) as count
        FROM students s
        JOIN registrations r ON s.student_id = r.student_id
        WHERE r.status = "Registered"
        GROUP BY s.year
        ORDER BY s.year
    ''').fetchall()

    # Department + Year
    dept_year_stats = db.execute('''
        SELECT s.department, s.year, COUNT(r.registration_id) as count
        FROM students s
        JOIN registrations r ON s.student_id = r.student_id
        WHERE r.status = "Registered"
        GROUP BY s.department, s.year
        ORDER BY s.department, s.year
    ''').fetchall()

    db.close()
    return render_template('participation.html',
                           dept_stats=dept_stats,
                           year_stats=year_stats,
                           dept_year_stats=dept_year_stats)

# About page
@app.route('/about')
def about():
    return render_template('about.html')

# Contact page
@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)