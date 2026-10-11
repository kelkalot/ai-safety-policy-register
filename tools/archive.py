#!/usr/bin/env python3
"""Download and keep local copies of every source in the register.

    python3 tools/archive.py

For each record in data/records.json this script:

  1. downloads the official URL (checking robots.txt first),
  2. if that is an HTML page, also downloads up to N PDFs it links to on the
     same official site (usually the legal text itself),
  3. downloads the secondary URL as a backup,
  4. stores every file under archive/<ID>/<YYYY-MM-DD>/ with a SHA-256 hash,
     the UTC retrieval time, the final URL after redirects and the HTTP status,
  5. writes the result into the record's "local_copy" block and flags anything
     that did not work (HTTP errors, timeouts, robots.txt blocks, bot-check or
     JavaScript-only pages, pages that no longer mention the document),
  6. regenerates data/records.js, data/records.csv and data/register.sqlite,
  7. writes archive/needs-attention.txt, the list of records that still need a
     human decision. The archiver never contacts anyone; what to do about a
     flagged record is left to the person running it.

Re-running is safe. Unchanged files are not stored twice; a changed source is
saved as a new dated snapshot and the record is marked "changed". If a source
that was archived before now fails, the earlier copy is kept and the record is
flagged for review.

Other modes:
  --verify          re-hash every local file and flag missing or modified ones
  --dry-run         list what would be fetched, download nothing
  --browser         retry failed or suspicious pages in headless Chromium
                    (needs: pip install playwright && playwright install chromium)

Standard library only (Python 3.8+), except the optional --browser mode.
"""
import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import html
import json
import re
import socket
import ssl
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402  (same folder)

TOOL_VERSION = "1.0"
AGENT_TOKEN = "AISafetyPolicyRegister-Archiver"
ROOT = build.ROOT
ARCHIVE = ROOT / "archive"
ATTENTION_FILE = ARCHIVE / "needs-attention.txt"

ROLE_LABELS = {
    "official": "Official source",
    "document": "Linked document (PDF)",
    "secondary": "Secondary source",
    "official-rendered": "Official source, rendered in a browser",
    "official-print": "Official source, printed to PDF by a browser",
}

BOT_PATTERNS = [
    (r"just a moment|checking your browser|cf-browser-verification|cf_chl_|attention required! \| cloudflare",
     "The site returned a bot-check page instead of the document"),
    (r"captcha|are you a robot|are you human|verify you are human|unusual traffic",
     "The site returned a CAPTCHA or bot-check page"),
    (r"access denied|request unsuccessful|incapsula incident|request rejected|forbidden",
     "The site returned an access-denied page"),
    (r"incident id:|before proceeding|additional security check|verifying you are human|ddos protection",
     "The site returned a bot-check page instead of the document"),
    (r"enable javascript|javascript is (?:required|disabled|not enabled)|requires javascript|turn on javascript",
     "The page says it needs JavaScript; the saved copy may be empty"),
]

# Markers of JavaScript bot-check pages served by web application firewalls. They carry almost no
# visible text, so they are checked against the raw HTML.
WAF_PATTERN = re.compile(r"awswaf|gokuprops|challenge-platform|cf-challenge|/cdn-cgi/challenge|_incapsula_resource|"
                         r"datadome|px-captcha|distil_r_captcha|bm-verify|queue-it\.net|hcaptcha\.com|recaptcha/api", re.I)

# Single-page-application shells: the HTML carries a mount point and the content arrives by script.
APP_SHELL_PATTERN = re.compile(r"<app-root|\bng-app\b|ng-version=|id=\"root\"|id=\"app\"|id=\"__next\"|data-reactroot|__NEXT_DATA__|id=\"__nuxt\"", re.I)

STOPWORDS = set("""
the and for with from that this into under over about their which other these those such shall upon
act law laws rules rule order measures measure provisions provision regulation regulations decree
national general article annex part code policy guidelines guideline framework strategy plan report
artificial intelligence system systems
""".split())

GENERIC_SLD = {"co", "com", "org", "net", "ac", "edu", "or", "ne"}


# ----------------------------------------------------------------------------- helpers

def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def iri_to_uri(url):
    """Percent-encode non-ASCII paths and IDNA-encode hosts so urllib accepts the URL."""
    p = urllib.parse.urlsplit(url.strip())
    host = p.hostname or ""
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    netloc = host + (":%d" % p.port if p.port else "")
    path = urllib.parse.quote(p.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?-._~")
    return urllib.parse.urlunsplit((p.scheme, netloc, path, query, ""))


def site_key(host):
    parts = (host or "").lower().split(".")
    if len(parts) >= 3 and parts[-2] in GENERIC_SLD:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_site(a, b):
    ka = site_key(urllib.parse.urlsplit(a).hostname or "")
    hb = (urllib.parse.urlsplit(b).hostname or "").lower()
    return hb == ka or hb.endswith("." + ka)


def ext_for(content_type, body, url):
    if body[:5] == b"%PDF-":
        return ".pdf"
    ct = (content_type or "").split(";")[0].strip().lower()
    table = {
        "text/html": ".html", "application/xhtml+xml": ".html", "application/pdf": ".pdf",
        "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml", "application/json": ".json",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    if ct in table:
        return table[ct]
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if suffix in {".html", ".htm", ".pdf", ".txt", ".xml", ".json", ".doc", ".docx"}:
        return ".html" if suffix == ".htm" else suffix
    if body.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        return ".html"
    return ".bin"


def decode_html(body, content_type):
    m = re.search(r"charset=([\w\-]+)", content_type or "", re.I)
    enc = m.group(1) if m else None
    if not enc:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w\-]+)", body[:4096], re.I)
        enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


