import os
import sys
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        # AdGuard Home
        self.adguard_url = self._require('ADGUARD_URL')
        self.adguard_user = self._require('ADGUARD_USER')
        self.adguard_pass = self._require('ADGUARD_PASS')

        # Resend Email
        self.resend_api_key = self._require('RESEND_API_KEY')
        self.email_from = self._require('EMAIL_FROM')
        self.email_to = [e.strip() for e in self._require('EMAIL_TO').split(',')]

        # Schedule
        self.cron_schedule = os.getenv('CRON_SCHEDULE', '0 6 * * *')
        self.timezone = os.getenv('TZ', 'America/Mexico_City')

        # Report settings
        self.reports_dir = os.getenv('REPORTS_DIR', './reports')
        self.querylog_hours = int(os.getenv('QUERYLOG_HOURS', '24'))
        self.querylog_limit = int(os.getenv('QUERYLOG_LIMIT', '5000'))
        self.top_domains_count = int(os.getenv('TOP_DOMAINS_COUNT', '20'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

        # Optional
        self.run_on_start = os.getenv('RUN_ON_START', 'true').lower() == 'true'

        # Normalize AdGuard URL
        self.adguard_url = self.adguard_url.rstrip('/')

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            logger.error(f'Variable de entorno requerida no encontrada: {key}')
            sys.exit(1)
        return value

    def setup_logging(self):
        log_dir = os.path.join(os.path.dirname(self.reports_dir), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(os.path.join(log_dir, 'adguard_reports.log'), encoding='utf-8'),
            ],
        )
