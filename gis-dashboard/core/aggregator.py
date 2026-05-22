"""상수도 표준 스키마 기반 자동 집계"""
import pandas as pd
import geopandas as gpd
from datetime import datetime


def safe_year(val):
    """IST_YMD에서 연도만 추출 (예: '20150315' → 2015)"""
    try:
        s = str(val)
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
    except Exception:
        pass
    return None


def summarize(gdf: gpd.GeoDataFrame) -> dict:
    """관로 GeoDataFrame에서 핵심 통계 산출"""
    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore"))

    # 사용 중 관로만 (NON_USE가 'Y'/'1'이면 미사용)
    if "NON_USE" in df.columns:
        df = df[~df["NON_USE"].astype(str).isin(["Y", "y", "1", "True"])]

    length_col = "BYC_LEN" if "BYC_LEN" in df.columns else None
    if length_col is None:
        return {"error": "BYC_LEN(연장) 컬럼이 없습니다."}

    df[length_col] = pd.to_numeric(df[length_col], errors="coerce").fillna(0)

    result = {
        "총_관로수": len(df),
        "총_연장_m": round(df[length_col].sum(), 1),
        "총_연장_km": round(df[length_col].sum() / 1000, 2),
    }

    # 관종별
    if "FTR_CDE_NM" in df.columns:
        by_type = df.groupby("FTR_CDE_NM")[length_col].sum().round(1).sort_values(ascending=False)
        result["관종별_연장"] = by_type.to_dict()

    # 구경별
    if "SAA_CDE" in df.columns:
        df["_dia"] = pd.to_numeric(df["SAA_CDE"], errors="coerce")
        by_dia = df.dropna(subset=["_dia"]).groupby("_dia")[length_col].sum().round(1).sort_index()
        result["구경별_연장"] = {int(k): v for k, v in by_dia.to_dict().items()}

    # 재질별
    if "MOP_CDE_NM" in df.columns:
        by_mat = df.groupby("MOP_CDE_NM")[length_col].sum().round(1).sort_values(ascending=False)
        result["재질별_연장"] = by_mat.to_dict()

    # 매설년도/노후관
    if "IST_YMD" in df.columns:
        df["_year"] = df["IST_YMD"].map(safe_year)
        valid = df.dropna(subset=["_year"])
        if not valid.empty:
            now_y = datetime.now().year
            valid = valid.copy()
            valid["_age"] = now_y - valid["_year"]
            valid["_decade"] = (valid["_year"] // 10 * 10).astype(int)
            result["매설년대별_연장"] = (
                valid.groupby("_decade")[length_col].sum().round(1).sort_index().to_dict()
            )
            old = valid[valid["_age"] >= 30]
            result["노후관_30년이상_연장_m"] = round(old[length_col].sum(), 1)
            total = valid[length_col].sum()
            result["노후관_비율_%"] = (
                round(old[length_col].sum() / total * 100, 1) if total > 0 else 0
            )

    # 행정동별
    if "HJD_CDE" in df.columns:
        by_dong = df.groupby("HJD_CDE")[length_col].sum().round(1).sort_values(ascending=False)
        result["행정동별_연장"] = by_dong.head(20).to_dict()

    return result
