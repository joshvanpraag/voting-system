"""
app.py — Flask application: routes, Socket.IO, and CLI setup wizard.

Start server:  python app.py
First-time:    python app.py --setup
"""
import os
import sys
import csv
import io
import logging
import argparse
import secrets
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for,
    request, session, jsonify, Response, flash,
)
from flask_socketio import SocketIO, emit
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import (
    SECRET_KEY, TOKEN_MAX_AGE, LOG_PATH,
    RESULTS_DISPLAY_SECONDS, ERROR_DISPLAY_SECONDS,
    BASE_DIR,
)
import database as db


# ── Logging ───────────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── App + SocketIO ────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = SECRET_KEY

# threading mode is mandatory — eventlet/gevent break I2C/GPIO drivers
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')


# ── Helpers ───────────────────────────────────────────────────────────────────

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def make_token(data):
    return URLSafeTimedSerializer(SECRET_KEY).dumps(data)


def verify_token(token):
    try:
        return URLSafeTimedSerializer(SECRET_KEY).loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def db_time_to_html(dt_str):
    """'2025-09-15 09:00:00'  →  '2025-09-15T09:00'  for datetime-local inputs."""
    if not dt_str:
        return ''
    return dt_str[:16].replace(' ', 'T')


def html_time_to_db(dt_str):
    """'2025-09-15T09:00'  →  '2025-09-15 09:00:00'  for SQLite storage."""
    if not dt_str:
        return ''
    return dt_str.replace('T', ' ') + ':00'


def _build_options(vsession):
    """Return list of (key, label) tuples for a session row."""
    options = [('A', vsession['option_a']), ('B', vsession['option_b'])]
    if vsession.get('option_c'):
        options.append(('C', vsession['option_c']))
    if vsession.get('option_d'):
        options.append(('D', vsession['option_d']))
    return options


# ── Public / Kiosk routes ─────────────────────────────────────────────────────

@app.route('/')
def welcome():
    active = db.get_active_session()
    if not active:
        return redirect(url_for('closed'))
    return render_template(
        'welcome.html',
        voting_session=active,
        error_display_ms=ERROR_DISPLAY_SECONDS * 1000,
    )


@app.route('/vote/<token>')
def vote(token):
    data = verify_token(token)
    if not data:
        return redirect(url_for('error_page', msg='token_expired'))

    active = db.get_active_session()
    if not active or active['id'] != data['session_id']:
        return redirect(url_for('error_page', msg='session_changed'))

    if db.card_has_voted(data['uid'], active['id']):
        return redirect(url_for('error_page', msg='already_voted'))

    return render_template(
        'vote.html',
        voting_session=active,
        options=_build_options(active),
        token=token,
    )


@app.route('/submit-vote', methods=['POST'])
def submit_vote():
    token         = request.form.get('token', '')
    chosen_option = request.form.get('option', '').upper()

    if not token or not chosen_option:
        return redirect(url_for('error_page', msg='invalid_request'))

    data = verify_token(token)
    if not data:
        return redirect(url_for('error_page', msg='token_expired'))

    uid        = data['uid']
    session_id = data['session_id']

    vsession = db.get_session(session_id)
    if not vsession:
        return redirect(url_for('error_page', msg='session_not_found'))

    valid_options = [k for k, _ in _build_options(vsession)]
    if chosen_option not in valid_options:
        return redirect(url_for('error_page', msg='invalid_option'))

    # Atomic duplicate-safe vote record
    if not db.record_vote(session_id, uid, chosen_option):
        return redirect(url_for('error_page', msg='already_voted'))

    # Fire-and-forget Sheets sync
    if db.get_setting('sheets_enabled') == '1':
        from sheets_sync import sync_to_sheets
        sync_to_sheets(session_id)

    # Notify any open result views
    total = db.get_total_votes(session_id)
    socketio.emit('vote_update', {'session_id': session_id, 'total': total}, namespace='/kiosk')

    return redirect(url_for('thankyou', session_id=session_id))


