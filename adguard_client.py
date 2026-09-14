import logging
import time
from datetime import datetime, timedelta, timezone

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class AdGuardClient:
    """Client for AdGuard Home REST API."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'Content-Type': 'application/json'})

    def _request(self, method: str, endpoint: str, params=None, json_data=None, max_retries=3):
        url = f'{self.base_url}/control{endpoint}'
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, params=params, json=json_data, timeout=30)
                response.raise_for_status()
                return response.json() if response.content else None
            except requests.exceptions.RequestException as e:
                wait = 2 ** attempt
                logger.warning(f'Request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait}s...')
                if attempt < max_retries - 1:
                    time.sleep(wait)
                else:
                    logger.error(f'Request failed after {max_retries} attempts: {endpoint}')
                    raise

    def get_status(self) -> dict:
        """Get server status to verify connectivity."""
        return self._request('GET', '/status')

    def get_clients(self) -> dict:
        """Get list of configured (named) clients and auto-discovered clients."""
        return self._request('GET', '/clients')

    def get_querylog(self, limit: int = 500, offset: int = 0, search: str = None,
                     older_than: str = None, response_status: str = None) -> dict:
        """Get DNS query log entries with pagination."""
        params = {'limit': limit}
        if offset:
            params['offset'] = offset
        if search:
            params['search'] = search
        if older_than:
            params['older_than'] = older_than
        if response_status:
            params['response_status'] = response_status
        return self._request('GET', '/querylog', params=params)

    def get_all_querylog(self, hours: int = 24, limit_per_page: int = 500) -> list:
        """Fetch ALL query log entries for the specified period using pagination.
        
        Uses the 'older_than' cursor-based pagination to iterate through all entries.
        Stops when entries are older than the cutoff time or no more data is returned.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        all_entries = []
        older_than = None
        page = 0

        logger.info(f'Fetching query log for the last {hours} hours (since {cutoff.isoformat()})...')

        while True:
            page += 1
            data = self.get_querylog(limit=limit_per_page, older_than=older_than)

            if not data or 'data' not in data or not data['data']:
                logger.info(f'No more data at page {page}. Total entries: {len(all_entries)}')
                break

            entries = data['data']
            oldest_entry_time = None

            for entry in entries:
                # Parse entry timestamp
                entry_time_str = entry.get('time', '')
                try:
                    entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    all_entries.append(entry)
                    continue

                if entry_time < cutoff:
                    logger.info(f'Reached cutoff time at page {page}. Total entries: {len(all_entries)}')
                    return all_entries

                all_entries.append(entry)
                oldest_entry_time = entry_time_str

            # Use the oldest entry's timestamp for next page cursor
            if 'oldest' in data and data['oldest']:
                older_than = data['oldest']
            elif oldest_entry_time:
                older_than = oldest_entry_time
            else:
                break

            logger.info(f'Page {page}: fetched {len(entries)} entries. Running total: {len(all_entries)}')

            # Small delay to avoid overwhelming the server
            time.sleep(0.2)

        logger.info(f'Query log fetch complete. Total entries: {len(all_entries)}')
        return all_entries

    def get_stats(self, recent_ms: int = None) -> dict:
        """Get aggregated DNS statistics."""
        params = {}
        if recent_ms:
            params['recent'] = recent_ms
        return self._request('GET', '/stats', params=params)

    def test_connection(self) -> bool:
        """Test connectivity to AdGuard Home."""
        try:
            status = self.get_status()
            logger.info(f'Connected to AdGuard Home v{status.get("version", "unknown")} at {self.base_url}')
            return True
        except Exception as e:
            logger.error(f'Cannot connect to AdGuard Home at {self.base_url}: {e}')
            return False
