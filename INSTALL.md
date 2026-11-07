# Install Rex's hnlinks

Install Python 3.10 or newer and Git first. Git is needed for the GitHub install URL; alternatively download the repository ZIP, extract it, and run `python -m pip install .` in that folder.

## Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install git+https://github.com/masterxhackerx420-oss/rex-hnlinks
.\.venv\Scripts\hnlinks.exe "python" --pages 1
```

No activation or execution-policy change required.

## macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install git+https://github.com/masterxhackerx420-oss/rex-hnlinks
.venv/bin/hnlinks "python" --pages 1
```

If Linux reports venv is unavailable, install your distribution's Python venv package. Do not use sudo pip.

## Usage

```sh
hnlinks "python" --kind github --days 30 --pages 3 --limit 10
hnlinks "physics" --kind arxiv --json
hnlinks --help
```

Use the full venv executable path above, or activate your environment to use `hnlinks` directly. A working HTTPS connection to hn.algolia.com is required. API errors exit nonzero: check connectivity and try later rather than looping requests. A clean empty sample is not an error. Uninstall using your environment's `python -m pip uninstall rex-hnlinks`.
