import re
from collections import Counter

# Category definitions with domain patterns
CATEGORY_PATTERNS = {
    'Redes Sociales': [
        'facebook.com', 'fbcdn.net', 'fb.com', 'instagram.com', 'cdninstagram.com',
        'twitter.com', 'x.com', 'twimg.com', 'tiktok.com', 'tiktokcdn.com',
        'snapchat.com', 'snap.com', 'sc-cdn.net', 'linkedin.com', 'licdn.com',
        'pinterest.com', 'pinimg.com', 'reddit.com', 'redd.it', 'redditstatic.com',
        'tumblr.com', 'threads.net', 'bsky.social', 'mastodon.social',
    ],
    'Streaming Video': [
        'netflix.com', 'nflxvideo.net', 'nflximg.net', 'nflxso.net', 'nflxext.com',
        'youtube.com', 'googlevideo.com', 'ytimg.com', 'youtu.be', 'yt3.ggpht.com',
        'disneyplus.com', 'disney-plus.net', 'bamgrid.com', 'disney.com',
        'hbomax.com', 'max.com', 'hbomaxcdn.com',
        'primevideo.com', 'amazonvideo.com', 'aiv-cdn.net',
        'hulu.com', 'hulustream.com', 'crunchyroll.com',
        'plex.tv', 'plexapp.com', 'twitch.tv', 'twitchcdn.net', 'jtvnw.net',
        'vimeo.com', 'vimeocdn.com', 'roku.com', 'paramountplus.com',
        'peacocktv.com', 'starz.com', 'mubi.com',
    ],
    'Streaming Música': [
        'spotify.com', 'scdn.co', 'spotifycdn.com', 'spotilocal.com',
        'music.apple.com', 'applemusic.com',
        'deezer.com', 'tidal.com', 'tidalhifi.com',
        'pandora.com', 'soundcloud.com', 'sndcdn.com',
        'music.youtube.com', 'music.amazon.com',
    ],
    'Mensajería': [
        'whatsapp.com', 'whatsapp.net',
        'telegram.org', 't.me', 'telegram.me', 'telegra.ph',
        'signal.org', 'signal.art',
        'discord.com', 'discord.gg', 'discordapp.com', 'discordapp.net',
        'slack.com', 'slack-edge.com',
        'messenger.com', 'fbsbx.com',
        'teams.microsoft.com', 'skype.com',
        'viber.com', 'line.me', 'zoom.us', 'zoomcdn.com',
    ],
    'Gaming': [
        'steampowered.com', 'steamcommunity.com', 'steamcontent.com', 'steamcdn-a.akamaihd.net',
        'epicgames.com', 'unrealengine.com', 'fortnite.com',
        'riotgames.com', 'leagueoflegends.com',
        'playstation.com', 'playstation.net', 'sonyentertainmentnetwork.com',
        'xbox.com', 'xboxlive.com',
        'nintendo.com', 'nintendo.net',
        'ea.com', 'origin.com',
        'ubisoft.com', 'ubi.com',
        'blizzard.com', 'battle.net', 'blzstatic.cn',
        'roblox.com', 'rbxcdn.com',
        'mojang.com', 'minecraft.net',
        'gog.com', 'valvesoftware.com',
    ],
    'Productividad': [
        'google.com', 'googleapis.com', 'gstatic.com', 'google-analytics.com',
        'microsoft.com', 'office.com', 'office365.com', 'microsoftonline.com',
        'live.com', 'outlook.com', 'hotmail.com',
        'dropbox.com', 'dropboxapi.com',
        'notion.so', 'notion.com',
        'trello.com', 'atlassian.com', 'jira.com',
        'github.com', 'githubusercontent.com', 'githubassets.com',
        'gitlab.com', 'stackoverflow.com',
        'docs.google.com', 'drive.google.com',
        'onedrive.live.com', 'sharepoint.com',
        'evernote.com', 'todoist.com',
    ],
    'E-commerce': [
        'amazon.com', 'amazon.com.mx', 'amazonws.com', 'media-amazon.com',
        'mercadolibre.com', 'mercadolibre.com.mx', 'mlstatic.com',
        'ebay.com', 'ebaystatic.com',
        'aliexpress.com', 'alibaba.com',
        'walmart.com', 'walmart.com.mx',
        'shopify.com', 'shein.com',
        'etsy.com', 'temu.com',
    ],
    'Noticias': [
        'bbc.com', 'bbc.co.uk', 'cnn.com', 'nytimes.com',
        'reuters.com', 'apnews.com', 'elpais.com',
        'eluniversal.com.mx', 'milenio.com', 'reforma.com',
        'infobae.com', 'univision.com',
        'theguardian.com', 'washingtonpost.com',
        'bloomberg.com', 'forbes.com',
    ],
    'Educación': [
        'wikipedia.org', 'wikimedia.org', 'wiktionary.org',
        'coursera.org', 'udemy.com', 'edx.org',
        'khanacademy.org', 'duolingo.com',
        'scholar.google.com', 'academia.edu',
        'quizlet.com', 'chegg.com',
    ],
    'Telemetría / Tracking': [
        'analytics', 'tracker', 'tracking', 'telemetry',
        'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
        'adsserver', 'adservice', 'advertising',
        'crashlytics.com', 'app-measurement.com',
        'branch.io', 'adjust.com', 'appsflyer.com',
        'mixpanel.com', 'amplitude.com', 'segment.io', 'segment.com',
        'hotjar.com', 'mouseflow.com', 'fullstory.com',
        'sentry.io', 'bugsnag.com',
    ],
    'CDN / Infraestructura': [
        'cloudflare.com', 'cloudflare-dns.com', 'cloudflareinsights.com',
        'akamai.net', 'akamaized.net', 'akamaihd.net',
        'fastly.net', 'fastlylb.net',
        'amazonaws.com', 'aws.amazon.com',
        'azure.com', 'azureedge.net', 'msedge.net',
        'cloudfront.net', 'edgekey.net',
    ],
    'Smart Home / IoT': [
        'alexa.amazon.com', 'amazonalexa.com',
        'nest.com', 'home.google.com',
        'philips-hue.com', 'meethue.com',
        'ring.com', 'wyze.com',
        'tuya.com', 'smartthings.com',
        'homekit.apple.com',
    ],
}


