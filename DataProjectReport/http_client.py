# http_client.py

import os
from pathlib import Path
from dotenv import load_dotenv

# 1️⃣ Locate your .env (project root)
base_dir = Path(__file__).parent.resolve()
env_path = base_dir / ".env"

# 2️⃣ Load environment variables
load_dotenv(dotenv_path=env_path)

import logging
from datetime import datetime, date
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Configuration ───────────────────────────────────────────
API_TOKEN      = os.getenv("API_TOKEN", "")
BASE_URL       = os.getenv("BASE_URL", "https://apis-eu.highbond.com/v1/orgs/48414")
PAGE_SIZE      = int(os.getenv("PAGE_SIZE", "100"))
HTTP_TIMEOUT   = int(os.getenv("HTTP_TIMEOUT", "10"))
RETRY_TOTAL    = int(os.getenv("RETRY_TOTAL", "5"))
RETRY_BACKOFF  = float(os.getenv("RETRY_BACKOFF", "1"))

if not API_TOKEN:
    raise RuntimeError("Missing API_TOKEN in environment")
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/vnd.api+json"
}

# ─── Logger ──────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Sync HTTP Client with Retry ────────────────────────────
def build_sync_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

sync_session = build_sync_session()


def get_all_projects() -> list[dict]:
    """
    Fetch all projects whose start_date <= today.
    - paginated (page[size], page[number])
    - retries built-in
    - drops any that slipped future-dated
    """
    today_str = date.today().isoformat()
    url = f"{BASE_URL}/projects"
    page = 1
    params = {
        "filter[start_date][lte]": today_str,
        "page[size]": PAGE_SIZE,
        "page[number]": page
    }
    all_projects = []

    while True:
        try:
            resp = sync_session.get(url, headers=HEADERS, params=params, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"❌ get_all_projects: failed page {page}: {e}")
            break

        body = resp.json()
        batch = body.get("data", [])
        all_projects.extend(batch)

        next_link = body.get("links", {}).get("next")
        if not next_link:
            break

        url = urljoin(BASE_URL, next_link)
        params = None
        page += 1

    # Final client-side filter
    filtered = []
    for p in all_projects:
        sd = p.get("attributes", {}).get("start_date", "")
        try:
            if datetime.strptime(sd, "%Y-%m-%d").date() <= date.today():
                filtered.append(p)
        except ValueError:
            continue

    logger.info(f"✅ get_all_projects: retrieved {len(filtered)} projects (up to {today_str})")
    return filtered


def get_project_issues(project_id: str) -> list[dict]:
    """
    Fetch all issues for a given project_id.
    Returns empty list on any error.
    """
    url = f"{BASE_URL}/projects/{project_id}/issues"
    try:
        resp = sync_session.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        logger.debug(f"Fetched {len(data)} issues for project {project_id}")
        return data
    except Exception as e:
        logger.error(f"❌ get_project_issues [{project_id}]: {e}")
        return []


# ─── Async HTTP Client Skeleton ─────────────────────────────
# Use this as a starting point if you later need full parallel fetch.
#
# import httpx, asyncio
#
# class AsyncHighBondClient:
#     def __init__(self):
#         token = os.getenv("API_TOKEN")
#         self.base_url = os.getenv("BASE_URL")
#         self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/vnd.api+json"}
#         self.client = httpx.AsyncClient(headers=self.headers, timeout=HTTP_TIMEOUT)
#
#     async def get_all_projects(self):
#         # similar pagination logic, but using await self.client.get(...)
#         pass
#
#     async def get_project_issues(self, project_id):
#         # parallelizable with asyncio.gather
#         pass
#
#     async def close(self):
#         await self.client.aclose()