class _TextAndLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.title = [], [], ""
        self._skip = 0
        self._in_title = False
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and a.get("href"):
            self._a = [a["href"], []]
        elif tag in ("iframe", "embed") and a.get("src"):
            self.links.append((a["src"], ""))
        elif tag == "object" and a.get("data"):
            self.links.append((a["data"], ""))
        elif tag == "link" and "pdf" in (a.get("type") or "") and a.get("href"):
            self.links.append((a["href"], "pdf"))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._a:
            self.links.append((self._a[0], " ".join(self._a[1]).strip()))
            self._a = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
        self.text.append(data)
        if self._a is not None:
            self._a[1].append(data.strip())


def parse_html(text):
    p = _TextAndLinks()
    try:
        p.feed(text)
        p.close()
    except Exception:  # malformed markup: keep what was parsed
        pass
    visible = re.sub(r"\s+", " ", " ".join(p.text)).strip()
    return visible, p.links, re.sub(r"\s+", " ", p.title).strip()


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) >= 4 and w not in STOPWORDS]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def text_digest(body, content_type):
    """SHA-256 of the visible text of an HTML page, so that pages whose markup or scripts change on
    every request (session tokens, ads, timestamps in comments) are not stored again and again."""
    text, _, _ = parse_html(decode_html(body, content_type))
    text = re.sub(r"\b[0-9a-f]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}\b|\b[0-9a-f]{16,}\b", "", text, flags=re.I)
    return sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8"))


def describe_network_error(exc):
    """Turn a urllib/socket exception into (message, code) that says what actually went wrong."""
    reason = getattr(exc, "reason", exc)
    s = str(reason)
    if isinstance(reason, socket.gaierror) or "nodename nor servname" in s or "Name or service not known" in s \
            or "getaddrinfo" in s or "Temporary failure in name resolution" in s:
        return "DNS lookup failed, so the site could not be reached from this machine (try another network, or save the document by hand)", "dns"
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in s:
        return "The connection timed out; the site may block this network", "timeout"
    if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in s:
        return "The site's TLS certificate could not be verified", "tls"
    if "refused" in s.lower():
        return "The connection was refused by the server", "network"
    return "Connection failed: %s" % s, "network"


