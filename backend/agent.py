import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai as genai_sdk
from dotenv import load_dotenv

load_dotenv()

# ─── Logging Setup ────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
LOG_FILE = f"logs/travel_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

_fmt = logging.Formatter(
    "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
_fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
_sh = logging.StreamHandler()
_fh.setFormatter(_fmt)
_sh.setFormatter(_fmt)

logger = logging.getLogger("TravelAgent")
logger.setLevel(logging.INFO)
logger.addHandler(_fh)
logger.addHandler(_sh)

logger.info("=" * 64)
logger.info("  ✈  Voyara — AI Journey Companion — Startup")
logger.info(f"  Log file : {os.path.abspath(LOG_FILE)}")
logger.info("=" * 64)

# ─── Gemini Setup ─────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-3-flash-preview"
_gemini_client = genai_sdk.Client(api_key=os.getenv("GEMINI_API_KEY"))
logger.info(f"Gemini model     : {GEMINI_MODEL}")

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(title="Voyara — AI Journey Companion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TravelRequest(BaseModel):
    travel_month: str
    travel_year: str
    destination_type: str      # "india" or "international"
    india_region: str = ""     # Northern / Southern / Eastern / Western / Central / All Regions
    trip_types: list[str]
    specific_country: str = ""
    email: str


class TravelResponse(BaseModel):
    packages: list[dict]
    summary: str


def build_location_context(req: TravelRequest) -> str:
    if req.destination_type.lower() == "india":
        region = req.india_region.strip()
        return f"within India — {region}" if region and region.lower() != "all regions" else "within India (any region)"
    else:
        country = req.specific_country.strip()
        return f"international — {country}" if country else "international destinations (any country)"


def search_travel_packages_with_gemini(req: TravelRequest) -> dict:
    trip_type_str = ", ".join(req.trip_types)
    location_context = build_location_context(req)

    prompt = f"""
You are an expert travel planner agent. A user is looking for travel packages with the following preferences:

- Travel Period  : {req.travel_month} {req.travel_year}
- Destination    : {location_context}
- Trip Types     : {trip_type_str}

Your task:
1. Suggest 5 specific travel packages that best match the above criteria.
2. For each package include:
   - Package name and destination
   - Why it's ideal for {req.travel_month} {req.travel_year}
   - Highlights (activities, attractions)
   - Estimated budget range per person (INR)
   - 2-3 real booking/reference links (use well-known platforms like MakeMyTrip, Thrillophilia,
     Kesari Tours, Thomas Cook, Club Mahindra, or official tourism boards)

Respond in the following JSON format ONLY (no extra text):
{{
  "packages": [
    {{
      "name": "Package Name",
      "destination": "Destination, State/Country",
      "best_for": "Why best for this period",
      "highlights": ["highlight1", "highlight2", "highlight3"],
      "budget_per_person": "₹XX,XXX - ₹XX,XXX",
      "links": [
        {{"label": "Book on MakeMyTrip", "url": "https://..."}},
        {{"label": "Thrillophilia Details", "url": "https://..."}}
      ]
    }}
  ],
  "summary": "A brief 2-3 sentence overall recommendation summary"
}}
"""

    # ── STEP 1: Prompt built ───────────────────────────────────────────────────
    logger.info("─" * 64)
    logger.info("STEP 1  ▶  Gemini prompt built")
    logger.info(f"         Travel period   : {req.travel_month} {req.travel_year}")
    logger.info(f"         Location        : {location_context}")
    logger.info(f"         Trip types      : {trip_type_str}")
    logger.info(f"         Recipient email : {req.email}")
    logger.info(f"         Prompt length   : {len(prompt)} chars")

    # ── STEP 2: Call Gemini ────────────────────────────────────────────────────
    logger.info("STEP 2  ▶  Calling Gemini API")
    logger.info(f"         Model           : {GEMINI_MODEL}")
    t_start = datetime.now()

    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    elapsed = (datetime.now() - t_start).total_seconds()
    response_text = response.text

    # ── STEP 3: Response received ──────────────────────────────────────────────
    logger.info("STEP 3  ▶  Gemini API response received")
    logger.info(f"         Elapsed time    : {elapsed:.2f}s")
    logger.info(f"         Response length : {len(response_text)} chars")

    raw = response_text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)

    # ── STEP 4: Packages parsed ────────────────────────────────────────────────
    pkg_count = len(result.get("packages", []))
    logger.info(f"STEP 4  ▶  Parsed {pkg_count} packages from Gemini response")
    for i, pkg in enumerate(result.get("packages", []), 1):
        logger.info(f"         [{i}] {pkg.get('name', '?')}  —  {pkg.get('destination', '?')}")

    return result


def send_email(to_email: str, packages: list[dict], summary: str, req: TravelRequest):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        raise ValueError("SMTP credentials not configured in .env")

    trip_type_str = ", ".join(req.trip_types)
    location_display = build_location_context(req)
    subject = f"✈️ Your {req.travel_month} {req.travel_year} Travel Packages — {trip_type_str.title()}"

    # ── STEP 5: Composing email ────────────────────────────────────────────────
    logger.info("STEP 5  ▶  Composing HTML email")
    logger.info(f"         To              : {to_email}")
    logger.info(f"         Subject         : {subject}")

    packages_html = ""
    for i, pkg in enumerate(packages, 1):
        links_html = "".join(
            f'<li><a href="{lnk["url"]}" style="color:#1a73e8;">{lnk["label"]}</a></li>'
            for lnk in pkg.get("links", [])
        )
        highlights_html = "".join(f"<li>{h}</li>" for h in pkg.get("highlights", []))
        packages_html += f"""
        <div style="background:#f9f9f9;border-radius:10px;padding:20px;margin-bottom:20px;border-left:4px solid #1a73e8;">
          <h3 style="margin:0 0 6px 0;color:#1a73e8;">#{i} {pkg.get('name','')}</h3>
          <p style="margin:2px 0;"><strong>Destination:</strong> {pkg.get('destination','')}</p>
          <p style="margin:2px 0;"><strong>Best for {req.travel_month} {req.travel_year}:</strong> {pkg.get('best_for','')}</p>
          <p style="margin:2px 0;"><strong>Budget per person:</strong> {pkg.get('budget_per_person','')}</p>
          <p style="margin:6px 0 2px 0;"><strong>Highlights:</strong></p>
          <ul style="margin:0 0 10px 16px;">{highlights_html}</ul>
          <p style="margin:6px 0 2px 0;"><strong>Useful Links:</strong></p>
          <ul style="margin:0 0 0 16px;">{links_html}</ul>
        </div>"""

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px;color:#333;">
      <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);padding:30px;border-radius:12px;text-align:center;margin-bottom:24px;">
        <h1 style="color:white;margin:0;">✈️ Your Travel Plan is Ready!</h1>
        <p style="color:#c8e6fa;margin:8px 0 0 0;">Curated for you by Voyara ✨</p>
      </div>
      <div style="background:#e8f0fe;border-radius:8px;padding:16px;margin-bottom:20px;">
        <strong>Your Preferences:</strong>&nbsp;
        Period: <em>{req.travel_month} {req.travel_year}</em> &nbsp;|&nbsp;
        Destination: <em>{location_display}</em> &nbsp;|&nbsp;
        Types: <em>{trip_type_str.title()}</em>
      </div>
      <p style="font-size:15px;line-height:1.6;">{summary}</p>
      <h2 style="color:#0d47a1;">Recommended Packages</h2>
      {packages_html}
      <p style="font-size:12px;color:#888;margin-top:30px;">Sent by Voyara — Your AI Journey Companion 🌍</p>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    # ── STEP 6: Send email ─────────────────────────────────────────────────────
    logger.info("STEP 6  ▶  Connecting to SMTP server")
    logger.info(f"         Host            : {smtp_host}:{smtp_port}")
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())

    # ── STEP 7: Done ───────────────────────────────────────────────────────────
    logger.info(f"STEP 7  ▶  Email delivered successfully → {to_email}")
    logger.info("─" * 64)


@app.post("/plan-trip", response_model=TravelResponse)
async def plan_trip(req: TravelRequest):
    logger.info("═" * 64)
    logger.info("  NEW REQUEST  →  POST /plan-trip")
    logger.info(f"  Month  : {req.travel_month}   Year   : {req.travel_year}")
    logger.info(f"  Dest   : {req.destination_type}   Region : {req.india_region or 'N/A'}")
    logger.info(f"  Types  : {req.trip_types}")
    logger.info(f"  Email  : {req.email}")
    logger.info("═" * 64)

    try:
        result = search_travel_packages_with_gemini(req)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error from Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    packages = result.get("packages", [])
    summary = result.get("summary", "")

    try:
        send_email(req.email, packages, summary, req)
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

    logger.info("  REQUEST COMPLETE  ✓")
    logger.info("═" * 64)

    return TravelResponse(packages=packages, summary=summary)


@app.get("/health")
async def health():
    return {"status": "ok"}
