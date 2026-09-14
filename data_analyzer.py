import logging
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Analyzes AdGuard Home query log data for a specific client."""

    def filter_by_client(self, logs: list[dict], client_ips: list[str], client_ids: list[str] = None) -> list[dict]:
        """Filter log entries belonging to a specific client by IP or client ID."""
        ip_set = set(client_ips or [])
        id_set = set(client_ids or [])
        filtered = []
        for entry in logs:
            client_ip = entry.get('client', '')
            client_id = entry.get('client_id', '')
            client_info_name = entry.get('client_info', {}).get('name', '') if entry.get('client_info') else ''
            if client_ip in ip_set or client_id in id_set or client_info_name in id_set:
                filtered.append(entry)
        return filtered

    def get_summary(self, logs: list[dict]) -> dict:
        """Get executive summary statistics."""
        total = len(logs)
        blocked = sum(1 for e in logs if self._is_blocked(e))
        return {
            'total_queries': total,
            'blocked_queries': blocked,
            'allowed_queries': total - blocked,
            'block_percentage': round((blocked / total * 100), 1) if total > 0 else 0,
            'avg_per_hour': round(total / 24, 1) if total > 0 else 0,
        }

    def get_top_domains(self, logs: list[dict], n: int = 20) -> list[tuple[str, int]]:
        """Get top N most queried domains."""
        domains = Counter()
        for entry in logs:
            question = entry.get('question', {})
            name = question.get('name', '') if isinstance(question, dict) else ''
            if name:
                name = name.rstrip('.')
                domains[name] += 1
        return domains.most_common(n)

    def get_top_blocked(self, logs: list[dict], n: int = 20) -> list[tuple[str, str, int]]:
        """Get top N blocked domains with blocking reason."""
        blocked = Counter()
        reasons = {}
        for entry in logs:
            if self._is_blocked(entry):
                question = entry.get('question', {})
                name = question.get('name', '') if isinstance(question, dict) else ''
                if name:
                    name = name.rstrip('.')
                    blocked[name] += 1
                    if name not in reasons:
                        reasons[name] = self._get_block_reason(entry)
        result = []
        for domain, count in blocked.most_common(n):
            result.append((domain, reasons.get(domain, 'Filtro'), count))
        return result

    def get_hourly_distribution(self, logs: list[dict]) -> dict[int, dict]:
        """Get query distribution by hour (0-23)."""
        hours_total = Counter()
        hours_blocked = Counter()
        for entry in logs:
            hour = self._get_hour(entry)
            if hour is not None:
                hours_total[hour] += 1
                if self._is_blocked(entry):
                    hours_blocked[hour] += 1
        result = {}
        for h in range(24):
            result[h] = {
                'total': hours_total.get(h, 0),
                'blocked': hours_blocked.get(h, 0),
            }
        return result

    def get_query_types(self, logs: list[dict]) -> list[tuple[str, int]]:
        """Get distribution of DNS query types (A, AAAA, HTTPS, etc.)."""
        types = Counter()
        for entry in logs:
            question = entry.get('question', {})
            qtype = question.get('type', 'UNKNOWN') if isinstance(question, dict) else 'UNKNOWN'
            types[qtype] += 1
        return types.most_common()

    def get_blocking_summary(self, logs: list[dict]) -> dict:
        """Get summary of blocks by reason category."""
        categories = Counter()
        for entry in logs:
            if self._is_blocked(entry):
                reason = self._get_block_reason(entry)
                categories[reason] += 1
        return dict(categories.most_common())

    def get_response_times(self, logs: list[dict]) -> dict:
        """Get response time statistics."""
        times = []
        for entry in logs:
            elapsed = entry.get('elapsed_ms', entry.get('elapsed', None))
            if elapsed is not None:
                try:
                    # elapsed might be in nanoseconds or milliseconds depending on version
                    val = float(elapsed)
                    # If value seems to be in nanoseconds (> 100000), convert to ms
                    if val > 100000:
                        val = val / 1_000_000
                    times.append(val)
                except (ValueError, TypeError):
                    continue
        if not times:
            return {'avg_ms': 0, 'min_ms': 0, 'max_ms': 0, 'median_ms': 0}
        times.sort()
        return {
            'avg_ms': round(sum(times) / len(times), 2),
            'min_ms': round(times[0], 2),
            'max_ms': round(times[-1], 2),
            'median_ms': round(times[len(times) // 2], 2),
        }

    def get_upstream_stats(self, logs: list[dict]) -> list[tuple[str, int]]:
        """Get most used upstream DNS servers."""
        upstreams = Counter()
        for entry in logs:
            upstream = entry.get('upstream', '')
            if upstream:
                upstreams[upstream] += 1
        return upstreams.most_common(10)

    def calculate_risk_score(self, logs: list[dict]) -> dict:
        """Calculate a risk score based on blocked threat types."""
        total = len(logs)
        if total == 0:
            return {'score': 0, 'level': 'Sin datos', 'details': {}}

        threat_counts = {
            'malware': 0,
            'phishing': 0,
            'parental': 0,
            'adblock': 0,
        }
        for entry in logs:
            if self._is_blocked(entry):
                reason = entry.get('reason', '')
                rules = entry.get('rules', []) or []
                reason_lower = str(reason).lower()
                rules_text = str(rules).lower()

                if 'safebrowsing' in reason_lower or 'malware' in rules_text:
                    threat_counts['malware'] += 1
                elif 'parental' in reason_lower:
                    threat_counts['parental'] += 1
                else:
                    threat_counts['adblock'] += 1

        # Score: malware/phishing weigh more heavily
        score = min(100, (
            threat_counts['malware'] * 10 +
            threat_counts['phishing'] * 8 +
            threat_counts['parental'] * 3 +
            threat_counts['adblock'] * 0.1
        ))

        if score >= 50:
            level = '🔴 Alto'
        elif score >= 20:
            level = '🟡 Medio'
        elif score > 0:
            level = '🟢 Bajo'
        else:
            level = '✅ Ninguno'

        return {'score': round(score, 1), 'level': level, 'details': threat_counts}

    # --- Private helpers ---

    def _is_blocked(self, entry: dict) -> bool:
        reason = entry.get('reason', '')
        if reason and reason not in ('NotFilteredNotFound', 'NotFilteredWhiteList', ''):
            # Check common blocked reasons
            blocked_reasons = [
                'FilteredBlackList', 'FilteredBlockedService',
                'FilteredSafeBrowsing', 'FilteredParental',
                'FilteredSafeSearch', 'FilteredInvalid',
                'Rewritten',  # Not exactly blocked but filtered
            ]
            if reason in blocked_reasons:
                return True
            # Also check if result has filter rules
            rules = entry.get('rules', [])
            if rules:
                return True
        return False

    def _get_block_reason(self, entry: dict) -> str:
        reason = entry.get('reason', '')
        reason_map = {
            'FilteredBlackList': 'Lista negra',
            'FilteredBlockedService': 'Servicio bloqueado',
            'FilteredSafeBrowsing': 'Safe Browsing (malware/phishing)',
            'FilteredParental': 'Control parental',
            'FilteredSafeSearch': 'Búsqueda segura',
            'FilteredInvalid': 'Consulta inválida',
        }
        return reason_map.get(reason, reason or 'Filtro')

    def _get_hour(self, entry: dict) -> int | None:
        time_str = entry.get('time', '')
        if not time_str:
            return None
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.hour
        except (ValueError, AttributeError):
            return None