class _Redirects(urllib.request.HTTPRedirectHandler):
    """Follow HTTP 308 like 307. Python before 3.11 treats 308 as an error."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, 307 if code == 308 else code, msg, headers, newurl)

    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_307(req, fp, code, msg, headers)


# ----------------------------------------------------------------------------- fetching

class Result:
    def __init__(self, url, ok, status=None, final_url=None, headers=None, body=b"", error=None, code=None,
                 method="http"):
        self.url, self.ok, self.status, self.final_url = url, ok, status, final_url
        self.headers = headers or {}
        self.body, self.error, self.code, self.method = body, error, code, method

    @property
    def content_type(self):
        return self.headers.get("content-type", "")

    @property
    def is_html(self):
        return ext_for(self.content_type, self.body, self.final_url or self.url) == ".html"

    @property
    def is_pdf(self):
        return self.body[:5] == b"%PDF-"


class TooLarge(Exception):
    pass


class Fetcher:
    def __init__(self, user_agent, timeout, retries, delay, max_bytes, respect_robots):
        self.ua, self.timeout, self.retries, self.delay = user_agent, timeout, retries, delay
        self.max_bytes, self.respect_robots = max_bytes, respect_robots
        self.host_locks = defaultdict(threading.Lock)
        self.last_hit = {}
        self.robots = {}
        self.robots_lock = threading.Lock()
        self.opener = urllib.request.build_opener(
            _Redirects(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            urllib.request.HTTPCookieProcessor(),
        )

    def _raw(self, url):
        req = urllib.request.Request(url, headers={
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "en;q=1.0, *;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        })
        with self.opener.open(req, timeout=self.timeout) as resp:
            chunks, size = [], 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_bytes:
                    raise TooLarge()
                chunks.append(chunk)
            body = b"".join(chunks)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            enc = headers.get("content-encoding", "").lower()
            if enc == "gzip":
                body = gzip.decompress(body)
            elif enc == "deflate":
                try:
                    body = zlib.decompress(body)
                except zlib.error:
                    body = zlib.decompress(body, -zlib.MAX_WBITS)
            return resp.status, resp.geturl(), headers, body

    def _robots_for(self, url):
        p = urllib.parse.urlsplit(url)
        base = "%s://%s" % (p.scheme, p.netloc)
        with self.robots_lock:
            if base in self.robots:
                return self.robots[base]
        rp = urllib.robotparser.RobotFileParser()
        note, code = None, "robots"
        with self.host_locks[p.netloc]:
            self._pace(p.netloc)
            try:
                status, _, _, body = self._raw(base + "/robots.txt")
                rp.parse(body.decode("utf-8", errors="replace").splitlines() if status == 200 else [])
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    rp.parse([])  # RFC 9309: robots.txt unavailable (4xx) means no restrictions
                else:
                    rp.parse(["User-agent: *", "Disallow: /"])
                    note = "robots.txt returned HTTP %d, which RFC 9309 treats as 'do not crawl'" % e.code
            except Exception as e:  # unreachable
                rp.parse(["User-agent: *", "Disallow: /"])
                msg, code = describe_network_error(e)
                note = "%s. robots.txt could not be checked, which RFC 9309 treats as 'do not crawl'" % msg
            finally:
                self.last_hit[p.netloc] = time.monotonic()
        with self.robots_lock:
            self.robots[base] = (rp, note, code)
        return rp, note, code

    def _pace(self, host):
        wait = self.delay - (time.monotonic() - self.last_hit.get(host, 0))
        if wait > 0:
            time.sleep(wait)

    def get(self, url):
        try:
            url = iri_to_uri(url)
        except Exception as e:
            return Result(url, False, error="The URL is malformed (%s)" % e, code="bad-url")
        if not url.lower().startswith(("http://", "https://")):
            return Result(url, False, error="Not an http(s) URL", code="bad-url")
        if self.respect_robots:
            rp, note, rcode = self._robots_for(url)
            if not rp.can_fetch(AGENT_TOKEN, url):
                return Result(url, False, error=note or "The site's robots.txt does not allow automated downloads of this page",
                              code=rcode)
        host = urllib.parse.urlsplit(url).netloc
        last_err = None
        for attempt in range(self.retries + 1):
            with self.host_locks[host]:
                self._pace(host)
                try:
                    status, final, headers, body = self._raw(url)
                    return Result(url, True, status, final, headers, body)
                except urllib.error.HTTPError as e:
                    msg = "HTTP %d %s" % (e.code, e.reason or "")
                    if e.code in (301, 302, 303, 307, 308):
                        msg = "HTTP %d redirect without a usable Location header; the site probably needs JavaScript or cookies" % e.code
                    last_err = Result(url, False, status=e.code, error=msg, code="http")
                    retry = e.code in (408, 425, 429, 500, 502, 503, 504)
                except TooLarge:
                    return Result(url, False, error="File is larger than the %d MB limit" % (self.max_bytes >> 20),
                                  code="too-large")
                except (socket.timeout, TimeoutError):
                    last_err = Result(url, False, error="Timed out after %ds" % self.timeout, code="timeout")
                    retry = True
                except (urllib.error.URLError, ConnectionError, ssl.SSLError, OSError) as e:
                    msg, code = describe_network_error(e)
                    if code == "tls":
                        return Result(url, False, error=msg, code=code)
                    if code == "timeout":
                        msg = "Timed out after %ds; the site may block this network" % self.timeout
                    last_err = Result(url, False, error=msg, code=code)
                    retry = code != "dns"
                finally:
                    self.last_hit[host] = time.monotonic()
            if not retry or attempt == self.retries:
                break
            time.sleep(3 * (attempt + 1) ** 2)
        return last_err


# ----------------------------------------------------------------------------- per-record work

def inspect_html(res, rec):
    """Return a list of warnings about an HTML page that downloaded with HTTP 200."""
    warnings = []
    text, _, title = parse_html(decode_html(res.body, res.content_type))
    low_title, low_text = title.lower(), text.lower()
    for pat, msg in BOT_PATTERNS:
        if re.search(pat, low_title) or (len(text) < 3000 and re.search(pat, low_text)):
            warnings.append(msg)
            break
    raw_head = decode_html(res.body[:300000], res.content_type) if len(text) < 2500 else ""
    if len(text) < 2500 and not warnings and APP_SHELL_PATTERN.search(raw_head) and not WAF_PATTERN.search(raw_head):
        warnings.append("The page is a JavaScript application shell; the saved copy holds only the site's navigation, not the document")
    if len(text) < 600 and not warnings:
        if WAF_PATTERN.search(raw_head):
            warnings.append("The site returned a JavaScript bot-check page (web application firewall) instead of the document")
        else:
            warnings.append("The page has very little readable text (%d characters); it probably needs JavaScript" % len(text))
    if not warnings:
        hay = low_text[:400000]
        best, checked = 0.0, False
        for cand in (rec.get("title"), rec.get("short_title")):
            ws = set(words(cand))
            if len(ws) >= 3:
                checked = True
                best = max(best, sum(1 for w in ws if w in hay) / len(ws))
        orig = (rec.get("original_title") or "").strip()
        if orig and orig[:10].lower() in hay:
            best = 1.0
        ident = rec.get("official_identifier") or ""
        nums = [n for n in re.findall(r"\d[\d/.\-]{2,}\d", ident) if len(n) >= 4]
        if any(n.lower() in hay for n in nums):
            best = 1.0
        if checked and best < 0.25:
            warnings.append("The page barely mentions the document's title; check that the URL still points to this document")
    return warnings, text


def pdf_candidates(res, rec, limit):
    if limit <= 0:
        return []
    _, links, _ = parse_html(decode_html(res.body, res.content_type))
    base = res.final_url or res.url
    title_words = set(words(rec.get("title")) + words(rec.get("short_title")))
    ident_nums = [n for n in re.findall(r"\d{3,}", rec.get("official_identifier") or "")]
    seen, scored = set(), []
    for pos, (href, text) in enumerate(links):
        href = (href or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "#", "tel:")):
            continue
        url = urllib.parse.urljoin(base, href).split("#")[0]
        if url in seen or not url.lower().startswith(("http://", "https://")):
            continue
        lu, lt = urllib.parse.unquote(url).lower(), (text or "").lower()
        path = urllib.parse.urlsplit(lu).path
        is_pdf = path.endswith(".pdf") or "/pdf/" in lu or re.search(r"[?&](format|type|rendition)=pdf", lu) \
            or "pdf" in lt
        if not is_pdf or not same_site(base, url):
            continue
        seen.add(url)
        score = (4 if path.endswith(".pdf") else 0) + (2 if "pdf" in lt else 0)
        hay = lu + " " + lt
        score += min(6, sum(1 for w in title_words if w in hay))
        if any(n in hay for n in ident_nums):
            score += 3
        if re.search(r"(^|[/_\-=.])en([/_\-.&]|$)", lu) or "english" in lt:
            score += 2
        if re.search(r"factsheet|fact-sheet|infographic|summary|press|brochure|poster", hay):
            score -= 2
        if re.search(r"accessib|certificat|veto[- ]message|signing[- ]message|privacy[- ]policy|terms", hay):
            continue  # site boilerplate or another bill's message, never the instrument
        if score <= 0:
            continue  # a PDF whose link says nothing about this document is more likely noise than the text
        scored.append((-score, pos, url))
    scored.sort()
    return [u for _, _, u in scored[:limit]]


class RecordJob:
    """Collects everything one record's run produced; finalise() turns it into local_copy."""

    def __init__(self, rec, run_date, run_time):
        self.rec = rec
        self.run_date, self.run_time = run_date, run_time
        prev = rec.get("local_copy") or {}
        self.prev_files = {f.get("role_key"): f for f in prev.get("files") or [] if f.get("role_key")}
        self.prev_attempts = prev.get("attempts") or []
        self.files, self.attempts, self.notes = [], [], []
        self.official_ok = False
        self.official_warnings = []
        self.official_error = None
        self.unusable = None  # set when this run's download was a bot-check/empty page and an earlier clean copy is kept
        self.need_browser = False

    # -- storage
    def store(self, role_key, role, res, warning=None):
        body = res.body
        digest = sha256(body)
        prev = self.prev_files.get(role_key)
        now = iso(utcnow())
        if prev and prev.get("sha256") == digest and (ROOT / prev.get("path", "")).is_file():
            f = dict(prev)
            f.update({"last_checked": now, "changed": False, "stale": False, "warning": warning,
                      "http_status": res.status, "final_url": res.final_url or res.url, "integrity": "ok"})
            self.files.append(f)
            return f
        ext = ext_for(res.content_type, body, res.final_url or res.url)
        tdigest = text_digest(body, res.content_type) if ext == ".html" else None
        if prev and tdigest and (ROOT / prev.get("path", "")).is_file() and prev.get("path", "").endswith(".html"):
            prev_td = prev.get("text_sha256") or text_digest((ROOT / prev["path"]).read_bytes(),
                                                               prev.get("content_type") or "text/html")
            if prev_td == tdigest:
                # Only markup or scripts differ; the readable content is the same, so keep the earlier copy.
                f = dict(prev)
                f.update({"last_checked": now, "changed": False, "stale": False, "warning": warning,
                          "http_status": res.status, "final_url": res.final_url or res.url, "integrity": "ok",
                          "text_sha256": prev_td})
                self.files.append(f)
                return f
        folder = ARCHIVE / self.rec["id"] / self.run_date
        folder.mkdir(parents=True, exist_ok=True)
        name = role_key + ext
        n = 2
        while (folder / name).exists() and sha256((folder / name).read_bytes()) != digest:
            name = "%s-%d%s" % (role_key, n, ext)
            n += 1
        (folder / name).write_bytes(body)
        rel = (folder / name).relative_to(ROOT).as_posix()
        self._append_sums(folder, name, digest)
        f = {
            "role_key": role_key, "role": role, "label": ROLE_LABELS.get(role, role), "path": rel,
            "url": res.url, "final_url": res.final_url or res.url, "http_status": res.status,
            "content_type": (res.content_type or "").split(";")[0] or None, "bytes": len(body), "sha256": digest,
            "text_sha256": tdigest,
            "retrieved_at": now, "last_checked": now, "method": res.method,
            "last_modified": res.headers.get("last-modified"), "etag": res.headers.get("etag"),
            "changed": bool(prev), "previous_sha256": prev.get("sha256") if prev else None,
            "previous_path": prev.get("path") if prev else None, "stale": False, "warning": warning,
            "integrity": "ok",
        }
        self.files.append(f)
        return f

    @staticmethod
    def _append_sums(folder, name, digest):
        sums = folder / "SHA256SUMS"
        lines = sums.read_text(encoding="utf-8").splitlines() if sums.exists() else []
        lines = [l for l in lines if not l.endswith("  " + name)] + ["%s  %s" % (digest, name)]
        sums.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def keep_previous(self, role_key, error):
        prev = self.prev_files.get(role_key)
        if prev and (ROOT / prev.get("path", "")).is_file():
            f = dict(prev)
            f.update({"stale": True, "last_failed": iso(self.run_time), "last_error": error})
            self.files.append(f)
            return True
        return False

    def attempt(self, role, res):
        self.attempts.append({
            "role": role, "url": res.url, "attempted_at": iso(utcnow()), "ok": bool(res.ok),
            "http_status": res.status, "error": res.error, "method": res.method,
        })

    # -- outcome
    def finalise(self):
        rec = self.rec
        stale = [f for f in self.files if f.get("stale")]
        fresh = [f for f in self.files if not f.get("stale")]
        has_official = any(f["role_key"] in ("official", "official-rendered") for f in fresh)
        has_any_official = any(f["role_key"].startswith("official") for f in self.files)
        has_secondary = any(f["role_key"] == "secondary" for f in self.files)
        flags = []
        if not rec.get("official_url"):
            if has_secondary:
                status = "partial"
                flags.append("No official URL is recorded; only the secondary source was saved.")
            else:
                status = "no-url" if not rec.get("secondary_url") else "failed"
                flags.append("No official URL is recorded, so nothing official could be archived."
                             if status == "no-url" else "No official URL, and the secondary source failed: %s"
                             % (self.official_error or "unknown error"))
        elif has_official and not self.official_warnings:
            status = "archived"
        elif has_official:
            status = "archived-review"
            flags.extend(self.official_warnings)
        elif has_any_official:  # only an earlier copy is left
            status = "archived-review"
            kept = ", ".join(sorted({f["retrieved_at"][:10] for f in stale if f["role_key"].startswith("official")}))
            if self.unusable:
                flags.append("This run's download of the official page was not usable (%s), so the clean copy from %s "
                             "is kept." % (self.unusable, kept))
            else:
                flags.append("The official source could not be downloaded this time (%s). The copy from %s is kept; "
                             "the source may have moved or been taken down." % (self.official_error, kept))
        elif has_secondary:
            status = "partial"
            flags.append("The official source could not be downloaded (%s); only the secondary source was saved."
                         % self.official_error)
        else:
            status = "failed"
            flags.append("The official source could not be downloaded: %s." % (self.official_error or "unknown error"))
        flags.extend(self.notes)
        if status == "archived" and any(f["role_key"].startswith(("official", "document")) for f in stale):
            status = "archived-review"  # a stale secondary is noted in the flag but does not need a review
        if any(f.get("changed") for f in fresh):
            flags.append("A source changed since the previous snapshot; both versions are kept.")
        flags = [f.strip() for f in flags if f and f.strip()]
        flags = [f if f.endswith((".", "!", "?")) else f + "." for f in flags]
        history = (self.prev_attempts + self.attempts)[-30:]
        rec["local_copy"] = {
            "status": status,
            "flag": " ".join(flags) or None,
            "last_attempt": iso(self.run_time),
            "files": sorted(self.files, key=lambda f: ["official", "official-rendered", "official-print",
                                                        "document", "secondary"].index(f["role"])
                            if f["role"] in ROLE_LABELS else 9),
            "attempts": history,
        }
        return status


