# qgis_valve_isolation.py
#
# QGIS Action script — 관로망 차단밸브 BFS 격리 분석
#
# 사용법:
#   레이어 속성 → 액션 → Python 액션 텍스트에 전체 내용 붙여넣기
#   QGIS가 실행 전에 [%FTR_IDN%]를 클릭한 관로의 실제 값으로 치환함
#
# 레이어 요구사항:
#   WTL_PIPE_LM  : 관로 레이어 (LineString), 필드 FTR_IDN
#   WTL_VALV_PS  : 밸브 레이어 (Point),      필드 FTR_CDE / FTR_IDN
#
# 출력 레이어:
#   🚨 차단밸브_표시  : 격리 밸브 위치 (빨간 점선 원형)
#   🚨 단수영향_관로  : 단수 영향 관로 (노란 굵은 선)

from collections import deque

from qgis.core import (
    QgsProject,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
    QgsSpatialIndex,
    QgsField,
    QgsMarkerSymbol,
    QgsLineSymbol,
    QgsSingleSymbolRenderer,
    QgsWkbTypes,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox

# ── 상수 ──────────────────────────────────────────────────────────────────────
PIPE_LAYER_NAME    = 'WTL_PIPE_LM'
VALVE_LAYER_NAME   = 'WTL_VALV_PS'
GATE_VALVE_CODE    = 'SA200'
SNAP_TOL           = 0.1   # 단위: m (EPSG:5186 기준)

RESULT_VALVE_LAYER = '🚨 차단밸브_표시'
RESULT_PIPE_LAYER  = '🚨 단수영향_관로'

# ── QGIS가 실행 시 [%FTR_IDN%]를 실제 값으로 치환 ─────────────────────────
clicked_pipe_id = str('[%FTR_IDN%]').strip()

# ── 레이어 조회 ───────────────────────────────────────────────────────────────
def _get_layer(name):
    matches = QgsProject.instance().mapLayersByName(name)
    if not matches:
        QMessageBox.critical(None, '레이어 오류', f"레이어를 찾을 수 없습니다: {name}")
        raise SystemExit(f"Layer not found: {name}")
    return matches[0]

pipe_layer  = _get_layer(PIPE_LAYER_NAME)
valve_layer = _get_layer(VALVE_LAYER_NAME)
crs_authid  = pipe_layer.crs().authid()

# ── 좌표 반올림으로 노드 키 생성 (디지타이징 오차 흡수) ──────────────────────
def _nkey(pt):
    return f"{round(pt.x(), 1)},{round(pt.y(), 1)}"

# ── 관로 그래프 구축 ──────────────────────────────────────────────────────────
# node_to_pipes : node_key → [ftr_idn, ...]  — 노드에 연결된 관로 목록
# pipe_to_nodes : ftr_idn  → (start_key, end_key)
# pipe_geom_cache: ftr_idn → QgsGeometry    — 밸브 근접 판단용

node_to_pipes   = {}
pipe_to_nodes   = {}
pipe_geom_cache = {}

for feat in pipe_layer.getFeatures():
    fid = str(feat['FTR_IDN']).strip()
    geom = feat.geometry()
    if geom is None or geom.isEmpty():
        continue
    # MultiLineString → 첫 번째 파트만 사용
    if QgsWkbTypes.isMultiType(geom.wkbType()):
        parts = geom.asMultiPolyline()
        if not parts:
            continue
        geom = QgsGeometry.fromPolylineXY(parts[0])
    pts = geom.asPolyline()
    if len(pts) < 2:
        continue

    s_key = _nkey(pts[0])
    e_key = _nkey(pts[-1])
    pipe_to_nodes[fid]   = (s_key, e_key)
    pipe_geom_cache[fid] = geom
    node_to_pipes.setdefault(s_key, []).append(fid)
    node_to_pipes.setdefault(e_key, []).append(fid)

if clicked_pipe_id not in pipe_to_nodes:
    QMessageBox.critical(
        None, '오류',
        f"관로 ID '{clicked_pipe_id}'를 그래프에서 찾을 수 없습니다.\n"
        f"WTL_PIPE_LM 레이어의 FTR_IDN 값과 일치하는지 확인하세요."
    )
    raise SystemExit("Pipe not in graph")

# ── 게이트밸브(SA200) 공간 인덱스 구축 ───────────────────────────────────────
valv_index    = QgsSpatialIndex()
valv_features = {}  # int feature_id → QgsFeature

for feat in valve_layer.getFeatures():
    if str(feat['FTR_CDE']).strip() != GATE_VALVE_CODE:
        continue
    valv_index.addFeature(feat)
    valv_features[feat.id()] = feat

# ── 밸브 근접 판단 헬퍼 ───────────────────────────────────────────────────────
def _valve_at_node(node_key):
    """노드 좌표 SNAP_TOL 이내에 있는 게이트밸브 반환 (없으면 None)."""
    x, y = map(float, node_key.split(','))
    pt_geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    bbox = pt_geom.boundingBox()
    bbox.grow(SNAP_TOL)
    for fid_int in valv_index.intersects(bbox):
        vf = valv_features[fid_int]
        if vf.geometry().distance(pt_geom) <= SNAP_TOL:
            return vf
    return None

def _valve_on_pipe(pipe_ftr_idn):
    """관로 선형 SNAP_TOL 이내에 있는 게이트밸브 반환 (없으면 None)."""
    pipe_geom = pipe_geom_cache[pipe_ftr_idn]
    bbox = pipe_geom.boundingBox()
    bbox.grow(SNAP_TOL)
    for fid_int in valv_index.intersects(bbox):
        vf = valv_features[fid_int]
        if vf.geometry().distance(pipe_geom) <= SNAP_TOL:
            return vf
    return None

# ── BFS 탐색 ──────────────────────────────────────────────────────────────────
queue          = deque()
visited_nodes  = set()
visited_pipes  = {clicked_pipe_id}
isolation_valves = []   # list of QgsFeature
affected_pipes   = [clicked_pipe_id]

# 클릭한 관로 양 끝점에서 BFS 시작
start_key, end_key = pipe_to_nodes[clicked_pipe_id]
queue.append(start_key)
queue.append(end_key)

while queue:
    current_node = queue.popleft()

    if current_node in visited_nodes:
        continue
    visited_nodes.add(current_node)

    # Case A: 이 노드(교차점)에 게이트밸브가 있으면 → 격리 지점, 탐색 중단
    valve = _valve_at_node(current_node)
    if valve:
        isolation_valves.append(valve)
        continue

    # 현재 노드에 연결된 미방문 관로로 확장
    for neighbor_pipe in node_to_pipes.get(current_node, []):
        if neighbor_pipe in visited_pipes:
            continue
        visited_pipes.add(neighbor_pipe)

        # Case B: 관로 선형 위에 게이트밸브가 있으면 → 격리 지점, far_node 미큐잉
        valve = _valve_on_pipe(neighbor_pipe)
        if valve:
            isolation_valves.append(valve)
            affected_pipes.append(neighbor_pipe)
            continue

        # 밸브 없음 → 단수 영향 관로, far_node 큐에 추가
        affected_pipes.append(neighbor_pipe)
        s, e = pipe_to_nodes[neighbor_pipe]
        far_node = e if s == current_node else s
        queue.append(far_node)

# ── 출력 레이어 관리 (find-or-create-and-clear) ───────────────────────────────
def _get_or_create_layer(name, geom_type_str, fields_def):
    """동일 이름 레이어가 있으면 피처만 삭제 후 재사용, 없으면 신규 생성."""
    for lyr in QgsProject.instance().mapLayersByName(name):
        if lyr.isValid():
            lyr.startEditing()
            lyr.deleteFeatures(lyr.allFeatureIds())
            lyr.commitChanges()
            return lyr
    uri = f"{geom_type_str}?crs={crs_authid}"
    lyr = QgsVectorLayer(uri, name, "memory")
    lyr.dataProvider().addAttributes(fields_def)
    lyr.updateFields()
    QgsProject.instance().addMapLayer(lyr)
    return lyr

def _style_valve_layer(lyr):
    sym = QgsMarkerSymbol.createSimple({
        'name':           'circle',
        'size':           '16',
        'color':          '0,0,0,0',    # 투명 채우기
        'outline_color':  '#FF0000',
        'outline_width':  '1.5',
        'outline_style':  'dash',
    })
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    lyr.triggerRepaint()

def _style_pipe_layer(lyr):
    sym = QgsLineSymbol.createSimple({
        'color':     '#FFD700',
        'width':     '4',
        'capstyle':  'round',
        'joinstyle': 'round',
    })
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    lyr.triggerRepaint()

# ── 차단밸브 결과 레이어 채우기 ───────────────────────────────────────────────
valve_out_lyr = _get_or_create_layer(
    RESULT_VALVE_LAYER,
    'Point',
    [QgsField('FTR_IDN', QVariant.String), QgsField('FTR_CDE', QVariant.String)],
)
valve_feats_out = []
for vf in isolation_valves:
    f = QgsFeature()
    f.setGeometry(vf.geometry())
    f.setAttributes([str(vf['FTR_IDN']), str(vf['FTR_CDE'])])
    valve_feats_out.append(f)
valve_out_lyr.dataProvider().addFeatures(valve_feats_out)
valve_out_lyr.updateExtents()
_style_valve_layer(valve_out_lyr)

# ── 단수영향 관로 결과 레이어 채우기 ─────────────────────────────────────────
pipe_out_lyr = _get_or_create_layer(
    RESULT_PIPE_LAYER,
    'LineString',
    [QgsField('FTR_IDN', QVariant.String)],
)
# 원본 관로 피처를 FTR_IDN으로 빠르게 조회
pipe_feat_lookup = {
    str(f['FTR_IDN']).strip(): f
    for f in pipe_layer.getFeatures()
}
pipe_feats_out = []
for pid in affected_pipes:
    src = pipe_feat_lookup.get(pid)
    if src is None:
        continue
    f = QgsFeature()
    f.setGeometry(src.geometry())
    f.setAttributes([pid])
    pipe_feats_out.append(f)
pipe_out_lyr.dataProvider().addFeatures(pipe_feats_out)
pipe_out_lyr.updateExtents()
_style_pipe_layer(pipe_out_lyr)

# ── 캔버스 갱신 및 결과 팝업 ──────────────────────────────────────────────────
iface.mapCanvas().refresh()

valve_ids = ', '.join(str(vf['FTR_IDN']) for vf in isolation_valves)
QMessageBox.information(
    None,
    '차단밸브 분석 결과',
    f"관로 {clicked_pipe_id} 차단 분석 완료\n\n"
    f"차단밸브 {len(isolation_valves)}개: {valve_ids}\n"
    f"단수영향 관로 {len(affected_pipes)}개",
)
