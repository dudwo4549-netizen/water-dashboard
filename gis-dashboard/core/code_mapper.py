"""표준 코드를 한글 명칭으로 변환"""
import yaml
from pathlib import Path
import pandas as pd

CODE_TABLE_PATH = Path("config/code_tables.yaml")


def load_code_tables() -> dict:
    with open(CODE_TABLE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_code_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """코드 컬럼에 _NM 컬럼 추가"""
    tables = load_code_tables()
    df = df.copy()
    for col, table in tables.items():
        if col in df.columns and table:
            df[f"{col}_NM"] = df[col].astype(str).map(table).fillna(df[col].astype(str))
    return df
