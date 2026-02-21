"""
database.py — SQLite schema and all DB helper functions.

All timestamps are stored and compared in local time using SQLite's
datetime('now', 'localtime') so school start/end times work correctly
regardless of the Pi's timezone setting.

WAL mode is enabled so the Sheets sync thread can read while Flask writes.
"""
import sqlite3
from config import DATABASE_PATH


# ── Connection ────────────────────────────────────────────────────────────────

def get_db():
    """Return a connection with WAL mode, foreign keys, and Row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables and insert default settings rows (idempotent)."""
    conn = get_db()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                question   TEXT    NOT NULL,
                option_a   TEXT    NOT NULL,
                option_b   TEXT    NOT NULL,
                option_c   TEXT,
                option_d   TEXT,
                start_time TEXT    NOT NULL,
                end_time   TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                is_active  INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS cards (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uid         TEXT    NOT NULL UNIQUE,
                label       TEXT,
                enrolled_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                is_active   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS votes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                option     TEXT    NOT NULL,
                voted_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS vote_tracker (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                card_uid   TEXT    NOT NULL,
                voted_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE(session_id, card_uid)
            );

            CREATE TABLE IF NOT EXISTS admin (
                id            INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            INSERT OR IGNORE INTO settings (key, value) VALUES ('sheets_spreadsheet_id', '');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('sheets_enabled', '0');
        """)
    conn.close()


# ── Session helpers ───────────────────────────────────────────────────────────

def get_active_session():
    """Return the session currently open for voting, or None."""
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT * FROM sessions
            WHERE is_active = 1
              AND datetime('now', 'localtime') BETWEEN datetime(start_time)
                                                   AND datetime(end_time)
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_session(session_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_sessions():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_session(question, option_a, option_b, option_c, option_d, start_time, end_time):
    conn = get_db()
    with conn:
        cursor = conn.execute(
            """INSERT INTO sessions
               (question, option_a, option_b, option_c, option_d, start_time, end_time)
               VALUES (?,?,?,?,?,?,?)""",
            (question, option_a, option_b, option_c or None, option_d or None, start_time, end_time),
        )
        return cursor.lastrowid
    conn.close()


def update_session(session_id, question, option_a, option_b, option_c, option_d,
                   start_time, end_time, is_active):
    conn = get_db()
    with conn:
        conn.execute("""
            UPDATE sessions
            SET question=?, option_a=?, option_b=?, option_c=?, option_d=?,
                start_time=?, end_time=?, is_active=?
            WHERE id=?
        """, (question, option_a, option_b, option_c or None, option_d or None,
              start_time, end_time, is_active, session_id))
    conn.close()


# ── Card helpers ──────────────────────────────────────────────────────────────

def card_is_registered(uid):
    """True if the card exists and is active."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM cards WHERE uid=? AND is_active=1", (uid,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def card_exists(uid):
    """True if the card exists (active or not) — used for enrollment UI."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM cards WHERE uid=?", (uid,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_all_cards():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM cards ORDER BY enrolled_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def enroll_card(uid, label=None):
    """Insert or re-activate a card."""
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO cards (uid, label, is_active) VALUES (?,?,1) "
            "ON CONFLICT(uid) DO UPDATE SET label=excluded.label, is_active=1",
            (uid, label),
        )
    conn.close()


def deactivate_card(card_id):
    conn = get_db()
    with conn:
        conn.execute("UPDATE cards SET is_active=0 WHERE id=?", (card_id,))
    conn.close()


# ── Vote helpers ──────────────────────────────────────────────────────────────

def card_has_voted(uid, session_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM vote_tracker WHERE session_id=? AND card_uid=?",
            (session_id, uid),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def record_vote(session_id, card_uid, option):
    """
    Atomically record a vote.
    Returns True on success, False if the card already voted (race-condition safe).
    """
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO vote_tracker (session_id, card_uid) VALUES (?,?)",
                (session_id, card_uid),
            )
            if cursor.rowcount == 0:
                return False
            conn.execute(
                "INSERT INTO votes (session_id, option) VALUES (?,?)",
                (session_id, option),
            )
        return True
    finally:
        conn.close()


def get_vote_counts(session_id):
    """
    Return {option: {label, count}} for all options in the session.
    Options with zero votes are included.
    """
    conn = get_db()
    try:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not session:
            return {}
        session = dict(session)

        rows = conn.execute(
            "SELECT option, COUNT(*) as cnt FROM votes WHERE session_id=? GROUP BY option",
            (session_id,),
        ).fetchall()
        counts_raw = {r['option']: r['cnt'] for r in rows}

        options = ['A', 'B']
        if session['option_c']:
            options.append('C')
        if session['option_d']:
            options.append('D')

        return {
            opt: {'label': session[f'option_{opt.lower()}'], 'count': counts_raw.get(opt, 0)}
            for opt in options
        }
    finally:
        conn.close()


def get_total_votes(session_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM votes WHERE session_id=?", (session_id,)
        ).fetchone()
        return row['cnt'] if row else 0
    finally:
        conn.close()


def get_all_votes_for_export(session_id):
    """Return list of {voted_at, option} dicts — no card UIDs."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT voted_at, option FROM votes WHERE session_id=? ORDER BY voted_at",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_setting(key):
    conn = get_db()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row['value'] if row else None
    finally:
        conn.close()


def set_setting(key, value):
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value)
        )
    conn.close()


# ── Admin helpers ─────────────────────────────────────────────────────────────

def set_admin_password(password_hash):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM admin")
        conn.execute("INSERT INTO admin (id, password_hash) VALUES (1,?)", (password_hash,))
    conn.close()


def get_admin_password_hash():
    conn = get_db()
    try:
        row = conn.execute("SELECT password_hash FROM admin WHERE id=1").fetchone()
        return row['password_hash'] if row else None
    finally:
        conn.close()
