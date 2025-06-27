# html_parser.py

from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Tuple, Dict, Any

def parse_html_content(html: str) -> List[Dict[str,Any]]:
    """
    Parses rich HTML into a sequence of:
      - {"type":"paragraph", "runs":[{"text":..., "bold":bool, "italic":bool, "href":opt str}, ...]}
      - {"type":"table", "rows":[[{"text":..., "colspan":int, "rowspan":int}, ...], ...]}
    """
    soup = BeautifulSoup(html or "", "html.parser")

    # strip scripts & styles
    for tag in soup(["script","style"]):
        tag.decompose()
    # unify <br>
    for br in soup.find_all("br"):
        br.replace_with("\n")

    content: List[Dict[str,Any]] = []

    # --- Helper to flatten a tag into styled runs ---
    def extract_runs(el) -> List[Dict]:
        runs = []
        def recurse(node, bold=False, italic=False, href=None):
            if isinstance(node, NavigableString):
                text = str(node)
                if text.strip():
                    runs.append({"text": text, "bold": bold, "italic": italic, "href": href})
            elif isinstance(node, Tag):
                b = bold or node.name in ("strong","b")
                i = italic or node.name in ("em","i")
                h = href or (node.get("href") if node.name=="a" else None)
                for child in node.contents:
                    recurse(child, bold=b, italic=i, href=h)
        recurse(el)
        return runs

    # --- Process top-level elements in order ---
    for elem in soup.body or soup.contents:
        if isinstance(elem, Tag) and elem.name=="table":
            # build a full matrix with colspan/rowspan
            rows: List[List[Dict]] = []
            # temporary tracker for rowspans
            span_map: Dict[Tuple[int,int], Dict] = {}
            for r_idx, tr in enumerate(elem.find_all("tr")):
                row_cells: List[Dict] = []
                c_idx = 0
                for cell in tr.find_all(["th","td"]):
                    # skip columns blocked by prior rowspans
                    while (r_idx, c_idx) in span_map:
                        row_cells.append(span_map.pop((r_idx, c_idx)))
                        c_idx += 1

                    text = cell.get_text(strip=True)
                    colspan = int(cell.get("colspan", 1))
                    rowspan = int(cell.get("rowspan", 1))
                    cell_info = {"text": text, "colspan": colspan, "rowspan": rowspan}

                    row_cells.append(cell_info)

                    # register future rowspan slots
                    if rowspan>1:
                        for extra_r in range(1, rowspan):
                            for extra_c in range(colspan):
                                span_map[(r_idx+extra_r, c_idx+extra_c)] = {
                                    "text": "", "colspan":1, "rowspan":1
                                }

                    c_idx += colspan

                rows.append(row_cells)

            content.append({"type":"table", "rows": rows})

        else:
            # treat as paragraph: split on double-newline to separate p-blocks
            text_blob = getattr(elem, "get_text", lambda: str(elem))().strip()
            if not text_blob:
                continue
            for paragraph in text_blob.split("\n\n"):
                # build runs by re-parsing on original sub-tree
                # find the corresponding Tag or fallback to plain
                p_tag = None
                if isinstance(elem, Tag) and elem.name in ("p","div","span"):
                    p_tag = elem
                runs = extract_runs(p_tag or BeautifulSoup(paragraph, "html.parser"))
                content.append({"type":"paragraph", "runs": runs})

    return content
