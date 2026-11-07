import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.error import URLError
from rex_hnlinks.core import extract, sample, APIError, fetch_page, MAX_BYTES
from rex_hnlinks.cli import main


def hit(id, text):
    return dict(objectID=str(id), comment_text=text)


class Behavior(unittest.TestCase):
    def test_github_normalization(self):
        self.assertEqual(extract('<a href="http://www.github.com/Owner/Repo.git/issues/2?a=1&amp;b=2">x</a> https://github.com/OWNER/REPO.'), {('github', 'https://github.com/owner/repo')})

    def test_reject_hosts_and_nonrepos(self):
        for url in ['https://github.com.evil.org/a/b', 'https://evilgithub.com/a/b', 'https://github.com/user', 'https://github.com/topics/python', 'https://github.com@evil.org/a/b', 'https://github.com/a/%1bboom', 'https://arxiv.org.evil/abs/2401.12345', 'https://github.com/a/b\x1b[31m']:
            with self.subTest(url=url):
                self.assertEqual(extract(url), set())

    def test_arxiv(self):
        self.assertEqual(extract('<a href="https://www.arxiv.org/pdf/2401.12345v2.pdf">paper</a> (https://arxiv.org/abs/hep-th/9901001v3). https://arxiv.org/pdf/2401.12345.pdf'), {('arxiv', 'https://arxiv.org/abs/2401.12345'), ('arxiv', 'https://arxiv.org/abs/hep-th/9901001')})

    def test_distinct_comments_and_pages(self):
        responses = iter([dict(hits=[hit(1, 'https://github.com/A/B https://github.com/a/b'), hit(2, 'https://arxiv.org/abs/2401.12345')], nbPages=2), dict(hits=[hit(1, 'https://github.com/a/b'), hit(3, 'https://github.com/a/b')], nbPages=2)])
        result = sample('python', fetch=lambda url: next(responses), now=10000000)
        self.assertEqual([x['comments'] for x in result['items']], [2, 1])
        self.assertEqual(result['sampling']['scanned_comments'], 3)
        self.assertEqual(result['sampling']['fetched_pages'], 2)
        self.assertEqual(result['items'][0]['example_comment'], 'https://news.ycombinator.com/item?id=1')

    def test_query_cutoff_and_bound(self):
        urls = []
        def fetch(url):
            urls.append(url)
            return dict(hits=[hit(len(urls), '')], nbPages=500)
        sample('a & b', pages=10, days=2, now=200000, fetch=fetch)
        self.assertEqual(len(urls), 10)
        q = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(q, dict(query=['a & b'], tags=['comment'], numericFilters=['created_at_i>27200'], hitsPerPage=['100'], page=['0']))
        self.assertEqual(parse_qs(urlsplit(urls[-1]).query)['page'], ['9'])

    def test_stop_empty_and_end(self):
        for response in [dict(hits=[], nbPages=99), dict(hits=[hit(1, '')], nbPages=1)]:
            calls = []
            def fetch(url):
                calls.append(url)
                return response
            sample('x', fetch=fetch)
            self.assertEqual(len(calls), 1)

    def test_order_kind_and_limit(self):
        fetch = lambda url: dict(hits=[hit(1, 'https://github.com/z/z https://github.com/a/a https://arxiv.org/abs/2401.12345')], nbPages=1)
        result = sample('x', kind='github', limit=1, fetch=fetch)
        self.assertEqual([i['url'] for i in result['items']], ['https://github.com/a/a'])

    def test_invalid_response(self):
        for response in [[], {}, {'hits': 'bad', 'nbPages': 1}, {'hits': [dict(objectID='\x1b', comment_text='')], 'nbPages': 1}, {'hits': [hit(1, '')]*101, 'nbPages': 1}, {'hits': [], 'nbPages': True}]:
            with self.subTest(response=response), self.assertRaises(APIError):
                sample('x', fetch=lambda url: response)

    def test_network_failures(self):
        for error in [TimeoutError(), URLError('offline')]:
            with patch('rex_hnlinks.core.urlopen', side_effect=error), self.assertRaises(APIError):
                fetch_page('https://hn.algolia.com/api/v1/search_by_date')

    def test_response_size_and_bad_json(self):
        for raw in [b'bad json', b'x'*(MAX_BYTES+1)]:
            with patch('rex_hnlinks.core.urlopen') as opened:
                opened.return_value.__enter__.return_value.read.return_value = raw
                with self.assertRaises(APIError):
                    fetch_page('https://hn.algolia.com/api/v1/search_by_date')
                self.assertEqual(opened.call_args.kwargs['timeout'], 15)

    def test_cli_validation(self):
        for argv in [['x', '--pages', '11'], ['x', '--pages', '0'], ['x', '--days', '-1'], ['x', '--limit', '0'], [' '], ['x', '--days', 'oops']]:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(argv)
            self.assertEqual(exc.exception.code, 2)

    def test_cli_error(self):
        out, err = io.StringIO(), io.StringIO()
        with patch('rex_hnlinks.cli.sample', side_effect=APIError('API unavailable')), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(['x']), 1)
        self.assertEqual(out.getvalue(), '')
        self.assertIn('API unavailable', err.getvalue())

    def test_json_deterministic(self):
        expected = sample('x', now=10000000, fetch=lambda url: dict(hits=[], nbPages=0))
        outputs = []
        for _ in range(2):
            out = io.StringIO()
            with patch('rex_hnlinks.cli.sample', return_value=expected), contextlib.redirect_stdout(out):
                self.assertEqual(main(['x', '--json']), 0)
            outputs.append(out.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(json.loads(outputs[0]), expected)

    def test_text_title_empty_and_safe(self):
        out = io.StringIO()
        result = sample('\x1b[31m', now=10000000, fetch=lambda url: dict(hits=[], nbPages=0))
        with patch('rex_hnlinks.cli.sample', return_value=result), contextlib.redirect_stdout(out):
            self.assertEqual(main(['x']), 0)
        self.assertIn("Rex's hnlinks", out.getvalue())
        self.assertIn('No matching links', out.getvalue())
        self.assertNotIn('\x1b', out.getvalue())


if __name__ == '__main__':
    unittest.main()