def run_http(job, fetcher, args):
    rec = job.rec
    job.run_time = utcnow()
    url = rec.get("official_url")
    if url:
        res = fetcher.get(url)
        job.attempt("official", res)
        if res.ok and res.status and res.status < 400 and res.body:
            warnings = []
            if res.is_html:
                warnings, _ = inspect_html(res, rec)
            prev = job.prev_files.get("official")
            if warnings and prev and not prev.get("warning") and (ROOT / prev.get("path", "")).is_file():
                # A bot-check or empty page must not replace a clean copy from an earlier run.
                job.unusable = "; ".join(warnings)
                job.official_error = job.unusable
                for key in [k for k in job.prev_files if k.startswith(("official", "document-"))]:
                    job.keep_previous(key, job.unusable)
                job.need_browser = True
                warnings = []
            else:
                job.store("official", "official", res, "; ".join(warnings) or None)
                job.official_ok = True
                job.official_warnings = warnings
                if warnings:
                    job.need_browser = True
            if res.is_html and args.pdfs > 0 and not warnings and not job.unusable:
                cands = pdf_candidates(res, rec, args.pdfs)
                for i, link in enumerate(cands, 1):
                    r2 = fetcher.get(link)
                    job.attempt("document", r2)
                    key = "document-%d" % i
                    if r2.ok and r2.is_pdf:
                        job.store(key, "document", r2)
                    elif r2.ok:
                        job.notes.append("A linked file (%s) was not a PDF and was skipped." % link)
                    elif job.keep_previous(key, r2.error):
                        job.notes.append("A linked PDF saved earlier can no longer be downloaded (%s: %s); "
                                         "the earlier copy is kept." % (link, r2.error))
                    else:
                        job.notes.append("A linked PDF could not be downloaded (%s: %s)." % (link, r2.error))
        else:
            if res.ok and not res.body:
                res.error = "The server returned an empty response"
            job.official_error = res.error or ("HTTP %s" % res.status)
            for key in [k for k in job.prev_files if k.startswith(("official", "document-"))]:
                job.keep_previous(key, job.official_error)
            job.need_browser = res.code not in ("robots", "bad-url", "dns", "timeout")
    sec = rec.get("secondary_url")
    if sec and not args.no_secondary:
        r3 = fetcher.get(sec)
        job.attempt("secondary", r3)
        sec_warnings = inspect_html(r3, rec)[0] if r3.ok and r3.body and r3.is_html else []
        sec_warnings = [w for w in sec_warnings if not w.startswith("The page barely mentions")]  # a secondary may be about the document
        prev_sec = job.prev_files.get("secondary")
        if r3.ok and r3.body and sec_warnings and prev_sec and not prev_sec.get("warning") \
                and (ROOT / prev_sec.get("path", "")).is_file():
            job.keep_previous("secondary", "; ".join(sec_warnings))
            job.notes.append("The secondary source returned a bot-check or empty page this time (%s); the earlier copy is kept."
                             % "; ".join(sec_warnings))
        elif r3.ok and r3.body:
            job.store("secondary", "secondary", r3, "; ".join(sec_warnings) or None)
            if sec_warnings:
                job.notes.append("The secondary source is a bot-check or empty page (%s)." % "; ".join(sec_warnings))
        elif job.keep_previous("secondary", r3.error):
            job.notes.append("The secondary source can no longer be downloaded (%s); the earlier copy is kept."
                             % r3.error)
        else:
            job.notes.append("The secondary source could not be downloaded (%s)." % r3.error)
            if not url:
                job.official_error = r3.error
    return job


