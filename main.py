# -*- coding: utf-8 -*-
"""
muslimbangla.com Prayer Times API
সরাসরি muslimbangla.com থেকে ডেটা স্ক্র্যাপ করে
"""

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from scraper import fetch_prayer_times

app = FastAPI(
    title="🕌 muslimbangla.com API",
    description="""
## muslimbangla.com নামাজের সময়সূচী API

সরাসরি **muslimbangla.com** থেকে ডেটা এনে JSON ফরম্যাটে দেয়।

### দুটো পদ্ধতিতে কাজ করে:
1. **Next.js JSON API** — `_next/data` endpoint থেকে সরাসরি clean JSON
2. **HTML Scraping** — fallback হিসেবে HTML parse করে

### Endpoints
| Route | বিবরণ |
|-------|--------|
| `GET /prayer-times/BD/Dhaka` | ঢাকার সময় |
| `GET /prayer-times/BD/Chittagong` | চট্টগ্রাম |
| `GET /prayer-times/BD/Sylhet` | সিলেট |
| `GET /prayer-times/{country}/{city}` | যেকোনো শহর |
| `GET /docs` | Swagger UI |

### শহরের নামের উদাহরণ
`Dhaka`, `Chittagong`, `Sylhet`, `Rajshahi`, `Khulna`,
`Barishal`, `Rangpur`, `Mymensingh`, `CoxsBazar`, `Comilla`
    """,
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["ℹ️ Info"])
async def root():
    return {
        "নাম": "muslimbangla.com Prayer API",
        "সংস্করণ": "2.0.0",
        "উৎস": "muslimbangla.com",
        "ব্যবহার": {
            "ঢাকা":        "/prayer-times/BD/Dhaka",
            "চট্টগ্রাম":   "/prayer-times/BD/Chittagong",
            "সিলেট":       "/prayer-times/BD/Sylhet",
            "রাজশাহী":     "/prayer-times/BD/Rajshahi",
            "খুলনা":       "/prayer-times/BD/Khulna",
            "বরিশাল":      "/prayer-times/BD/Barishal",
            "রংপুর":       "/prayer-times/BD/Rangpur",
            "ময়মনসিংহ":   "/prayer-times/BD/Mymensingh",
            "কক্সবাজার":   "/prayer-times/BD/CoxsBazar",
            "Swagger_UI":  "/docs",
        }
    }


@app.get(
    "/prayer-times/{country}/{city}",
    tags=["🕌 নামাজের সময়"],
    summary="যেকোনো শহরের নামাজের সময়সূচী",
)
async def get_prayer_times(
    country: str = Path(..., example="BD", description="দেশের কোড (BD, SA, AE...)"),
    city:    str = Path(..., example="Dhaka", description="শহরের নাম ইংরেজিতে"),
):
    """
    muslimbangla.com থেকে সরাসরি নামাজের সময়সূচী আনে।

    **Response-এ থাকবে:**
    - `ওয়াক্তের_সময়`: ফজর, যুহর, আসর, মাগরিব, ইশার শুরু ও শেষ সময়
    - `নিষিদ্ধ_সময়`: সূর্যোদয়, দুপুর, সূর্যাস্তের সময়
    - `নফল_নামাজ`: তাহাজ্জুদ, ইশরাক, চাশতের সময়
    - `বর্তমান_নামাজ`: এই মুহূর্তে কোন ওয়াক্ত চলছে
    - `সাহরী_শেষ`: সাহরীর শেষ সময়
    - `তারিখ`: হিজরি ও বাংলা তারিখ
    """
    result = await fetch_prayer_times(country.upper(), city)
    result["আপডেট"] = datetime.now().isoformat()
    return result


@app.get("/health", tags=["ℹ️ Info"])
async def health():
    return {"status": "✅ চালু", "time": datetime.now().isoformat()}
