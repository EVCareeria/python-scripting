import hashlib
import secrets
import sqlite3

DB_PATH = 'c2_data.db'
PBKDF2_ITERATIONS = 210000
SESSION_COOKIE_NAME = 'cowrie_session'


def init_db():
    """Initialize SQLite database with parameterized schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            details TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES app_users(id)
        )
    ''')
    conn.commit()
    conn.close()


def hash_password(password):
    """Hash a password with PBKDF2-HMAC-SHA256 using a strong random salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()
    return salt, password_hash


def verify_password(password, password_hash, salt):
    """Verify a candidate password against the stored hash and salt."""
    expected_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()
    return secrets.compare_digest(expected_hash, password_hash)


def get_user_count():
    """Return the number of stored application users."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM app_users')
    count = cursor.fetchone()[0]
    conn.close()
    return count


def create_user(username, password, confirm_password):
    """Create the initial single-user account with a PBKDF2 hash."""
    username = (username or '').strip()
    password = password or ''
    if not username or len(password) < 12 or password != confirm_password:
        return False
    if get_user_count() > 0:
        return False

    salt, password_hash = hash_password(password)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO app_users (username, password_hash, salt) VALUES (?, ?, ?)',
            (username, password_hash, salt),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_username(username):
    """Return a stored user record for a username."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username, password_hash, salt FROM app_users WHERE username = ?',
        (username,),
    )
    user = cursor.fetchone()
    conn.close()
    if not user:
        return None
    return {'id': user[0], 'username': user[1], 'password_hash': user[2], 'salt': user[3]}


def build_session_token():
    """Return a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def create_session(username):
    """Create a new session for the user and return the token."""
    user = get_user_by_username(username)
    if not user:
        return None

    token = build_session_token()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO app_sessions (user_id, session_token, last_seen) VALUES (?, ?, CURRENT_TIMESTAMP)',
        (user['id'], token),
    )
    conn.commit()
    conn.close()
    return token


def parse_session_cookie_value(raw_value):
    """Parse a cookie value containing one or more session tokens."""
    if not raw_value:
        return []
    tokens = [part.strip() for part in raw_value.split(',') if part.strip()]
    return list(dict.fromkeys(tokens))


def get_active_sessions_for_user(username):
    """Return all valid session tokens for the given user."""
    user = get_user_by_username(username)
    if not user:
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT session_token FROM app_sessions WHERE user_id = ?',
        (user['id'],),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_user_from_session_tokens(tokens):
    """Return the corresponding user for any valid token, else None."""
    if not tokens:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ', '.join('?' for _ in tokens)
    query = f'''
        SELECT u.id, u.username
        FROM app_sessions s
        INNER JOIN app_users u ON u.id = s.user_id
        WHERE s.session_token IN ({placeholders})
    '''
    cursor.execute(query, tokens)
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {'id': row[0], 'username': row[1]}


def delete_session_token(token):
    """Delete a specific session token from storage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM app_sessions WHERE session_token = ?', (token,))
    conn.commit()
    conn.close()


def delete_all_user_sessions(username):
    """Delete all stored sessions for a username."""
    user = get_user_by_username(username)
    if not user:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM app_sessions WHERE user_id = ?', (user['id'],))
    conn.commit()
    conn.close()


def authenticate_user(username, password):
    """Authenticate a user against the stored PBKDF2 hash."""
    user = get_user_by_username(username)
    if not user:
        return False

    stored_username = user['username']
    if stored_username != username:
        return False
    return verify_password(password, user['password_hash'], user['salt'])


def log_event(timestamp, source, details):
    """Safely insert audit logs using parameterized SQL queries."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO audit_logs (timestamp, source, details) VALUES (?, ?, ?)',
            (timestamp, source, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
