"""
Logging filters to reduce noise from known benign requests.
"""
import logging

# Path requested by Chrome DevTools when DevTools are open; returns 404 and clutters logs
CHROME_DEVTOOLS_PATH = "/.well-known/appspecific/com.chrome.devtools.json"


class SuppressChromeDevTools404(logging.Filter):
    """Drop log records for Chrome DevTools' automatic request (404)."""

    def filter(self, record):
        try:
            msg = record.getMessage()
            if CHROME_DEVTOOLS_PATH in msg:
                return False
            if record.args and CHROME_DEVTOOLS_PATH in str(record.args):
                return False
        except Exception:
            pass
        return True
