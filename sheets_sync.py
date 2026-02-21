"""
sheets_sync.py — Google Sheets integration.

Design decisions:
  - Fire-and-forget: sync_to_sheets() spawns a daemon thread so it never
    blocks the vote response path.  SQLite is always the source of truth.
  - Debounce: automatic syncs are skipped if the last sync was < 30 seconds
    ago.  The next vote will catch up.  This avoids hitting the Sheets API
    rate limit (≈60 writes/min) during burst voting.
  - Manual sync (Admin → Export) always runs immediately, bypassing debounce.
  - Summary tab: Option | Label | Count | Percentage  (cleared + rewritten)
  - Detail tab:  Timestamp | Option  (no card UIDs — privacy-safe)
"""
import threading
import time
import logging
import os

from config import CREDENTIALS_PATH, SHEETS_SYNC_DEBOUNCE

logger = logging.getLogger(__name__)

_last_sync_time = 0.0
_debounce_lock  = threading.Lock()

try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    logger.warning("gspread / google-auth not installed — Sheets sync disabled")

_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


# ── Public API ────────────────────────────────────────────────────────────────

def sync_to_sheets(session_id):
    """Non-blocking fire-and-forget sync (debounced)."""
    t = threading.Thread(target=_do_sync, args=(session_id, False), daemon=True)
    t.start()


def sync_to_sheets_blocking(session_id):
    """Synchronous sync for the Admin → Export button. Returns result dict."""
    global _last_sync_time
    with _debounce_lock:
        _last_sync_time = 0.0  # reset so debounce doesn't skip
    return _do_sync(session_id, force=True)


# ── Internal ──────────────────────────────────────────────────────────────────

def _get_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=_SCOPES)
    return gspread.authorize(creds)


def _do_sync(session_id, force=False):
    global _last_sync_time

    if not SHEETS_AVAILABLE:
        return {'success': False, 'error': 'gspread library not installed'}

    # Debounce check
    if not force:
        with _debounce_lock:
            now = time.time()
            if now - _last_sync_time < SHEETS_SYNC_DEBOUNCE:
                logger.debug("Sheets sync debounced (last sync %.0fs ago)", now - _last_sync_time)
                return {'success': False, 'error': 'Debounced'}
            _last_sync_time = now

    from database import get_setting, get_session, get_vote_counts, get_all_votes_for_export

    spreadsheet_id = get_setting('sheets_spreadsheet_id') or ''
    sheets_enabled  = get_setting('sheets_enabled') == '1'

    if not sheets_enabled:
        return {'success': False, 'error': 'Sheets sync is disabled in settings'}
    if not spreadsheet_id:
        return {'success': False, 'error': 'No Spreadsheet ID configured in settings'}
    if not os.path.exists(CREDENTIALS_PATH):
        return {'success': False, 'error': f'Credentials file not found: {CREDENTIALS_PATH}'}

    try:
        client = _get_client()
        sheet  = client.open_by_key(spreadsheet_id)

        session     = get_session(session_id)
        vote_counts = get_vote_counts(session_id)
        total       = sum(v['count'] for v in vote_counts.values())

        # ── Summary tab ───────────────────────────────────────────────────────
        try:
            summary_ws = sheet.worksheet('Summary')
        except gspread.WorksheetNotFound:
            summary_ws = sheet.add_worksheet(title='Summary', rows=30, cols=4)

        summary_ws.clear()
        summary_ws.update('A1', [['Question', session['question']]])
        summary_ws.update('A2', [['Option', 'Label', 'Count', 'Percentage']])

        summary_rows = []
        for opt, data in vote_counts.items():
            pct = f"{data['count'] / total * 100:.1f}%" if total > 0 else '0.0%'
            summary_rows.append([opt, data['label'], data['count'], pct])

        if summary_rows:
            summary_ws.update('A3', summary_rows)
        summary_ws.update(f'A{3 + len(summary_rows)}', [['', 'TOTAL', total, '']])

        # ── Detail tab ────────────────────────────────────────────────────────
        try:
            detail_ws = sheet.worksheet('Detail')
        except gspread.WorksheetNotFound:
            detail_ws = sheet.add_worksheet(title='Detail', rows=2000, cols=2)

        detail_ws.clear()
        detail_ws.update('A1', [['Timestamp', 'Option']])

        votes = get_all_votes_for_export(session_id)
        if votes:
            detail_ws.update('A2', [[v['voted_at'], v['option']] for v in votes])

        logger.info("Sheets sync complete for session %d (%d votes)", session_id, total)
        return {'success': True, 'total': total}

    except Exception as exc:
        logger.error("Sheets sync failed: %s", exc)
        return {'success': False, 'error': str(exc)}
