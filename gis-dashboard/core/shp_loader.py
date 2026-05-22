"""shp 파일 ZIP을 받아 GeoDataFrame으로 변환"""
import zipfile
import tempfile
from pathlib import Path
import geopandas as gpd
import chardet

SOURCE_CRS = "EPSG:5186"   # 중부원점
TARGET_CRS = "EPSG:4326"   # 웹지도용


def detect_encoding(dbf_path: Path) -> str:
    """dbf 파일 인코딩 자동 감지 (CP949 vs UTF-8)"""
    with open(dbf_path, "rb") as f:
        raw = f.read(10000)
    result = chardet.detect(raw)
    enc = result.get("encoding", "cp949") or "cp949"
    # 한국 데이터는 CP949가 압도적
    if enc.lower() in ("euc-kr", "ks_c_5601-1987", "cp949"):
        return "cp949"
    return enc


def extract_zip(zip_file, extract_dir: Path) -> list[Path]:
    """업로드된 ZIP을 풀고 shp 파일 경로 리스트 반환"""
    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(extract_dir)
    return list(extract_dir.rglob("*.shp"))


def load_shp(shp_path: Path) -> gpd.GeoDataFrame:
    """shp 한 개를 GeoDataFrame으로 로드, 좌표계 변환 포함"""
    dbf_path = shp_path.with_suffix(".dbf")
    encoding = detect_encoding(dbf_path) if dbf_path.exists() else "cp949"

    gdf = gpd.read_file(shp_path, encoding=encoding)

    # 좌표계 설정: .prj 없으면 5186으로 가정
    if gdf.crs is None:
        gdf = gdf.set_crs(SOURCE_CRS, allow_override=True)

    # 웹지도용으로 변환
    gdf_wgs = gdf.to_crs(TARGET_CRS)
    return gdf_wgs


def load_zip_to_gdf(zip_file, project_dir: Path) -> dict[str, gpd.GeoDataFrame]:
    """ZIP 안의 모든 shp을 dict로 반환 {파일명: gdf}"""
    project_dir.mkdir(parents=True, exist_ok=True)
    shp_paths = extract_zip(zip_file, project_dir)
    result = {}
    for shp in shp_paths:
        try:
            result[shp.stem] = load_shp(shp)
        except Exception as e:
            print(f"[로드 실패] {shp.name}: {e}")
    return result
