import pandas as pd
from lxml import etree

def read_xliff(file) -> pd.DataFrame:
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        ns = {"x": "urn:oasis:names:tc:xliff:document:1.2"}

        rows = []
        # XLIFF 1.2
        for unit in root.findall(".//x:trans-unit", ns):
            src = unit.find("x:source", ns)
            tgt = unit.find("x:target", ns)
            rows.append({
                "source": (src.text or "") if src is not None else "",
                "target": (tgt.text or "") if tgt is not None else "",
            })

        if not rows:
            # XLIFF 2.x — no namespace
            for unit in root.findall(".//{urn:oasis:names:tc:xliff:document:2.0}unit"):
                src = unit.find(".//{urn:oasis:names:tc:xliff:document:2.0}source")
                tgt = unit.find(".//{urn:oasis:names:tc:xliff:document:2.0}target")
                rows.append({
                    "source": (src.text or "") if src is not None else "",
                    "target": (tgt.text or "") if tgt is not None else "",
                })

        return pd.DataFrame(rows).fillna("")
    except Exception as e:
        return None