@app.route('/thankyou/<int:session_id>')
def thankyou(session_id):
    vsession = db.get_session(session_id)
    if not vsession:
        return redirect(url_for('welcome'))
    return render_template(
        'thankyou.html',
        voting_session=vsession,
        results_display_seconds=RESULTS_DISPLAY_SECONDS,
    )


@app.route('/closed')
def closed():
    return render_template('closed.html')


@app.route('/error')
def error_page():
    msg = request.args.get('msg', 'unknown_error')
    messages = {
        'token_expired':     'Your session has expired. Please tap your card again.',
        'already_voted':     'You have already voted this week!',
        'session_changed':   'The voting session changed. Please tap your card again.',
        'invalid_request':   'Invalid request. Please try again.',
        'session_not_found': 'Voting session not found.',
        'invalid_option':    'Invalid option selected.',
        'unknown_error':     'An unexpected error occurred.',
    }
    return render_template(
        'error.html',
        message=messages.get(msg, messages['unknown_error']),
        error_display_seconds=ERROR_DISPLAY_SECONDS,
    )


@app.route('/results-data/<int:session_id>')
def results_data(session_id):
    counts = db.get_vote_counts(session_id)
    total  = sum(v['count'] for v in counts.values())
    return jsonify({'counts': counts, 'total': total})


# ── Admin — auth ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        hash_    = db.get_admin_password_hash()
        if hash_ and bcrypt.checkpw(password.encode(), hash_.encode()):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect password.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# ── Admin — dashboard ─────────────────────────────────────────────────────────

@app.route('/admin')
@app.route('/admin/')
@require_admin
def admin_dashboard():
    active      = db.get_active_session()
    all_sessions = db.get_all_sessions()
    cards       = db.get_all_cards()
    total_cards = sum(1 for c in cards if c['is_active'])
    votes_today = db.get_total_votes(active['id']) if active else 0
    return render_template(
        'admin/dashboard.html',
        active_session=active,
        sessions=all_sessions,
        total_cards=total_cards,
        votes_today=votes_today,
    )


# ── Admin — sessions ──────────────────────────────────────────────────────────

@app.route('/admin/sessions')
@require_admin
def admin_sessions():
    return render_template('admin/sessions.html', sessions=db.get_all_sessions())


@app.route('/admin/sessions/new', methods=['GET', 'POST'])
@require_admin
def admin_sessions_new():
    if request.method == 'POST':
        question   = request.form.get('question',   '').strip()
        option_a   = request.form.get('option_a',   '').strip()
        option_b   = request.form.get('option_b',   '').strip()
        option_c   = request.form.get('option_c',   '').strip() or None
        option_d   = request.form.get('option_d',   '').strip() or None
        start_time = html_time_to_db(request.form.get('start_time', '').strip())
        end_time   = html_time_to_db(request.form.get('end_time',   '').strip())

        if not all([question, option_a, option_b, start_time, end_time]):
            flash('Please fill in all required fields.', 'error')
            return render_template('admin/session_form.html', vs=None, action='Create')

        db.create_session(question, option_a, option_b, option_c, option_d, start_time, end_time)
        flash('Session created!', 'success')
        return redirect(url_for('admin_sessions'))

    return render_template('admin/session_form.html', vs=None, action='Create')


