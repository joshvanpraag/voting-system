"""
config.py — Application constants and paths.

Edit NFC_I2C_ADDRESS if 'i2cdetect -y 1' shows a different address.
Set VOTING_SECRET_KEY env var in production for a stable key across reboots.
"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Security ──────────────────────────────────────────────────────────────────
# Stable key file is written by --setup; env var overrides for CI/testing
_key_file = os.path.join(BASE_DIR, '.secret_key')
if os.path.exists(_key_file):
    with open(_key_file) as _f:
        SECRET_KEY = _f.read().strip()
else:
    SECRET_KEY = os.environ.get('VOTING_SECRET_KEY', secrets.token_hex(32))

TOKEN_MAX_AGE = 300  # signed vote token lifespan in seconds (5 minutes)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_PATH = os.path.join(BASE_DIR, 'voting.db')

# ── NFC / Hardware ────────────────────────────────────────────────────────────
# Run `i2cdetect -y 1` to confirm. Coolwell PN532 HAT typically uses 0x24.
NFC_I2C_ADDRESS = 0x24
SCAN_COOLDOWN   = 2.0  # seconds before the same card UID can trigger again
RETRY_DELAY     = 5    # seconds to wait before reconnecting after an I2C error

# ── Display timing ────────────────────────────────────────────────────────────
RESULTS_DISPLAY_SECONDS = 15   # thankyou screen auto-return delay
ERROR_DISPLAY_SECONDS   = 5    # error overlay auto-hide delay

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH = os.path.join(BASE_DIR, 'logs', 'app.log')

# ── Google Sheets ─────────────────────────────────────────────────────────────
CREDENTIALS_PATH     = os.path.join(BASE_DIR, 'credentials', 'google_service_account.json')
SHEETS_SYNC_DEBOUNCE = 30  # minimum seconds between automatic background syncs
