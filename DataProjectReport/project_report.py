#!/usr/bin/env python3

import sys
import logging
import re
from datetime import datetime, date
import pandas as pd

from http_client import get_all_projects, get_project_issues, ProjectMeta, Issue
from report_builder import ReportBuilder

# ─── Logger ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup

def strip_html(html: str) -> str:
    """
    Remove any HTML tags and entities, collapsing whitespace.
    Handles None or non-string inputs safely.
    """
    if not isinstance(html, str):
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator="")
    return " ".join(text.split())

def normalize(value):
    """Trim only. Don’t lowercase so original data stays intact."""
    if isinstance(value, list):
        value = value[0] if value else ""
    return value.strip() if isinstance(value, str) else ""

def prompt_filters():
    """Prompt user for region, month, severity filters."""
    region = input("► Enter Region filter (e.g. Mombasa; empty = all): ").strip()
    month = input("► Enter Start Month (YYYY-MM; empty = all): ").strip()
    severity = input("► Enter Severity levels (comma: high,medium,low; empty = all): ").strip()

    sev_set = {s.strip().lower() for s in severity.split(",") if s.strip()}
    if month:
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            logger.error("❌ Invalid month format. Use YYYY-MM")
            sys.exit(1)

    return region or None, month or None, sev_set or None

def main():
    region_filter, month_filter, severity_filters = prompt_filters()
    today = date.today()

    logger.info("🔍 Fetching all projects...")
    all_projects = get_all_projects()

    matching_rows = []

    for pr in all_projects:
        raw_region = pr.region or ""
        project_region = normalize(raw_region)
        region_filter_norm = normalize(region_filter) if region_filter else ""

        print(f"📌 Checking Project: {pr.name} | Region: [{project_region}] vs Filter: [{region_filter_norm}]")

        if region_filter and region_filter_norm != project_region:
            print("⏭️ Skipped: Region does not match")
            continue

        if month_filter and not pr.start_date.strftime("%Y-%m").startswith(month_filter):
            print(f"⏭️ Skipped: Start date {pr.start_date} does not match {month_filter}")
            continue

        print(f"✅ Matched Project: {pr.name}")

        issues = get_project_issues(
            project_id=pr.id,
            severity=list(severity_filters) if severity_filters else None
        )

        print(f"🔍 Found {len(issues)} issues for {pr.name}")

        if not issues:
            logger.warning(f"⚠️ No issues matched for {pr.name}")
            continue

        for issue in issues:
            print(f"📝 Issue: {issue.title} | Severity: {issue.severity}")

            sev = normalize(issue.severity)
            if severity_filters and sev not in [normalize(s) for s in severity_filters]:
                print(f"⏭️ Skipped issue {issue.title}: severity {sev} not in {severity_filters}")
                continue

            # Assign bm, om, sup from project or issue as appropriate (set to empty string if not available)
            bm = getattr(pr, "bm", "")
            om = getattr(pr, "om", "")
            sup = getattr(pr, "sup", "")

            matching_rows.append([
    pr.id,
    pr.name,
    pr.region,
    pr.start_date.isoformat(),
    issue.id,
    issue.title,
    issue.severity,
    strip_html(issue.description_html),
    strip_html(issue.implication),
    issue.cost_impact,
    strip_html(issue.mgmt_comment1),
    strip_html(issue.mgmt_comment2),
    strip_html(issue.table_html),       # if you want raw table HTML stripped
    strip_html(issue.recommendation),   # recommendation cleaned
    bm, om, sup
])

    if not matching_rows:
        logger.warning("⚠️ No data matched your filters.")
        sys.exit(0)

    # Save CSV for debug
    df = pd.DataFrame(matching_rows, columns=[
        "project_id", "project_name", "region", "start_date",
        "issue_id", "title", "severity", "description_html",
        "implication", "cost_impact", "mgmt_comment1",
        "mgmt_comment2", "table_html", "recommendation",
        "bm", "om", "sup"
    ])
    df.to_csv("project_data.csv", index=False)
    logger.info("✅ Data exported: project_data.csv")

    # Build report meta
    first = matching_rows[0]
    meta = ProjectMeta(
        id=first[0],
        name=first[1],
        start_date=datetime.strptime(first[3], "%Y-%m-%d").date(),
        end_date=None,
        region=first[2],
        bm=first[14],
        om=first[15],
        sup=first[16]
    )

    # Build Issue list
    issues = [
        Issue(
            id=row[4],
            title=row[5],
            severity=row[6],
            region=row[2],
            description_html=row[7],
            implication=row[8],
            cost_impact=float(row[9]),
            mgmt_comment1=row[10],
            mgmt_comment2=row[11],
            table_html=row[12],
            recommendation=row[13]
        )
        for row in matching_rows
    ]

    # Final DOCX
    builder = ReportBuilder(meta=meta, issues=issues, report_date=today)

    safe_region = re.sub(r"\W+", "_", region_filter or meta.region or "ALL")
    safe_month = re.sub(r"\W+", "_", month_filter or meta.start_date.strftime("%Y-%m"))
    fname = f"project_report_{safe_region}_{safe_month}.docx"

    builder.build(output_path=fname)
    logger.info(f"✅ Report saved to: {fname}")

if __name__ == "__main__":
    main()