class BrowserFetcher:
    """Optional fallback: render a page in headless Chromium via Playwright (sequential)."""

    def __init__(self, timeout):
        from playwright.sync_api import sync_playwright  # noqa: import inside so the rest needs no deps
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.ctx = self.browser.new_context(accept_downloads=False)
        self.timeout = timeout * 1000

    def get(self, url):
        url = iri_to_uri(url)
        page = self.ctx.new_page()
        try:
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=self.timeout)
            except Exception as e:
                if "Download is starting" in str(e):
                    r = self.ctx.request.get(url, timeout=self.timeout)
                    return Result(url, r.ok, r.status, r.url, {k.lower(): v for k, v in r.headers.items()},
                                  r.body(), None if r.ok else "HTTP %d" % r.status, method="browser"), None
                return Result(url, False, error="Browser could not load the page: %s" % str(e).splitlines()[0],
                              code="browser", method="browser"), None
            status = resp.status if resp else None
            if status and status >= 400:
                return Result(url, False, status, page.url, error="HTTP %d (in browser)" % status, code="http",
                              method="browser"), None
            prev = -1  # single-page apps keep loading after "networkidle": wait until the visible text stops growing
            for _ in range(8):
                page.wait_for_timeout(1000)
                try:
                    n = len(page.inner_text("body") or "")
                except Exception:
                    break
                if n == prev:
                    break
                prev = n
            html_bytes = page.content().encode("utf-8")
            res = Result(url, True, status, page.url, {"content-type": "text/html; charset=utf-8"}, html_bytes,
                         method="browser")
            try:
                pdf = page.pdf(format="A4", print_background=True)
                pres = Result(url, True, status, page.url, {"content-type": "application/pdf"}, pdf,
                              method="browser")
            except Exception:
                pres = None
            return res, pres
        finally:
            page.close()

    def close(self):
        self.browser.close()
        self._pw.stop()


