# Rex's hnlinks

![Illustrated characters against a fiery sunset](docs/rex-hnlinks-banner.jpg)

Rank GitHub repositories and arXiv papers by distinct mentions in a bounded sample of Hacker News comments.

Requires Python 3.10+. No runtime dependencies. Nothing in comments is executed, and extracted links are never fetched.

```sh
pip install git+https://github.com/masterxhackerx420-oss/rex-hnlinks
hnlinks "python"
hnlinks "language models" --kind arxiv --days 30 --pages 3 --limit 10
hnlinks "python" --kind github --json
hnlinks --version
```

See [INSTALL.md](INSTALL.md) for isolated Windows/macOS/Linux installation.

## What it measures

Uses the documented public [Algolia HN Search API](https://hn.algolia.com/api): `search_by_date`, `tags=comment`, a full-text query, and `created_at_i` greater than the cutoff. Each request asks for 100 hits; `--pages` is bounded to 1–10 (default 3). `--days` defaults to 30 and `--limit` to 10; both must be positive integers. Pagination stops on an empty page or the reported last page. One 15-second timeout per request; no automatic retries. Responses over 4 MiB or malformed responses fail with a nonzero exit status.

Repeated links in one comment count once. Duplicate comment IDs across pages count once. GitHub links group case-insensitively at owner/repository level, including issue/subpage links. arXiv abs/pdf links group across versions, including legacy IDs. Each result includes one example HN comment URL. Ties sort by kind then canonical URL. JSON contains `items` and `sampling`, including actual fetched pages, distinct scanned comments, requested window, cutoff, and a warning.

**LIMITED SAMPLE:** mentions are not endorsements. Counts are not likes, points, quality scores, or a comprehensive ranking of HN. Newest-first search, indexing gaps, query semantics, deleted comments, API search limits and changing pages can omit relevant comments. A zero result means no recognized links in this sample, not no mentions on HN. Canonicalization is syntactic, not proof a repository or paper exists. No secrets or API keys required; your search phrase is sent to Algolia. The documented rate limit is 10,000 requests/hour/IP; this tool makes at most 10 requests per invocation. Be considerate on shared connections.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Tests mock the API and require no network access. MIT licensed.
