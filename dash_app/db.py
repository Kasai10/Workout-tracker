import sqlite3
import pandas as pd

DB_PATH = "workout.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT,
            exercise TEXT,
            repetitions INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_set(person, exercise, repetitions, date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if date:
        cursor.execute("""
            INSERT INTO workout_sets (person, exercise, repetitions, timestamp)
            VALUES (?, ?, ?, ?)
        """, (person, exercise, repetitions, date))
    else:
        cursor.execute("""
            INSERT INTO workout_sets (person, exercise, repetitions)
            VALUES (?, ?, ?)
        """, (person, exercise, repetitions))
    conn.commit()
    conn.close()

def delete_set(set_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM workout_sets WHERE id = ?
    """, (set_id,))
    conn.commit()
    conn.close()

def init_targets_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT,
            exercise TEXT,
            target_reps INTEGER,
            UNIQUE(person, exercise)
        )
    """)
    conn.commit()
    conn.close()

def insert_or_update_target(person, exercise, target_reps):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO daily_targets (person, exercise, target_reps)
        VALUES (?, ?, ?)
        ON CONFLICT(person, exercise) 
        DO UPDATE SET target_reps = ?
    """, (person, exercise, target_reps, target_reps))
    conn.commit()
    conn.close()

def get_all_targets():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM daily_targets ORDER BY person, exercise", conn)
    conn.close()
    return df

def delete_target(target_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM daily_targets WHERE id = ?
    """, (target_id,))
    conn.commit()
    conn.close()

def init_people_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    # Insert default people if not exists
    cursor.execute("INSERT OR IGNORE INTO people (name) VALUES ('Julia')")
    cursor.execute("INSERT OR IGNORE INTO people (name) VALUES ('Simo')")
    cursor.execute("INSERT OR IGNORE INTO people (name) VALUES ('Leon')")
    conn.commit()
    conn.close()

def init_exercises_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    # Insert default exercises if not exists
    default_exercises = ["Liegestütz", "Klimmzug", "Jogging", "Frauenliegestütz"]
    for exercise in default_exercises:
        cursor.execute("INSERT OR IGNORE INTO exercises (name) VALUES (?)", (exercise,))
    conn.commit()
    conn.close()

def add_person(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO people (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def add_exercise(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_all_people():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT name FROM people ORDER BY name", conn)
    conn.close()
    return df['name'].tolist() if not df.empty else []

def get_all_exercises_from_db():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT name FROM exercises ORDER BY name", conn)
    conn.close()
    return df['name'].tolist() if not df.empty else []

# Initialize DB on import
init_db()
init_targets_db()
init_people_db()
init_exercises_db()