def run_browser(job, bf, fetcher, args):
    rec = job.rec
    url = rec.get("official_url")
    if args.respect_robots:
        rp, _, _ = fetcher._robots_for(iri_to_uri(url))
        if not rp.can_fetch(AGENT_TOKEN, iri_to_uri(url)):
            return
    res, pres = bf.get(url)
    job.attempt("official-rendered", res)
    if not res.ok:
        job.notes.append("The browser retry also failed (%s)." % res.error)
        return
    if res.is_pdf:
        job.files = [f for f in job.files if not (f["role_key"] == "official" and f.get("stale"))]
        job.store("official", "official", res)
        job.official_warnings = []
        return
    warnings, _ = inspect_html(res, rec)
    job.store("official-rendered", "official-rendered", res, "; ".join(warnings) or None)
    if pres:
        job.store("official-print", "official-print", pres)
    job.files = [f for f in job.files if not (f["role_key"] == "official" and f.get("stale"))]
    job.official_warnings = warnings
    if not warnings:
        job.notes.append("Saved with a headless browser because the plain download %s." % (
            "failed" if not job.official_ok else "looked incomplete"))


# ----------------------------------------------------------------------------- modes

def verify(db):
    problems = 0
    for rec in db["records"]:
        lc = rec.get("local_copy") or {}
        bad = []
        for f in lc.get("files") or []:
            p = ROOT / f.get("path", "")
            if not p.is_file():
                f["integrity"] = "missing"
                bad.append("%s (missing)" % f["path"])
            elif sha256(p.read_bytes()) != f.get("sha256"):
                f["integrity"] = "modified"
                bad.append("%s (modified)" % f["path"])
            else:
                f["integrity"] = "ok"
        if bad:
            problems += len(bad)
            msg = "Integrity check %s: local file missing or changed since archiving: %s." % (
                iso(utcnow())[:10], ", ".join(bad))
            lc["integrity_flag"] = msg
            if lc.get("status") == "archived":
                lc["status"] = "archived-review"
            print("  %-10s %s" % (rec["id"], msg))
        elif lc.get("files"):
            lc["integrity_flag"] = None
    return problems