@app.route('/admin/sessions/<int:session_id>/edit', methods=['GET', 'POST'])
@require_admin
def admin_sessions_edit(session_id):
    vsession = db.get_session(session_id)
    if not vsession:
        flash('Session not found.', 'error')
        return redirect(url_for('admin_sessions'))

    if request.method == 'POST':
        question   = request.form.get('question',   '').strip()
        option_a   = request.form.get('option_a',   '').strip()
        option_b   = request.form.get('option_b',   '').strip()
        option_c   = request.form.get('option_c',   '').strip() or None
        option_d   = request.form.get('option_d',   '').strip() or None
        start_time = html_time_to_db(request.form.get('start_time', '').strip())
        end_time   = html_time_to_db(request.form.get('end_time',   '').strip())
        is_active  = 1 if request.form.get('is_active') else 0

        if not all([question, option_a, option_b, start_time, end_time]):
            flash('Please fill in all required fields.', 'error')
        else:
            db.update_session(session_id, question, option_a, option_b, option_c, option_d,
                              start_time, end_time, is_active)
            flash('Session updated.', 'success')
            return redirect(url_for('admin_sessions'))

    # Pre-fill form with HTML-compatible datetime strings
    vs = dict(vsession)
    vs['start_time_html'] = db_time_to_html(vsession['start_time'])
    vs['end_time_html']   = db_time_to_html(vsession['end_time'])
    return render_template('admin/session_form.html', vs=vs, action='Edit')


# ── Admin — cards ─────────────────────────────────────────────────────────────

@app.route('/admin/cards')
@require_admin
def admin_cards():
    return render_template('admin/cards.html', cards=db.get_all_cards())


@app.route('/admin/cards/deactivate/<int:card_id>', methods=['POST'])
@require_admin
def admin_cards_deactivate(card_id):
    db.deactivate_card(card_id)
    flash('Card deactivated.', 'success')
    return redirect(url_for('admin_cards'))


# ── Admin — results ───────────────────────────────────────────────────────────

@app.route('/admin/results')
@require_admin
def admin_results():
    all_sessions = db.get_all_sessions()
    selected_id  = request.args.get('session_id', type=int)
    active       = db.get_active_session()

    if selected_id:
        selected = db.get_session(selected_id)
    elif active:
        selected    = active
        selected_id = active['id']
    elif all_sessions:
        selected    = all_sessions[0]
        selected_id = selected['id']
    else:
        selected = None

    return render_template(
        'admin/results.html',
        sessions=all_sessions,
        selected=selected,
        selected_id=selected_id,
    )


# ── Admin — export ────────────────────────────────────────────────────────────

@app.route('/admin/export')
@require_admin
def admin_export():
    all_sessions = db.get_all_sessions()
    selected_id  = request.args.get('session_id', type=int)
    if not selected_id and all_sessions:
        selected_id = all_sessions[0]['id']
    selected = db.get_session(selected_id) if selected_id else None
    return render_template(
        'admin/export.html',
        sessions=all_sessions,
        selected=selected,
        selected_id=selected_id,
    )


@app.route('/admin/export/csv')
@require_admin
def admin_export_csv():
    session_id   = request.args.get('session_id', type=int)
    all_sessions = db.get_all_sessions()

    if not session_id and all_sessions:
        session_id = all_sessions[0]['id']
    if not session_id:
        flash('No sessions available.', 'error')
        return redirect(url_for('admin_export'))

    vsession = db.get_session(session_id)
    votes    = db.get_all_votes_for_export(session_id)
    counts   = db.get_vote_counts(session_id)
    total    = sum(v['count'] for v in counts.values())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Voting System Export'])
    writer.writerow(['Question:', vsession['question']])
    writer.writerow(['Session Start:', vsession['start_time']])
    writer.writerow(['Session End:',   vsession['end_time']])
    writer.writerow([])
    writer.writerow(['=== SUMMARY ==='])
    writer.writerow(['Option', 'Label', 'Count', 'Percentage'])
    for opt, data in counts.items():
        pct = f"{data['count'] / total * 100:.1f}%" if total > 0 else '0.0%'
        writer.writerow([opt, data['label'], data['count'], pct])
    writer.writerow(['', 'TOTAL', total, ''])
    writer.writerow([])
    writer.writerow(['=== DETAIL ==='])
    writer.writerow(['Timestamp', 'Option'])
    for v in votes:
        writer.writerow([v['voted_at'], v['option']])

    safe_q   = vsession['question'][:30].replace(' ', '_')
    filename = f"votes_{safe_q}_{datetime.now().strftime('%Y%m%d')}.csv"
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@app.route('/admin/export/sheets', methods=['POST'])
@require_admin
def admin_export_sheets():
    session_id = request.form.get('session_id', type=int)
    if not session_id:
        return jsonify({'success': False, 'error': 'No session selected'})
    from sheets_sync import sync_to_sheets_blocking
    result = sync_to_sheets_blocking(session_id)
    return jsonify(result)


