import click
import json
import os
import re
import requests
import sys
import time

from lxml import html
from urllib.parse import unquote, urljoin

class Scraper:

    def __init__(self, save_location, base_url):
        self.save_location = save_location
        os.makedirs(self.save_location, exist_ok=True)
        self.s = requests.Session()
        #
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        self.base_url = base_url.rstrip('/') + '/'
        self.current_url = self.base_url

        self.tree = None
        self.path = None

        self.exclude = ["mini_", "normal_", "thumb_"]
        self.seen = {}

        self.count = 1
        self.total = 0
        
        # cache for resume
        self.cache_path = os.path.join(self.save_location, 'CopperKeep_cache.jsonl')
        self.cache = {}
        self._load_cache()


    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            e = json.loads(line)
                            self.cache[e['url']] = e
                        except:
                            pass
            except:
                pass

    def _log(self, url, path, size, status):
        entry = {"url": url, "file": os.path.relpath(path, self.save_location).replace("\\", "/"), "size": size, "status": status, "ts": time.time()}
        self.cache[url] = entry
        try:
            with open(self.cache_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except:
            pass

    def build_url(self, link):
        # use the last loaded page as base to survive redirects
        base = getattr(self, 'current_url', self.base_url)
        return urljoin(base, link)

    def set_html_tree(self, url):
        r = self.s.get(url, timeout=30, allow_redirects=True)
        r.raise_for_status()
        self.current_url = r.url
        self.tree = html.fromstring(r.content)

    def set_page_path(self, title=None, subtitle=None):
        try:
            temp = self.tree.xpath('//td[@class="tableh1"]//a/text()')
            if not temp:
                temp = self.tree.xpath('//td[@class="statlink"]//a/text()')
            if not temp:
                temp = self.tree.xpath('//h1//text() | //div[@class="breadcrumb"]//a/text()')
            if not temp:
                temp = ["download"]

            if title is not None:
                if temp:
                    temp[-1] = title
                else:
                    temp = [title]
            if subtitle is not None:
                if temp:
                    temp[-1] = temp[-1] + " - " + subtitle
                else:
                    temp = [subtitle]

            self.path = []
            for x in temp:
                if not x or not x.strip():
                    continue
                clean = x.replace("/", " & ").replace(":", " -").replace("?", "").replace('"', "").replace("|", "-").replace(">", "-").replace("<", "-").replace("*", "").replace("’", "'").replace("  ", " ").replace("	", "").strip(".").strip()
                if clean:
                    self.path.append(clean)
            if not self.path:
                self.path = ["download"]
        except Exception as e:
            print(f"Warning: set_page_path failed ({e}), using default")
            self.path = ["download"]

    def get_album_size(self):
        # try multiple xpaths
        texts = self.tree.xpath('//td[@class="tableh1" and @valign="middle"]//text()') + self.tree.xpath('//span[@class="tableh1-small"]//text()')
        for t in texts:
            m = re.search(r'(\d+)\s+files?', t, re.I)
            if m:
                items = int(m.group(1))
                return max(len(str(items)), 3)
        return 3

    def get_page_count(self):
        texts = self.tree.xpath('//td[@class="tableh1" and @valign="middle"]//text()') + self.tree.xpath('//span[@class="tableh1-small"]//text()')
        for t in texts:
            # old format: "12 files on 3 pages"
            m = re.search(r'on\s+(\d+)\s+pages?', t, re.I)
            if m:
                return int(m.group(1))
            # new format sometimes only shows pages in pagination
            m2 = re.search(r'(\d+)\s+pages?', t, re.I)
            if m2:
                return int(m2.group(1))
        # fallback: look for pagination links
        pages = self.tree.xpath('//a[contains(@href,"page=")]/@href')
        if pages:
            nums = [int(re.search(r'page=(\d+)', p).group(1)) for p in pages if re.search(r'page=(\d+)', p)]
            return max(nums) if nums else 1
        return 1

    def get_image_links(self):
        # 2021 xpath broke on Coppermine 1.6
        links = self.tree.xpath('//a/img[contains(@class,"image") and contains(@class,"thumbnail")]/@src')
        if not links:
            links = self.tree.xpath('//img[contains(@class,"image")]/@data-src')
        if not links:
            links = self.tree.xpath('//img[contains(@class,"thumbnail")]/@src')
        # clean thumb prefixes
        cleaned = []
        for link in links:
            for j in self.exclude:
                link = link.replace(j, "")
            cleaned.append(link)
        return cleaned

    def album_page_saved(self, links):
        path = os.path.join(self.save_location, *self.path)
        if os.path.isdir(path):
            saved = set(os.listdir(path))
            for i, link in enumerate(links):
                ext = link.rpartition('.')[2] or 'jpg'
                fname = str(self.count + i).zfill(self.get_album_size()) + "." + ext
                if fname not in saved:
                    return False
            self.count += len(links)
            return True
        return False

    def get_album_page(self, url, page):
        if page > 1:
            self.set_html_tree(url)
        links = self.get_image_links()
        if not links:
            print("|   |-- PAGE " + str(page) + " - NO IMAGES FOUND (xpath changed?)")
            return
        # keep fast skip if whole page already on disk
        if self.album_page_saved(links):
            print("|   |-- PAGE " + str(page) + " - SKIPPED")
            return
        print("|   |-- PAGE " + str(page))
        images = [x.rpartition('/')[2] for x in links]
        for i, link in enumerate(links):
            image_url = self.build_url(link)
            ext = link.rpartition('.')[2] or 'jpg'
            filename = str(self.count).zfill(self.get_album_size()) + "." + ext
            location = os.path.join(self.save_location, *self.path, filename)

            # resume check
            cached = self.cache.get(image_url)
            if cached and cached.get('status') == 'downloaded' and os.path.exists(location):
                print(f"|   |   |-- skipping {images[i]} (cached)")
                self.count += 1
                continue

            try:
                t0 = time.time()
                r = self.s.get(image_url, timeout=30)
                r.raise_for_status()
                data = r.content
                dt = time.time() - t0
                size = len(data)
                speed = size / dt if dt > 0 else 0
                os.makedirs(os.path.dirname(location), exist_ok=True)
                with open(location, 'wb') as f:
                    f.write(data)
                print(f"|   |   |-- saving {images[i]} as {filename} [{size/1024:.1f} KB @ {speed/1024:.1f} KB/s]")
                self._log(image_url, location, size, 'downloaded')
                self.count += 1
                self.total += 1
            except Exception as e:
                print(f"|   |   |-- failed {images[i]}: {e}")
                self._log(image_url, location, 0, 'failed')
                continue

    def get_album(self, url, title=None, subtitle=None):
        self.count = 1
        self.set_html_tree(url)
        self.set_page_path(title, subtitle)
        print("SAVING\n|-- " + unquote(url) + "\n|-- " + "/".join(self.path))
        pages = self.get_page_count()
        for i in range(1, pages + 1):
            if i == 1:
                page_url = url
            else:
                sep = '&' if '?' in url else '?'
                page_url = f"{url}{sep}page={i}"
            self.get_album_page(page_url, i)

    def get_album_url(self, stat):
        url = stat.xpath('../../..//span[@class="alblink"]/a/@href')
        if not url:
            url = stat.xpath('..//a/@href')
        return self.build_url(url[0]) if url else None

    def get_album_title(self, stat):
        title = stat.xpath('../../..//span[@class="alblink"]/a/text()')
        if not title:
            title = stat.xpath('..//a/text()')
        album_title = title[0].strip() if title else "untitled"
        if album_title in self.seen:
            self.seen[album_title] += 1
            album_title += f" ({self.seen[album_title]})"
        else:
            self.seen[album_title] = 1
        return album_title

    def get_album_subtitle(self, stat):
        #
        album_subtitle = None
        try:
            strong = stat.xpath('../p[not(@class)]/strong/text()')
            strong = [x.replace(":", "").lower().strip() for x in strong] if strong else []
            details = stat.xpath('../p[not(@class)]/text()')
            if details:
                details = [x.replace("\r\n", "").strip() for x in details if x.strip() != ""][:2]
                while len(strong) < 2:
                    strong.append("")
                if not any(strong):
                    for j in range(len(details)):
                        if details[j].lower().startswith("from"):
                            details[j] = re.sub(r"^from\s*:*\s*", "", details[j], flags=re.I)
                            strong[0] = "from"
                        if details[j].lower().startswith("by"):
                            details[j] = re.sub(r"^by\s*:*\s*", "", details[j], flags=re.I)
                            strong[1] = "by"
                parts = []
                if len(details) > 0:
                    if strong[0]: parts.append(strong[0])
                    parts.append(details[0])
                if len(details) > 1:
                    if strong[1]: parts.append(strong[1])
                    parts.append(details[1])
                subtitle = " ".join(parts).strip()
                album_subtitle = subtitle if subtitle else None
        except Exception:
            album_subtitle = None
        return album_subtitle

    def scrape(self, start_url, ps=False):
        queue = [start_url]
        while queue:
            url = queue.pop()
            try:
                self.set_html_tree(url)
            except Exception as e:
                print(f"Failed to load {url}: {e}")
                continue
            self.set_page_path()
            print("SCRAPING\n|-- " + unquote(url) + "\n|-- " + "/".join(self.path))
            pages = self.get_page_count()
            if pages and "&page=" not in url and "?page=" not in url:
                self.seen = {}
                if pages > 1:
                    for i in range(pages, 1, -1):
                        sep = '&' if '?' in url else '?'
                        queue.append(f"{url}{sep}page={i}")
            cats = self.tree.xpath('//span[@class="catlink"]/a/@href')
            for cat in reversed(cats):
                queue.append(self.build_url(str(cat)))
            albums = self.tree.xpath('//p[@class="album_stat"]')
            for i in albums:
                if i.text and i.text.lower().strip() != "0 files":
                    album_url = self.get_album_url(i)
                    if not album_url:
                        continue
                    album_title = self.get_album_title(i)
                    album_subtitle = self.get_album_subtitle(i) if ps else None
                    self.get_album(album_url, album_title, album_subtitle)

    def start(self, start_url, ps=False):
        if "album" in start_url.lower() or "thumbnails.php?album=" in start_url:
            self.get_album(start_url)
        else:
            self.scrape(start_url, ps)

def main():
    if len(sys.argv) > 3:
        save_location, base_url, start_url = sys.argv[1:4]
        ps = len(sys.argv) > 4
    else:
        current = os.path.abspath(os.path.dirname(__file__))
        save_location = click.prompt("save_location", default=current)
        base_url = click.prompt("base_url")
        start_url = click.prompt("start_url")
        ps = click.confirm("ps")
    scraper = Scraper(save_location, base_url)
    start = time.time()
    scraper.start(start_url, ps=ps)
    print(f"{round(time.time()-start)} seconds")
    print(f"{scraper.total} images")

if __name__ == '__main__':
    main()