def select(db, args):
    recs = db["records"]
    if args.only:
        ids = {x.strip() for x in args.only.split(",") if x.strip()}
        recs = [r for r in recs if r["id"] in ids or r.get("slug") in ids]
    if args.status:
        st = {x.strip() for x in args.status.split(",") if x.strip()}
        recs = [r for r in recs if (r.get("local_copy") or {}).get("status", "not-attempted") in st]
    return recs


def write_manifest(db, started, args, counts, ua):
    ARCHIVE.mkdir(exist_ok=True)
    manifest = {
        "generated_at": iso(utcnow()), "tool": "tools/archive.py", "tool_version": TOOL_VERSION,
        "user_agent": ua, "records": {r["id"]: r.get("local_copy") for r in db["records"]},
    }
    tmp = ARCHIVE / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ARCHIVE / "manifest.json")
    with open(ARCHIVE / "runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "started": iso(started), "finished": iso(utcnow()), "counts": counts,
            "options": vars(args),
        }, ensure_ascii=False) + "\n")


ATTENTION_GROUPS = [
    ("failed", "Nothing could be downloaded"),
    ("partial", "Only the secondary source was saved"),
    ("archived-review", "Saved, but the copy needs a human look"),
    ("no-url", "No URL to archive"),
    ("not-attempted", "Not attempted yet"),
    ("integrity", "A local file is missing or has changed since it was archived"),
]