# ── Admin — settings ──────────────────────────────────────────────────────────

@app.route('/admin/settings', methods=['GET', 'POST'])
@require_admin
def admin_settings():
    if request.method == 'POST':
        spreadsheet_id = request.form.get('spreadsheet_id', '').strip()
        sheets_enabled = '1' if request.form.get('sheets_enabled') else '0'
        db.set_setting('sheets_spreadsheet_id', spreadsheet_id)
        db.set_setting('sheets_enabled', sheets_enabled)
        flash('Settings saved.', 'success')

    spreadsheet_id = db.get_setting('sheets_spreadsheet_id') or ''
    sheets_enabled  = db.get_setting('sheets_enabled') == '1'
    return render_template(
        'admin/settings.html',
        spreadsheet_id=spreadsheet_id,
        sheets_enabled=sheets_enabled,
    )


# ── Socket.IO handlers ────────────────────────────────────────────────────────

@socketio.on('connect', namespace='/kiosk')
def kiosk_connect():
    logger.debug("Kiosk client connected")


@socketio.on('connect', namespace='/admin')
def admin_connect():
    logger.debug("Admin client connected")


@socketio.on('enroll_card', namespace='/admin')
def handle_enroll_card(data):
    uid   = (data.get('uid')   or '').strip()
    label = (data.get('label') or '').strip() or None
    if not uid:
        return
    db.enroll_card(uid, label)
    logger.info("Card enrolled: %s (%s)", uid, label)
    emit('enroll_success', {'uid': uid, 'label': label or ''})


# ── CLI setup wizard ──────────────────────────────────────────────────────────

def run_setup():
    """Initialise DB, generate stable secret key, set admin password."""
    import getpass

    print("=== School Voting System — First-Time Setup ===\n")

    # Stable secret key
    key_file = os.path.join(BASE_DIR, '.secret_key')
    if not os.path.exists(key_file):
        key = secrets.token_hex(32)
        with open(key_file, 'w') as f:
            f.write(key)
        os.chmod(key_file, 0o600)
        print("Secret key generated.")
    else:
        print("Secret key already exists.")

    # Database
    db.init_db()
    print("Database initialised.")

    # Admin password
    while True:
        pw  = getpass.getpass("\nSet admin password (min 6 chars): ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw != pw2:
            print("Passwords do not match.")
            continue
        if len(pw) < 6:
            print("Password must be at least 6 characters.")
            continue
        break

    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    db.set_admin_password(hashed)
    print("\nAdmin password set.")
    print("\nSetup complete!")
    print("  Start server:  python app.py")
    print("  Admin panel:   http://127.0.0.1:5000/admin")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='School Voting System')
    parser.add_argument('--setup', action='store_true', help='Run first-time setup wizard')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    if args.setup:
        run_setup()
        sys.exit(0)

    if not os.path.exists(db.DATABASE_PATH):
        print("Database not found. Run:  python app.py --setup")
        sys.exit(1)

    from nfc_reader import init_nfc
    init_nfc(socketio)

    logger.info("Starting server on %s:%d", args.host, args.port)
    # use_reloader=False is MANDATORY — reloader spawns a second process
    # which starts a second NFC thread causing an I2C conflict.
    socketio.run(app, host=args.host, port=args.port, debug=False, use_reloader=False)
