# -*- coding: utf-8 -*-
"""
muslimbangla.com scraper
দুটো পদ্ধতি:
1. Next.js _next/data JSON API (সবচেয়ে দ্রুত, clean data)
2. HTML parse fallback (১ কাজ না করলে)
"""

import httpx
import re
import json
from html.parser import HTMLParser


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "bn-BD,bn;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://muslimbangla.com/",
}

TIME_RE       = re.compile(r'[০-৯]{1,2}:[০-৯]{2}')
PRAYER_NAMES  = ['ফজর', 'যুহর', 'আসর', 'মাগরিব', 'ইশা']
FORBID_NAMES  = ['সূর্যোদয়', 'দুপুর', 'সূর্যাস্ত']
NAFL_NAMES    = ['তাহাজ্জুদ', 'ইশরাক', 'চাশত']


# ── HTML Text Extractor ────────────────────────────────────────────────────

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts, self.tag, self.skip = [], '', False
        self._skip_tags = {'script','style','noscript','svg','img','meta','link'}

    def handle_starttag(self, tag, attrs):
        self.tag = tag
        if tag in self._skip_tags: self.skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags: self.skip = False

    def handle_data(self, data):
        if not self.skip:
            t = data.strip()
            if t and len(t) > 1:
                self.texts.append(t)


def _extract(texts, names):
    out = {}
    for i, t in enumerate(texts):
        for name in names:
            if t == name and name not in out:
                times, j = [], i + 1
                while j < len(texts) and len(times) < 2:
                    times += TIME_RE.findall(texts[j]); j += 1
                if times:
                    out[name] = {
                        "শুরু": times[0],
                        "শেষ": times[1] if len(times) > 1 else ""
                    }
    return out


def _parse_html(html: str, country: str, city: str) -> dict:
    """HTML থেকে সব ডেটা বের করা"""
    p = TextExtractor()
    p.feed(html)
    texts = p.texts

    date_info, current = {}, None
    for i, t in enumerate(texts):
        if 'হিজরি' in t and 'হিজরি' not in date_info:
            date_info['হিজরি'] = t
        if 'বঙ্গাব্দ' in t and 'বাংলা' not in date_info:
            date_info['বাংলা'] = t
        if 'বর্তমান নামাজ' in t or ('বর্তমান' in t and i+1 < len(texts)):
            for name in PRAYER_NAMES:
                if name in t: current = name

    prayers  = _extract(texts, PRAYER_NAMES)
    forbidden = _extract(texts, FORBID_NAMES)
    nafl     = _extract(texts, NAFL_NAMES)

    sahri = ""
    for i, t in enumerate(texts):
        if 'সাহরী' in t:
            times = TIME_RE.findall(t) or (TIME_RE.findall(texts[i+1]) if i+1 < len(texts) else [])
            if times: sahri = times[0]
            break

    return {
        "শহর": city,
        "দেশ": country,
        "তারিখ": date_info,
        "বর্তমান_নামাজ": current,
        "ওয়াক্তের_সময়": prayers,
        "নিষিদ্ধ_সময়": forbidden,
        "নফল_নামাজ": nafl,
        "সাহরী_শেষ": sahri,
    }


async def _get_build_id(client: httpx.AsyncClient) -> str | None:
    """Next.js build ID বের করা"""
    try:
        r = await client.get("https://muslimbangla.com/", headers=HEADERS)
        m = re.search(r'"buildId"\s*:\s*"([^"]+)"', r.text)
        if m: return m.group(1)
        # __NEXT_DATA__ থেকেও পাওয়া যায়
        nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
        if nd:
            data = json.loads(nd.group(1))
            return data.get('buildId')
    except:
        pass
    return None


async def fetch_prayer_times(country: str, city: str) -> dict:
    """
    muslimbangla.com থেকে নামাজের সময় আনা।
    পদ্ধতি ১: Next.js JSON API (_next/data)
    পদ্ধতি ২: HTML scraping (fallback)
    """
    page_url = f"https://muslimbangla.com/world/{country}/prayer-times-{city}"
    method_used = None

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15,
        headers=HEADERS
    ) as client:

        # ── পদ্ধতি ১: Next.js _next/data JSON API ─────────────────────────
        build_id = await _get_build_id(client)
        if build_id:
            json_url = (
                f"https://muslimbangla.com/_next/data/{build_id}"
                f"/world/{country}/prayer-times-{city}.json"
            )
            try:
                jr = await client.get(json_url, headers={
                    **HEADERS,
                    "Accept": "application/json",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                })
                if jr.status_code == 200:
                    raw = jr.json()
                    # pageProps এর ভেতরে prayer data থাকে
                    props = raw.get("pageProps", {})
                    method_used = "next_data_json"

                    # JSON structure বের করে parse করা
                    prayer_data = (
                        props.get("prayerTimes")
                        or props.get("data")
                        or props.get("salat")
                        or props
                    )

                    if prayer_data and isinstance(prayer_data, dict):
                        return {
                            "শহর": city,
                            "দেশ": country,
                            "পদ্ধতি": method_used,
                            "raw_props": prayer_data,
                        }
            except Exception:
                pass

        # ── পদ্ধতি ২: HTML scraping ────────────────────────────────────────
        r = await client.get(page_url, headers=HEADERS)

        if r.status_code == 403:
            from fastapi import HTTPException
            raise HTTPException(503, detail="muslimbangla.com এক্সেস ব্লক করেছে।")
        if r.status_code == 404:
            from fastapi import HTTPException
            raise HTTPException(404, detail=f"'{city}' শহর পাওয়া যায়নি।")
        if r.status_code != 200:
            from fastapi import HTTPException
            raise HTTPException(502, detail=f"HTTP {r.status_code}")

        # __NEXT_DATA__ থেকে JSON নেওয়া
        nd = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r.text, re.DOTALL
        )
        if nd:
            try:
                next_data = json.loads(nd.group(1))
                build_id_found = next_data.get('buildId', '')
                props = next_data.get('props', {}).get('pageProps', {})
                method_used = f"next_data_embedded (buildId: {build_id_found})"

                # prayer data বের করা
                prayer_raw = (
                    props.get("prayerTimes")
                    or props.get("salat")
                    or props.get("data")
                    or {}
                )

                result = _parse_html(r.text, country, city)
                result["পদ্ধতি"] = method_used
                result["next_props"] = props  # full props include করা
                return result
            except json.JSONDecodeError:
                pass

        # Pure HTML parse
        result = _parse_html(r.text, country, city)
        result["পদ্ধতি"] = "html_parse"
        return result
