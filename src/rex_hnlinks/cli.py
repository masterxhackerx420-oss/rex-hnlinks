"""Command-line interface for Rex's hnlinks."""
import argparse
import json
import sys
from . import __version__
from .core import APIError, sample


def positive(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('must be a positive integer') from None
    if number < 1:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def page_count(value):
    number = positive(value)
    if number > 10:
        raise argparse.ArgumentTypeError('must be between 1 and 10')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rex's hnlinks — rank links by distinct comment mentions, not endorsements.")
    parser.add_argument('query', help='HN comment search phrase')
    parser.add_argument('--kind', choices=['github', 'arxiv', 'all'], default='all')
    parser.add_argument('--days', type=positive, default=30)
    parser.add_argument('--limit', type=positive, default=10)
    parser.add_argument('--pages', type=page_count, default=3, help='1–10 pages, 100 hits each (default: 3)')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args(argv)
    if not args.query.strip():
        parser.error('query must not be blank')
    try:
        result = sample(args.query, kind=args.kind, days=args.days, limit=args.limit, pages=args.pages)
    except (APIError, ValueError) as exc:
        print(f'hnlinks: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        meta = result['sampling']
        print("Rex's hnlinks")
        print(f"Scanned {meta['scanned_comments']} distinct comments in {meta['fetched_pages']} page(s); requested window: {args.days} days.")
        print(meta['warning'])
        for item in result['items']:
            print(f"{item['comments']:>4} comments  {item['url']}\n     example: {item['example_comment']}")
        if not result['items']:
            print('No matching links in this sample.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