def write_attention_log(db):
    """Rewrite archive/needs-attention.txt: every record that is not cleanly archived, with the reason.

    The file is for the person running the register. Nothing in it is sent anywhere, and the
    archiver takes no further action; saving a copy by hand, asking the site operator or leaving
    the record flagged is their decision.
    """
    ARCHIVE.mkdir(exist_ok=True)
    today = utcnow().strftime("%Y-%m-%d")
    groups = defaultdict(list)
    listed = set()
    for rec in db["records"]:
        lc = rec.get("local_copy") or {}
        status = lc.get("status") or "not-attempted"
        if status != "archived":
            groups[status].append(rec)
            listed.add(rec["id"])
        if lc.get("integrity_flag"):
            groups["integrity"].append(rec)
            listed.add(rec["id"])

    def wrap(label, text):
        return textwrap.wrap("%-14s%s" % (label, text or "-"), width=96, subsequent_indent=" " * 14,
                             break_long_words=False, break_on_hyphens=False) or ["%-14s-" % label]

    lines = [
        "Records that need a human decision - AI Safety Policy Register",
        "Written %s by tools/archive.py. Register: %d records, %d listed here." % (
            iso(utcnow()), len(db["records"]), len(listed)),
        "",
        "This file is rewritten after every archiver run and after --verify. Nothing in it is sent",
        "anywhere. For each record, decide yourself what to do:",
        "  - open the official URL in a normal browser, save the document into the folder named",
        "    below, add it to local_copy.files in data/records.json, then run tools/build.py and",
        "    tools/archive.py --verify;",
        "  - or ask the site operator for a copy;",
        "  - or leave the record flagged (the flag stays visible in the app and the data files).",
        "",
    ]
    for status, heading in ATTENTION_GROUPS:
        recs = groups.get(status) or []
        if not recs:
            continue
        lines += ["=" * 100, "%s (%s): %d" % (heading, status, len(recs)), "=" * 100, ""]
        for rec in recs:
            lc = rec.get("local_copy") or {}
            lines.append("%s  %s" % (rec["id"], rec.get("short_title") or rec.get("title") or ""))
            lines += ["    " + l for l in wrap("jurisdiction:", rec.get("jurisdiction"))]
            if rec.get("official_url"):
                lines.append("    %-14s%s" % ("official:", rec["official_url"]))
            if rec.get("secondary_url"):
                lines.append("    %-14s%s" % ("secondary:", rec["secondary_url"]))
            problem = lc.get("integrity_flag") if status == "integrity" else lc.get("flag")
            lines += ["    " + l for l in wrap("problem:", problem)]
            if lc.get("last_attempt"):
                lines.append("    %-14s%s" % ("last attempt:", lc["last_attempt"]))
            stored = [f["path"] for f in lc.get("files") or [] if f.get("path") and not f.get("stale")]
            if stored:
                lines += ["    " + l for l in wrap("stored:", ", ".join(stored))]
            if status == "no-url":
                lines.append("    %-14s%s" % ("to do:", "add an official_url to data/records.json, then re-run the archiver"))
            else:
                lines.append("    %-14s%s" % ("save by hand:", "archive/%s/%s/" % (rec["id"], today)))
            lines.append("")
    if not listed:
        lines.append("Every record is cleanly archived. Nothing to decide.")
    ATTENTION_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(listed)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Download local copies of the register's sources and flag failures.")
    ap.add_argument("--only", help="comma-separated record IDs or slugs, e.g. EU-01,US-07")
    ap.add_argument("--status", help="only records whose local status is one of these, e.g. failed,partial,not-attempted")
    ap.add_argument("--pdfs", type=int, default=2, help="max linked PDFs to save per official page (default 2, 0 = none)")
    ap.add_argument("--no-secondary", action="store_true", help="do not download secondary URLs")
    ap.add_argument("--browser", action="store_true", help="retry failed/suspicious pages in headless Chromium (Playwright)")
    ap.add_argument("--ignore-robots", dest="respect_robots", action="store_false",
                    help="do not check robots.txt (only if you have the right to fetch these pages)")
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads across different sites (default 4)")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests to the same site (default 2)")
    ap.add_argument("--timeout", type=int, default=45, help="seconds per request (default 45)")
    ap.add_argument("--retries", type=int, default=2, help="retries for timeouts and 5xx/429 errors (default 2)")
    ap.add_argument("--max-mb", type=int, default=150, help="largest file to keep, in MB (default 150)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be fetched and exit")
    ap.add_argument("--verify", action="store_true", help="re-hash local files, flag missing/modified ones, and exit")
    args = ap.parse_args(argv)

    db = build.normalise(build.load())

    if args.verify:
        print("Verifying local files against their recorded SHA-256 hashes ...")
        n = verify(db)
        build.save(db)
        todo = write_attention_log(db)
        print("Integrity problems: %d" % n)
        print("Records that need a decision: %d, listed in %s" % (todo, ATTENTION_FILE.relative_to(ROOT)))
        return 1 if n else 0

    recs = select(db, args)
    if args.dry_run:
        for r in recs:
            print("%-10s %-15s official=%s secondary=%s" % (
                r["id"], r["local_copy"]["status"], r.get("official_url"), r.get("secondary_url")))
        print("%d records selected." % len(recs))
        return 0

    ua = "%s/%s (research archive of public AI policy documents)" % (AGENT_TOKEN, TOOL_VERSION)
    fetcher = Fetcher(ua, args.timeout, args.retries, args.delay, args.max_mb << 20, args.respect_robots)
    started = utcnow()
    run_date = started.strftime("%Y-%m-%d")
    print("Archiving %d records into %s (%s workers, %.1fs per-site delay, robots.txt %s)" % (
        len(recs), ARCHIVE.relative_to(ROOT), args.workers, args.delay,
        "respected" if args.respect_robots else "IGNORED"))

    jobs, done = [], 0
    counts = defaultdict(int)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futs = {pool.submit(run_http, RecordJob(r, run_date, utcnow()), fetcher, args): r for r in recs}
            for fut in concurrent.futures.as_completed(futs):
                rec = futs[fut]
                done += 1
                try:
                    job = fut.result()
                except Exception as e:  # never lose the run because of one record
                    job = RecordJob(rec, run_date, utcnow())
                    job.official_error = "Archiver error: %s: %s" % (type(e).__name__, e)
                    job.keep_previous("official", job.official_error)
                jobs.append(job)
                status = job.finalise()
                counts[status] += 1
                sizes = sum(f.get("bytes") or 0 for f in job.files if not f.get("stale"))
                print("[%3d/%d] %-10s %-16s %7.1f KB  %s" % (
                    done, len(recs), rec["id"], status, sizes / 1024,
                    (rec["local_copy"].get("flag") or "")[:110]))
                if done % 10 == 0:
                    build.save(db)
    except KeyboardInterrupt:
        print("\nInterrupted; saving what has been archived so far.")

    if args.browser:
        retry = [j for j in jobs if j.need_browser and j.rec.get("official_url")]
        if retry:
            try:
                bf = BrowserFetcher(args.timeout)
            except Exception as e:
                print("Browser mode unavailable (%s). Install with: pip install playwright && playwright install chromium" % e)
                bf = None
            if bf:
                print("Retrying %d records in a headless browser ..." % len(retry))
                try:
                    for j in retry:
                        before = j.rec["local_copy"]["status"]
                        counts[before] -= 1
                        try:
                            run_browser(j, bf, fetcher, args)
                        except Exception as e:
                            j.notes.append("The browser retry failed (%s)." % e)
                        after = j.finalise()
                        counts[after] += 1
                        print("  %-10s %s -> %s" % (j.rec["id"], before, after))
                finally:
                    bf.close()

    build.save(db)
    counts = {k: v for k, v in counts.items() if v}
    write_manifest(db, started, args, counts, ua)
    todo = write_attention_log(db)
    total = defaultdict(int)
    for r in db["records"]:
        total[r["local_copy"]["status"]] += 1
    print("\nThis run: " + ", ".join("%s %d" % (k, counts[k]) for k in build.LOCAL_STATUSES if k in counts))
    print("Whole register: " + ", ".join("%s %d" % (k, total[k]) for k in build.LOCAL_STATUSES if k in total))
    print("Flags are stored in data/records.json (local_copy.flag) and shown in the app.")
    print("Records that need a decision: %d, listed in %s. Nothing is sent anywhere; what to do is up to you."
          % (todo, ATTENTION_FILE.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
