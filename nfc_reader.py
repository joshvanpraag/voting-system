"""
nfc_reader.py — PN532 NFC reader background thread.

Critical constraints:
  - async_mode='threading' is mandatory; eventlet/gevent break I2C.
  - use_reloader=False is mandatory; the reloader spawns a second process
    which starts a second NFC thread causing I2C conflicts.
  - This thread never touches Flask routes — only Socket.IO emits.

I2C address: run `i2cdetect -y 1` to confirm. Typically 0x24 for the
Coolwell PN532 HAT. Change NFC_I2C_ADDRESS in config.py if needed.
"""
import threading
import time
import logging

from config import NFC_I2C_ADDRESS, SCAN_COOLDOWN, RETRY_DELAY, SECRET_KEY

logger = logging.getLogger(__name__)

# Graceful degradation: import hardware libs only on Pi
try:
    import board
    import busio
    from adafruit_pn532.i2c import PN532_I2C
    HW_AVAILABLE = True
except (ImportError, NotImplementedError):
    HW_AVAILABLE = False
    logger.warning("NFC hardware libraries not available — running without NFC reader")

_socketio = None


def init_nfc(socketio_instance):
    """Start the NFC reader thread. Called once at app startup."""
    global _socketio
    _socketio = socketio_instance
    t = NFCReaderThread()
    t.daemon = True
    t.start()
    if HW_AVAILABLE:
        logger.info("NFC reader thread started")
    else:
        logger.info("NFC reader thread started (simulation mode — no hardware)")


class NFCReaderThread(threading.Thread):
    def __init__(self):
        super().__init__(name="NFCReaderThread", daemon=True)
        self._last_uid       = None
        self._last_scan_time = 0.0

    def run(self):
        if not HW_AVAILABLE:
            # Keep thread alive so the app can still run on non-Pi machines
            while True:
                time.sleep(60)
            return

        while True:
            try:
                self._run_reader()
            except Exception as exc:
                logger.error("NFC reader error: %s. Reconnecting in %ds…", exc, RETRY_DELAY)
                time.sleep(RETRY_DELAY)

    def _run_reader(self):
        i2c   = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, address=NFC_I2C_ADDRESS)
        pn532.SAM_configuration()
        logger.info("PN532 ready at I2C 0x%02X", NFC_I2C_ADDRESS)

        while True:
            uid_bytes = pn532.read_passive_target(timeout=0.5)
            if uid_bytes is None:
                continue

            uid = ':'.join(f'{b:02X}' for b in uid_bytes)
            now = time.time()

            # Suppress double-fire from a single physical tap
            if uid == self._last_uid and (now - self._last_scan_time) < SCAN_COOLDOWN:
                continue

            self._last_uid       = uid
            self._last_scan_time = now
            logger.info("Card scanned: %s", uid)
            self._process_scan(uid)

    def _process_scan(self, uid):
        from database import (
            get_active_session, card_is_registered,
            card_has_voted, card_exists,
        )
        from itsdangerous import URLSafeTimedSerializer

        # Always tell the admin enrollment UI about every scan
        already_enrolled = card_exists(uid)
        _socketio.emit(
            'card_scan_raw',
            {'uid': uid, 'already_enrolled': already_enrolled},
            namespace='/admin',
        )

        # Gate 1: is voting open?
        session = get_active_session()
        if not session:
            _socketio.emit(
                'card_error',
                {'message': 'Voting is not open right now.'},
                namespace='/kiosk',
            )
            return

        # Gate 2: is card registered?
        if not card_is_registered(uid):
            _socketio.emit(
                'card_error',
                {'message': 'Card not registered. Please see an administrator.'},
                namespace='/kiosk',
            )
            return

        # Gate 3: already voted?
        if card_has_voted(uid, session['id']):
            _socketio.emit(
                'card_error',
                {'message': 'You have already voted this week!'},
                namespace='/kiosk',
            )
            return

        # All checks passed — issue a short-lived signed token
        token = URLSafeTimedSerializer(SECRET_KEY).dumps(
            {'uid': uid, 'session_id': session['id']}
        )
        _socketio.emit(
            'card_valid',
            {'redirect_url': f'/vote/{token}'},
            namespace='/kiosk',
        )
