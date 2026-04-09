import pandas as pd

POSSIBLE_SOURCE = ["source", "src", "Source", "SOURCE", "ต้นฉบับ", "English", "EN"]
POSSIBLE_TARGET = ["target", "tgt", "Target", "TARGET", "คำแปล", "Thai", "TH", "translation"]

def read_excel(file) -> pd.DataFrame:
    df = pd.read_excel(file, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    src_col = next((c for c in POSSIBLE_SOURCE if c in df.columns), None)
    tgt_col = next((c for c in POSSIBLE_TARGET if c in df.columns), None)

    if src_col is None or tgt_col is None:
        # fallback: assume first col = source, second = target
        if len(df.columns) >= 2:
            df = df.rename(columns={df.columns[0]: "source", df.columns[1]: "target"})
        else:
            return None
    else:
        df = df.rename(columns={src_col: "source", tgt_col: "target"})

    return df[["source", "target"]].fillna("")
