"""Read-only, bounded HN sampling and URL normalization."""
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

API = 'https://hn.algolia.com/api/v1/search_by_date'
MAX_BYTES = 4 * 1024 * 1024
WARNING = 'LIMITED SAMPLE: mentions are not endorsements; this is not a comprehensive HN ranking.'
RESERVED = {'about', 'apps', 'blog', 'collections', 'contact', 'customer-stories', 'enterprise', 'events', 'explore', 'features', 'issues', 'join', 'login', 'logout', 'marketplace', 'new', 'notifications', 'orgs', 'organizations', 'pricing', 'pulls', 'search', 'security', 'settings', 'site', 'sponsors', 'topics', 'trending', 'users'}


def canonical(raw):
    raw = raw.rstrip('.,;:!?)]}')
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):
        return None
    try:
        u = urlsplit(raw)
        if u.scheme.lower() not in ('https', 'http') or u.username or u.password or u.port:
            return None
        host = (u.hostname or '').lower()
    except ValueError:
        return None
    if host in ('github.com', 'www.github.com'):
        parts = u.path.strip('/').split('/')
        if len(parts) < 2 or parts[0].lower() in RESERVED:
            return None
        owner, repo = parts[:2]
        if repo.lower().endswith('.git'):
            repo = repo[:-4]
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?', owner):
            return None
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or repo in ('.', '..'):
            return None
        return ('github', f'https://github.com/{owner.lower()}/{repo.lower()}')
    if host in ('arxiv.org', 'www.arxiv.org'):
        m = re.fullmatch(r'/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-zA-Z][a-zA-Z.-]*/\d{7}))(?:v\d+)?(?:\.pdf)?/?', u.path)
        if m:
            return ('arxiv', 'https://arxiv.org/abs/' + m[1].lower())
    return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.urls.extend(v for k, v in attrs if k == 'href' and v)

    def handle_data(self, data):
        self.text.append(data)


def extract(text):
    parser = Links()
    parser.feed(text)
    urls = parser.urls + re.findall(r'https?://[^\s<>"\']+', ' '.join(parser.text), re.I)
    return {item for url in urls if (item := canonical(url))}


class APIError(Exception):
    """An API request failed or returned an invalid response."""


def fetch_page(url):
    try:
        request = Request(url, headers={'User-Agent': 'rex-hnlinks/0.1.0', 'Accept': 'application/json'})
        with urlopen(request, timeout=15) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise APIError('API response exceeded 4 MiB')
        return json.loads(raw)
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise APIError('API request failed (network error or invalid JSON)') from exc


def sample(query, *, kind='all', days=30, limit=10, pages=3, now=None, fetch=fetch_page):
    if not query.strip() or kind not in ('all', 'github', 'arxiv') or not 1 <= pages <= 10 or days < 1 or limit < 1:
        raise ValueError('invalid sampling options')
    cutoff = int(time.time() if now is None else now) - days * 86400
    seen, counts, examples = set(), {}, {}
    fetched = 0
    for page in range(pages):
        params = dict(query=query, tags='comment', numericFilters=f'created_at_i>{cutoff}', hitsPerPage=100, page=page)
        data = fetch(API + '?' + urlencode(params))
        if not isinstance(data, dict) or not isinstance(data.get('hits'), list) or type(data.get('nbPages')) is not int or data['nbPages'] < 0:
            raise APIError('API returned an invalid response schema')
        hits = data['hits']
        if len(hits) > 100:
            raise APIError('API returned more than 100 hits in one page')
        fetched += 1
        for hit in hits:
            if not isinstance(hit, dict) or not isinstance(hit.get('objectID'), str) or not hit['objectID'].isascii() or not hit['objectID'].isdigit() or not isinstance(hit.get('comment_text'), (str, type(None))):
                raise APIError('API returned an invalid comment')
            identifier = hit['objectID']
            if identifier in seen:
                continue
            seen.add(identifier)
            for item in extract(hit.get('comment_text') or ''):
                if kind != 'all' and item[0] != kind:
                    continue
                counts[item] = counts.get(item, 0) + 1
                examples.setdefault(item, f'https://news.ycombinator.com/item?id={identifier}')
        if not hits or page + 1 >= data['nbPages']:
            break
    items = [dict(kind=k, url=u, comments=n, example_comment=examples[(k, u)]) for (k, u), n in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]]
    return dict(items=items, sampling=dict(query=query, kind=kind, days=days, cutoff_unix=cutoff, requested_pages=pages, fetched_pages=fetched, hits_per_page=100, scanned_comments=len(seen), limit=limit, warning=WARNING))
