# http_client.py

import os, json, logging
from pathlib import Path
from datetime import date
from typing import Iterator, Dict, Any, List, Optional
from urllib.parse import urljoin
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# ─── Load .env ──────────────────────────────────────────
_base = Path(__file__).parent
load_dotenv(_base / ".env")

API_TOKEN = os.getenv("API_TOKEN")
BASE_URL  = os.getenv("BASE_URL")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "100"))
TIMEOUT   = int(os.getenv("HTTP_TIMEOUT", "10"))

if not API_TOKEN or not BASE_URL:
    raise RuntimeError("❌ Missing API_TOKEN or BASE_URL in .env")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type":  "application/vnd.api+json"
}

logger = logging.getLogger(__name__)
CACHE_DIR = _base / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ─── Data models ──────────────────────────────────────
@dataclass
class ProjectMeta:
    id: str
    name: str
    start_date: date
    end_date: Optional[date]
    region: Optional[str]
    bm: Optional[str] = None
    om: Optional[str] = None
    sup: Optional[str] = None
    status: Optional[str] = None
    contacts: List[str] = field(default_factory=list)

@dataclass
class Issue:
    id: str
    title: str
    severity: str
    region: str
    description_html: str
    implication: Optional[str]
    cost_impact: float
    mgmt_comment1: Optional[str]
    mgmt_comment2: Optional[str]
    table_html: Optional[str]
    recommendation: Optional[str] = None

# ─── Helpers ──────────────────────────────────────────
def normalize(value, default="") -> str:
    if isinstance(value, list):
        value = value[0] if value else default
    return value.strip() if isinstance(value, str) else default

def _get_with_retries(url: str, params: dict = None) -> Dict[str, Any]:
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://',  HTTPAdapter(max_retries=retries))
    resp = session.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def paginate(endpoint: str, params: dict) -> Iterator[Dict[str, Any]]:
    url = f"{BASE_URL}{endpoint}"
    while True:
        data = _get_with_retries(url, params=params)
        yield from data.get("data", [])
        next_link = data.get("links", {}).get("next")
        if not next_link:
            break
        url = urljoin(BASE_URL, next_link)
        params = None

# ─── Fetch projects ───────────────────────────────────
def get_all_projects() -> List[ProjectMeta]:
    today = date.today().isoformat()
    params = {"filter[start_date][lte]": today, "page[size]": PAGE_SIZE}
    result: List[ProjectMeta] = []

    for item in paginate("/projects", params):
        attr = item.get("attributes", {})
        ca   = attr.get("custom_attributes", [])
        try:
            start = date.fromisoformat(attr.get("start_date"))
        except:
            continue
        end = None
        if attr.get("end_date"):
            try:
                end = date.fromisoformat(attr["end_date"])
            except:
                pass

        def extract(term: str) -> str:
            return normalize(next((c["value"] for c in ca if c.get("term")==term), ""))

        pm = ProjectMeta(
            id         = item.get("id",""),
            name       = attr.get("name",""),
            start_date = start,
            end_date   = end,
            region     = extract("Region"),
            bm         = extract("Branch Manager"),
            om         = extract("Operations Manager"),
            sup        = extract("Supervisor"),
            status     = attr.get("status","Active"),
            contacts   = []
        )
        pm.contacts = [pm.bm, pm.om, pm.sup]
        result.append(pm)

    return result

# ─── Fetch issues ─────────────────────────────────────
def get_project_issues(
    project_id: str,
    severity: Optional[List[str]] = None,
    use_cache: bool = True
) -> List[Issue]:
    cache_file = CACHE_DIR / f"{project_id}_issues.json"
    items = []

    # 1) Fetch or fallback to cache
    try:
        data = _get_with_retries(f"{BASE_URL}/projects/{project_id}/issues")
        items = data.get("data", [])
        if use_cache:
            cache_file.write_text(json.dumps(items))
    except Exception as e:
        logger.warning(f"⚠️ API failed, using cache: {e}")
        if cache_file.exists():
            items = json.loads(cache_file.read_text())
        else:
            return []

    filtered: List[Issue] = []
    for itm in items:
        ia = itm.get("attributes", {})
        if not isinstance(ia, dict):
            continue

        cm = {c["term"]: c["value"] for c in ia.get("custom_attributes", [])}

        # Region & severity
        region = normalize(cm.get("Region",""))
        sev    = normalize(ia.get("severity","")).lower()
        if severity and sev not in [s.lower() for s in severity]:
            continue

        # Raw HTML fields
        desc_html = ia.get("description","") or ""
        rec_html  = ia.get("recommendation","") or ""
        mg1       = cm.get("Management Comments 1","") or ""
        mg2       = cm.get("Management Comments 2","") or ""
        tbl_html  = cm.get("Table Details","") or ""

        issue = Issue(
            id               = itm.get("id",""),
            title            = ia.get("title","") or "",
            severity         = sev,
            region           = region,
            description_html = desc_html,
            implication      = ia.get("effect","") or "",
            cost_impact      = float(ia.get("cost_impact") or 0),
            mgmt_comment1    = mg1,
            mgmt_comment2    = mg2,
            table_html       = tbl_html,
            recommendation   = rec_html
        )
        filtered.append(issue)

    return filtered
