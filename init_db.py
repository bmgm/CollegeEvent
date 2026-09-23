import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'college_event.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        department TEXT NOT NULL,
        year TEXT NOT NULL,
        mobile TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT NOT NULL,
        description TEXT,
        date TEXT,
        time TEXT,
        venue TEXT,
        eligibility TEXT,
        rules TEXT,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS registrations (
        registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Registered',
        UNIQUE(student_id, event_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        event_id INTEGER,
        message TEXT NOT NULL,
        notification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0
    )''')

    # Sample events
    sample_events = [
        ("Annual Sports Day", "Annual inter-college sports competition featuring athletics, basketball, volleyball and more.", "2026-10-15", "09:00 AM", "College Ground", "Open to all students", "Follow ground rules; wear appropriate sports gear.", "sports.jpg"),
        ("Cultural Fest", "A celebration of arts, music, dance and cultural performances from various departments.", "2026-10-22", "04:00 PM", "College Auditorium", "All students", "Maintain decorum during performances.", "culture.jpg"),
        ("Coding Competition", "A programming challenge testing algorithmic skills and problem-solving.", "2026-11-05", "10:00 AM", "Computer Lab", "BCA, BCS, BBA", "Use provided IDE; no external resources.", "coding.jpg"),
        ("Business Quiz", "An interactive quiz on business concepts, economics and marketing.", "2026-11-12", "02:00 PM", "Seminar Hall", "B.Com, B.Com(CA)", "Teams of 2; no mobile phones.", "quiz.jpg"),
        ("Traditional Day", "A day celebrating traditional culture, dress and heritage of our college.", "2026-11-20", "11:00 AM", "College Campus", "All students", "Wear traditional attire.", "traditional.jpg"),
    ]
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        for ev in sample_events:
            c.execute("INSERT INTO events (event_name, description, date, time, venue, eligibility, rules, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ev)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
