#!/usr/bin/env python3
"""Build the translated copies of kilnviewer.com from the English pages.

The English pages (index.html, support/index.html) are the source. Every
visible string, alt text, aria-label and meta description is collected into
i18n/strings.json. A translation is i18n/<lang>.json mapping each English string
to its translation; anything missing stays English. `build` writes
<lang>/index.html and <lang>/support/index.html, and refreshes the language
switcher and hreflang links in every page, English included.

    python3 tools/i18n.py extract     # after editing the English pages
    python3 tools/i18n.py missing     # strings each language still lacks
    python3 tools/i18n.py build       # regenerate all languages
"""
import html
import json
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "support/index.html"]
I18N = SITE / "i18n"

# Second Life's viewer languages plus Korean. Order is the switcher's order.
LANGUAGES = [
    ("en", "English"), ("da", "Dansk"), ("de", "Deutsch"), ("es", "Español"),
    ("fr", "Français"), ("it", "Italiano"), ("ja", "日本語"), ("ko", "한국어"),
    ("pl", "Polski"), ("pt", "Português"), ("ru", "Русский"), ("tr", "Türkçe"),
    ("zh", "中文（繁體）"),
]
HTML_LANG = {"pt": "pt-BR", "zh": "zh-Hant"}
CJK_FONT = {"ja": "Noto+Sans+JP", "ko": "Noto+Sans+KR", "zh": "Noto+Sans+TC"}

TEXT = re.compile(r">([^<>]+)<")
ATTR = re.compile(r'\b(alt|aria-label|title)="([^"]+)"')
META = re.compile(r'(<meta (?:name|property)="(?:description|og:title|og:description)" content=")([^"]+)(")')
SKIPPED_BLOCKS = re.compile(r"<script\b.*?</script>|<style\b.*?</style>|<p class=\"footer__credits\">.*?</p>|<!-- i18n:skip -->.*?<!-- /i18n:skip -->", re.S)
SWITCHER = re.compile(r"<!-- i18n:switcher -->.*?<!-- /i18n:switcher -->", re.S)
HREFLANG = re.compile(r"<!-- i18n:hreflang -->.*?<!-- /i18n:hreflang -->", re.S)


def wanted(text):
    return re.search(r"[A-Za-z]", text) and not text.startswith(("http", "{"))


def masked(source):
    """The page with untranslated regions blanked, so nothing is collected from them."""
    return SKIPPED_BLOCKS.sub(lambda m: " " * len(m.group(0)), source)


def collect(source):
    found = []
    view = masked(source)
    for m in TEXT.finditer(view):
        text = m.group(1).strip()
        if text and wanted(text):
            found.append(html.unescape(text))
    for m in ATTR.finditer(view):
        found.append(html.unescape(m.group(2)))
    for m in META.finditer(view):
        found.append(html.unescape(m.group(2)))
    return found


def extract():
    strings = []
    for page in PAGES:
        for s in collect((SITE / page).read_text(encoding="utf-8")):
            if s not in strings:
                strings.append(s)
    I18N.mkdir(exist_ok=True)
    (I18N / "strings.json").write_text(json.dumps(strings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(strings)} strings -> i18n/strings.json")


def switcher(lang, page):
    """Language menu for one page; links stay on the same page in every language."""
    depth = page.count("/") + (0 if lang == "en" else 1)
    up = "../" * depth
    tail = "" if page == "index.html" else page.replace("index.html", "")
    current = dict(LANGUAGES)[lang]
    items = "".join(
        f'<li><a href="{up}{"" if code == "en" else code + "/"}{tail}" hreflang="{HTML_LANG.get(code, code)}" lang="{HTML_LANG.get(code, code)}"'
        + (' aria-current="page"' if code == lang else "")
        + f">{name}</a></li>"
        for code, name in LANGUAGES
    )
    return (f'<!-- i18n:switcher --><details class="tile lang"><summary>{current}</summary>'
            f'<ul class="lang__menu">{items}</ul></details><!-- /i18n:switcher -->')


def hreflang(page):
    tail = "" if page == "index.html" else page.replace("index.html", "")
    links = "".join(
        f'\n  <link rel="alternate" hreflang="{HTML_LANG.get(code, code)}" href="https://kilnviewer.com/{"" if code == "en" else code + "/"}{tail}">'
        for code, _ in LANGUAGES
    )
    links += f'\n  <link rel="alternate" hreflang="x-default" href="https://kilnviewer.com/{tail}">'
    return f"<!-- i18n:hreflang -->{links}\n  <!-- /i18n:hreflang -->"


def localise_paths(source, depth):
    """Point relative src/href one directory further up for a page that moved down a level."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#|/|data:)", url):
            return m.group(0)
        return f'{attr}="{"../" * depth}{url}"'
    return re.sub(r'\b(src|href|poster)="([^"]*)"', fix, source)


def translate(source, table):
    view = masked(source)
    out, pos = [], 0
    edits = []
    for m in TEXT.finditer(view):
        raw = m.group(1)
        key = html.unescape(raw.strip())
        if key in table and wanted(raw.strip()):
            lead = raw[: len(raw) - len(raw.lstrip())]
            trail = raw[len(raw.rstrip()):]
            edits.append((m.start(1), m.end(1), lead + html.escape(table[key], quote=False) + trail))
    for m in ATTR.finditer(view):
        key = html.unescape(m.group(2))
        if key in table:
            edits.append((m.start(2), m.end(2), html.escape(table[key], quote=True)))
    for m in META.finditer(view):
        key = html.unescape(m.group(2))
        if key in table:
            edits.append((m.start(2), m.end(2), html.escape(table[key], quote=True)))
    for start, end, new in sorted(edits):
        out.append(source[pos:start])
        out.append(new)
        pos = end
    out.append(source[pos:])
    return "".join(out)


def build():
    for page in PAGES:
        english = (SITE / page).read_text(encoding="utf-8")
        english = SWITCHER.sub(lambda m: switcher("en", page), english)
        english = HREFLANG.sub(lambda m: hreflang(page), english)
        (SITE / page).write_text(english, encoding="utf-8")
        for code, _ in LANGUAGES[1:]:
            table_file = I18N / f"{code}.json"
            if not table_file.exists():
                continue
            table = json.loads(table_file.read_text(encoding="utf-8"))
            text = translate(english, table)
            text = localise_paths(text, 1)
            text = SWITCHER.sub(lambda m: switcher(code, page), text)
            text = text.replace('<html lang="en">', f'<html lang="{HTML_LANG.get(code, code)}">', 1)
            text = re.sub(r'(<meta property="og:url" content="https://kilnviewer\.com/)', rf"\g<1>{code}/", text, count=1)
            if code in CJK_FONT:
                text = text.replace(
                    "family=Jost:wght@400;500;700&display=swap",
                    f"family=Jost:wght@400;500;700&family={CJK_FONT[code]}:wght@400;500;700&display=swap", 1)
            out = SITE / code / page
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"{code}/{page}")


def missing():
    strings = json.loads((I18N / "strings.json").read_text(encoding="utf-8"))
    for code, _ in LANGUAGES[1:]:
        f = I18N / f"{code}.json"
        table = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        gap = [s for s in strings if s not in table]
        print(f"{code}: {len(gap)} missing" + ("" if not gap else " — " + "; ".join(gap[:3])))


if __name__ == "__main__":
    {"extract": extract, "build": build, "missing": missing}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
