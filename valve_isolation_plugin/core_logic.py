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
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QMessageBox

PIPE_LAYER_NAME    = 'WTL_PIPE_LM'
VALVE_LAYER_NAME   = 'WTL_VALV_PS'
GATE_VALVE_CODE    = 'SA200'
SNAP_TOL           = 0.1   # 단위: m

RESULT_VALVE_LAYER = '🚨 차단밸브_표시'
RESULT_PIPE_LAYER  = '🚨 단수영향_관로'

def _nkey(pt):
    return f"{round(pt.x(), 1)},{round(pt.y(), 1)}"

def _get_or_create_layer(name, geom_type_str, crs_authid, fields_def):
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

def run_isolation(iface, clicked_pipe_id):
    project = QgsProject.instance()
    pipe_layers = project.mapLayersByName(PIPE_LAYER_NAME)
    valve_layers = project.mapLayersByName(VALVE_LAYER_NAME)
    
    if not pipe_layers or not valve_layers:
        raise Exception("관로(WTL_PIPE_LM) 또는 밸브(WTL_VALV_PS) 레이어를 찾을 수 없습니다.")
        
    pipe_layer = pipe_layers[0]
    valve_layer = valve_layers[0]
    crs_authid = pipe_layer.crs().authid()

    node_to_pipes = {}
    pipe_to_nodes = {}
    pipe_geom_cache = {}

    # 1. 관로 그래프 구축
    for feat in pipe_layer.getFeatures():
        fid = str(feat['FTR_IDN']).strip()
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
            
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
        pipe_to_nodes[fid] = (s_key, e_key)
        pipe_geom_cache[fid] = geom
        node_to_pipes.setdefault(s_key, []).append(fid)
        node_to_pipes.setdefault(e_key, []).append(fid)

    if clicked_pipe_id not in pipe_to_nodes:
        raise Exception(f"클릭한 관로 ID '{clicked_pipe_id}'를 찾을 수 없습니다.")

    # 2. 제수밸브(SA200) 공간 인덱스 구축
    valv_index = QgsSpatialIndex()
    valv_features = {}
    
    for feat in valve_layer.getFeatures():
        if str(feat.attribute('FTR_CDE')).strip() != GATE_VALVE_CODE:
            continue
        valv_index.addFeature(feat)
        valv_features[feat.id()] = feat

    def _valve_at_node(node_key):
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
        pipe_geom = pipe_geom_cache[pipe_ftr_idn]
        bbox = pipe_geom.boundingBox()
        bbox.grow(SNAP_TOL)
        for fid_int in valv_index.intersects(bbox):
            vf = valv_features[fid_int]
            if vf.geometry().distance(pipe_geom) <= SNAP_TOL:
                return vf
        return None

    # 3. BFS 탐색 (격리 확인)
    queue = deque()
    visited_nodes = set()
    visited_pipes = {clicked_pipe_id}
    isolation_valves = []
    affected_pipes = [clicked_pipe_id]
    valve_ids_to_select = []

    start_key, end_key = pipe_to_nodes[clicked_pipe_id]
    queue.append(start_key)
    queue.append(end_key)

    while queue:
        current_node = queue.popleft()

        if current_node in visited_nodes:
            continue
        visited_nodes.add(current_node)

        # 노드에 밸브가 있으면 차단
        valve = _valve_at_node(current_node)
        if valve:
            isolation_valves.append(valve)
            valve_ids_to_select.append(valve.id())
            continue

        # 미방문 관로로 확장
        for neighbor_pipe in node_to_pipes.get(current_node, []):
            if neighbor_pipe in visited_pipes:
                continue
            visited_pipes.add(neighbor_pipe)

            # 관로 중간에 밸브가 있으면 차단
            valve = _valve_on_pipe(neighbor_pipe)
            if valve:
                isolation_valves.append(valve)
                valve_ids_to_select.append(valve.id())
                affected_pipes.append(neighbor_pipe)
                continue

            affected_pipes.append(neighbor_pipe)
            s, e = pipe_to_nodes[neighbor_pipe]
            far_node = e if s == current_node else s
            queue.append(far_node)

    # 4. 결과 표기 (레이어 생성)
    valve_out_lyr = _get_or_create_layer(RESULT_VALVE_LAYER, 'Point', crs_authid, [QgsField('FTR_IDN', QVariant.String), QgsField('FTR_CDE', QVariant.String)])
    valve_feats_out = []
    for vf in isolation_valves:
        f = QgsFeature()
        f.setGeometry(vf.geometry())
        f.setAttributes([str(vf['FTR_IDN']), str(vf['FTR_CDE'])])
        valve_feats_out.append(f)
    valve_out_lyr.dataProvider().addFeatures(valve_feats_out)
    
    # 밸브 스타일 적용
    sym = QgsMarkerSymbol.createSimple({
        'name': 'circle', 'size': '18', 'color': '0,0,0,0',
        'outline_color': '#FF0000', 'outline_width': '2.0', 'outline_style': 'solid'
    })
    valve_out_lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    valve_out_lyr.triggerRepaint()

    pipe_out_lyr = _get_or_create_layer(RESULT_PIPE_LAYER, 'LineString', crs_authid, [QgsField('FTR_IDN', QVariant.String)])
    pipe_feat_lookup = {str(f['FTR_IDN']).strip(): f for f in pipe_layer.getFeatures()}
    pipe_feats_out = []
    for pid in affected_pipes:
        src = pipe_feat_lookup.get(pid)
        if src:
            f = QgsFeature()
            f.setGeometry(src.geometry())
            f.setAttributes([pid])
            pipe_feats_out.append(f)
    pipe_out_lyr.dataProvider().addFeatures(pipe_feats_out)
    
    # 관로 스타일 적용
    sym2 = QgsLineSymbol.createSimple({
        'color': '#FFD700', 'width': '5', 'capstyle': 'round', 'joinstyle': 'round'
    })
    pipe_out_lyr.setRenderer(QgsSingleSymbolRenderer(sym2))
    pipe_out_lyr.triggerRepaint()

    # 원본 밸브 레이어에서도 피처 선택 표시
    valve_layer.selectByIds(valve_ids_to_select)

    iface.mapCanvas().refresh()

    valve_names = ', '.join(str(vf.attribute('FTR_IDN')) for vf in isolation_valves)
    QMessageBox.information(
        iface.mainWindow(),
        '고립확인 완료',
        f"단수 구역을 고립시키기 위해 다음 밸브들을 차단해야 합니다.\n\n"
        f"✅ 차단 필요 밸브 ({len(isolation_valves)}개):\n{valve_names}\n\n"
        f"⚠️ 단수 영향 관로: {len(affected_pipes)}개"
    )