class DomainClassifier:
    """Classifies domains into predefined categories."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile patterns for efficient matching."""
        self._exact = {}  # domain -> category for exact matches
        self._substring = []  # (substring, category) for partial matches

        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                # If pattern looks like a full domain (has a dot), use suffix matching
                if '.' in pattern:
                    self._exact[pattern] = category
                else:
                    # Substring match (for patterns like 'analytics', 'tracker')
                    self._substring.append((pattern.lower(), category))

    def classify(self, domain: str) -> str:
        """Classify a single domain into a category."""
        if not domain:
            return 'Otros'

        domain_lower = domain.lower().strip('.')

        # Check exact match and suffix match (e.g., 'api.facebook.com' matches 'facebook.com')
        for known_domain, category in self._exact.items():
            if domain_lower == known_domain or domain_lower.endswith('.' + known_domain):
                return category

        # Check substring matches (e.g., 'analytics' in domain)
        for substring, category in self._substring:
            if substring in domain_lower:
                return category

        return 'Otros'

    def classify_bulk(self, domains_with_counts: list[tuple[str, int]]) -> dict[str, int]:
        """Classify a list of (domain, count) tuples and return category totals."""
        category_counts = Counter()
        for domain, count in domains_with_counts:
            category = self.classify(domain)
            category_counts[category] += count
        return dict(category_counts.most_common())

    def classify_domains_list(self, domains_with_counts: list[tuple[str, int]]) -> dict[str, list[tuple[str, int]]]:
        """Classify domains and return them grouped by category."""
        categories = {}
        for domain, count in domains_with_counts:
            category = self.classify(domain)
            if category not in categories:
                categories[category] = []
            categories[category].append((domain, count))
        # Sort each category's domains by count descending
        for cat in categories:
            categories[cat].sort(key=lambda x: x[1], reverse=True)
        return categories
