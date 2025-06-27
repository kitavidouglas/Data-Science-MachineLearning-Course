#!/usr/bin/env python3
import sys, re, argparse
from datetime import datetime, date
import pandas as pd
from collections import defaultdict

from http_client import get_all_projects, get_project_issues
from report_builder import create_word_report
from your_utils import ensure_str  # your helper

# ─── API Constants ──────────────────────────────────────────
API_TOKEN = "acd6c44de072af279f19042267e98f0a70ca00c5966e118636dd87a451786347"
BASE_URL  = "https://apis-eu.highbond.com/v1/orgs/48414"
HEADERS   = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/vnd.api+json"
}

logger = __import__('logging').getLogger(__name__)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region")
    p.add_argument("--month")
    p.add_argument("--severity")
    args = p.parse_args()

    region_f = (args.region or "").strip().lower()
    month_f  = (args.month  or "").strip()
    sev_in   = (args.severity or "").strip()
    sev_filters = {s.strip().lower() for s in sev_in.split(",") if s}

    if month_f:
        try: datetime.strptime(month_f, "%Y-%m")
        except: 
            logger.error("Invalid month. Use YYYY-MM."); sys.exit(1)

    # Fetch projects & build table_data
    td = []
    for pr in get_all_projects():
        start = pr["attributes"].get("start_date","")
        # client-side filter
        if month_f and not start.startswith(month_f): continue
        pid, attr = pr["id"], pr["attributes"]
        region = ensure_str(next((c["value"] for c in attr.get("custom_attributes",[]) if c["term"]=="Region"),""))
        if region_f and region_f not in region.lower(): continue

        for isd in get_project_issues(pid):
            ia = isd["attributes"]
            if not ia:
              logger.warning(f"Skipping issue without attributes in project {pid}")
            continue

            sev = str(ia.get("severity", "")).lower()
            if sev_filters and sev not in sev_filters: continue
            # extract fields...
            td.append([
                pid,
                attr.get("name",""),
                # ... rest of the fields ...
            ])

    if not td:
        logger.warning("No data matched filters"); return

    # audit CSV
    pd.DataFrame(td).to_csv("project_data.csv", index=False)

    safe_r = re.sub(r"\W+", "_", region_f or "ALL")
    safe_m = re.sub(r"\W+", "_", month_f or "ALL")
    fname = f"project_report_{safe_r}_{safe_m}.docx"

    doc = create_word_report(td, region_f)
    doc.save(fname)
    logger.info(f"Report written to {fname}")

if __name__ == "__main__":
    main()
