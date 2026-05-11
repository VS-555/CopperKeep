# CopperKeep

A fast, resumable downloader for Coppermine Photo Galleries.

CopperKeep is the 2026 rebuild of the classic "long-live" scraper — fixed for modern gallery themes, with a proper cache and resume system.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **One-click GUI** – paste a gallery URL, choose a folder, go
- **Resume support** – creates `CopperKeep_cache.jsonl` in your download folder; restarts skip already-downloaded files
- **Live stats** – shows file size and download speed: `[121.7 KB @ 845.3 KB/s]`
- **2026 fixes** – handles www→non-www redirects, lazy-load images, and Windows-illegal characters (`> < : * | ? "`)
- **No re-scrape** – only missing files are fetched on subsequent runs

## Quick Start

```bash
pip install -r requirements.txt
python src/gui.py
```

Paste a Coppermine URL like:
```
https://emmastoneweb.com/gallery/
```

## Build Windows EXE

```bash
pyinstaller build.spec --clean
```
Output: `dist/CopperKeep.exe`

## How Resume Works

1. First run creates `your_folder/CopperKeep_cache.jsonl`
2. Each image logs: URL, local path, size, status
3. Next run loads the cache and prints `skipping ... (cached)`

Delete the cache file to force a full re-download.

## Project Structure
```
CopperKeep/
├── src/
│   ├── gui.py       # Tkinter GUI
│   └── scraper.py   # Core downloader with cache
├── assets/
│   └── icon.ico
├── requirements.txt
└── build.spec
```

## Disclaimer

For personal archival of publicly accessible galleries only. Respect robots.txt and site terms.

## License

MIT © 2026
