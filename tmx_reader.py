import pandas as pd
from lxml import etree

def read_tmx(file) -> pd.DataFrame:
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        rows = []

        for tu in root.findall(".//tu"):
            tuvs = tu.findall("tuv")
            src, tgt = "", ""
            for i, tuv in enumerate(tuvs):
                seg = tuv.find("seg")
                text = (seg.text or "") if seg is not None else ""
                if i == 0:
                    src = text
                else:
                    tgt = text
            rows.append({"source": src, "target": tgt})

        return pd.DataFrame(rows).fillna("")
    except Exception:
        return None
