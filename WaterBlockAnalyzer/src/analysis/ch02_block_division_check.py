# QGIS 교육 제2장 - 블록 분할 계획 검토 실행 스크립트
# 근거: 상수도 설계기준(KDS 57 00 00), 유수율제고사업 가이드북(환경부)
# 실행: QGIS Python 콘솔 편집기에서 열고 실행(Ctrl+Enter)

# =====================================================
# 레이어명 / 필드명 설정 (실제 환경에 맞게 수정)
# =====================================================
PIPE_LAYER    = '상수관로'          # 관로 레이어
METER_LAYER   = '수도계량기'        # 계량기(급수전) 레이어
VALVE_LAYER   = '제수밸브'          # 밸브 레이어
BLOCK_LAYER   = '소블록 경계_2025'   # 블록 경계 폴리곤 레이어
DEM_LAYER     = '양평읍DEM'         # DEM 래스터 레이어

BLOCK_ID_FIELD   = 'ID'       # 블록 ID 필드
BLOCK_TYPE_FIELD = 's_block'  # 블록 유형 필드
VALVE_CODE_FIELD = 'FEATURE'  # 밸브 종류 코드 필드
GATE_VALVE_CODE  = 'SA200'    # 제수밸브(경계밸브) 코드
METER_SUM_FIELD  = '일평균2'    # 수용가 일평균 사용량 필드 (m3/일)


# =====================================================
# [1순위] 소블록 급수전 수 + 일사용량 집계
#         기준: 급수전 500~1,500전 / 일사용량 500~3,000 m3/일
# =====================================================
print("=" * 60)
print("[1순위] 소블록 급수전 수 + 일사용량 집계 시작")
print("=" * 60)

from qgis.core import (
    QgsProject, QgsSpatialIndex, QgsField,
    QgsRuleBasedRenderer, QgsFillSymbol
)
from qgis.PyQt.QtCore import QVariant

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
meter_layer = QgsProject.instance().mapLayersByName(METER_LAYER)

if not block_layer:
    print("오류: " + BLOCK_LAYER + " 블록 경계 레이어를 찾을 수 없습니다.")
elif not meter_layer:
    print("오류: " + METER_LAYER + " 계량기 레이어를 찾을 수 없습니다.")
else:
    block_layer = block_layer[0]
    meter_layer = meter_layer[0]

    # 일평균 사용량 필드 확인
    meter_fields = [f.name() for f in meter_layer.fields()]
    if METER_SUM_FIELD not in meter_fields:
        print("경고: '" + METER_SUM_FIELD + "' 필드를 찾을 수 없습니다.")
        print("계량기 레이어 필드 목록: " + ", ".join(meter_fields))
        METER_SUM_FIELD = None
    else:
        print("일사용량 필드: " + METER_SUM_FIELD + " 확인")

    # -------------------------------------------------------
    # 기존 관련 필드 전체 삭제 (중복 축약 필드 포함)
    # Shapefile 10자 제한으로 생긴 _1, _2 등 모두 제거
    # -------------------------------------------------------
    CLEAN_TARGETS = [
        'MTR_CNT', 'MTR_GRADE', 'DAILY_USE', 'USE_GRADE',
        # 구버전 잔여 필드
        'METER_COUNT', 'METER_COUN', 'METER_GRADE', 'METER_GRAD',
        'METER_CO_1', 'METER_GR_1', 'METER_CO_2', 'METER_GR_2',
        'METER_CO_3', 'METER_GR_3', 'DAILY_US_1', 'USE_GRAD_1',
    ]
    block_layer.startEditing()
    for fname in CLEAN_TARGETS:
        idx = block_layer.fields().indexFromName(fname)
        if idx != -1:
            block_layer.dataProvider().deleteAttributes([
                block_layer.fields().indexFromName(fname)
            ])
            block_layer.updateFields()
            print("  삭제: " + fname)
    block_layer.commitChanges()

    # 새 필드 추가 (10자 이내로 명명)
    #   MTR_CNT  : 급수전 수
    #   MTR_GRADE: 급수전 수 판정 (9자)
    #   DAILY_USE: 일평균 사용량 합계
    #   USE_GRADE: 사용량 판정
    block_layer.startEditing()
    block_layer.dataProvider().addAttributes([
        QgsField('MTR_CNT',   QVariant.Int),
        QgsField('MTR_GRADE', QVariant.String),
        QgsField('DAILY_USE', QVariant.Double),
        QgsField('USE_GRADE', QVariant.String),
    ])
    block_layer.updateFields()
    block_layer.commitChanges()

    mc_idx = block_layer.fields().indexFromName('MTR_CNT')
    mg_idx = block_layer.fields().indexFromName('MTR_GRADE')
    du_idx = block_layer.fields().indexFromName('DAILY_USE')
    ug_idx = block_layer.fields().indexFromName('USE_GRADE')

    # 공간 인덱스
    meter_index = QgsSpatialIndex(meter_layer.getFeatures())
    meter_cache = {f.id(): f for f in meter_layer.getFeatures()}

    block_layer.startEditing()
    print("")
    print("블록ID   급수전수  전수판정       일사용량(m3)  사용량판정")
    print("-" * 62)

    for block in block_layer.getFeatures():
        block_geom = block.geometry()
        block_id   = block.attribute(BLOCK_ID_FIELD) or block.id()
        count      = 0
        daily_sum  = 0.0

        for mid in meter_index.intersects(block_geom.boundingBox()):
            if block_geom.contains(meter_cache[mid].geometry()):
                count += 1
                if METER_SUM_FIELD:
                    try:
                        val = meter_cache[mid][METER_SUM_FIELD]
                        if val is not None:
                            daily_sum += float(val)
                    except Exception:
                        pass

        # 급수전 수 판정
        if count < 500:
            m_grade = "소규모"
        elif count <= 1500:
            m_grade = "적정"
        else:
            m_grade = "대규모"

        # 일사용량 판정
        if METER_SUM_FIELD:
            if daily_sum < 500:
                u_grade = "사용량부족"
            elif daily_sum <= 3000:
                u_grade = "적정"
            else:
                u_grade = "사용량초과"
        else:
            u_grade = "데이터없음"

        block_layer.changeAttributeValue(block.id(), mc_idx, count)
        block_layer.changeAttributeValue(block.id(), mg_idx, m_grade)
        block_layer.changeAttributeValue(block.id(), du_idx, round(daily_sum, 1))
        block_layer.changeAttributeValue(block.id(), ug_idx, u_grade)

        print(str(block_id).ljust(8) +
              str(count).rjust(6) + "  " +
              m_grade.ljust(12) +
              str(round(daily_sum, 1)).rjust(10) + "  " +
              u_grade)

    block_layer.commitChanges()

    # 급수전 수(MTR_CNT) 기준 심볼로지
    mtr_rules = [
        ('소규모 (500전 미만)',   '"MTR_CNT" < 500',                         '#ff0000', 0.8),
        ('적정 (500~1500전)',     '"MTR_CNT" >= 500 AND "MTR_CNT" <= 1500',  '#00b050', 0.5),
        ('대규모 (1500전 초과)', '"MTR_CNT" > 1500',                         '#ff8c00', 0.8),
    ]
    root = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in mtr_rules:
        sym = QgsFillSymbol.createSimple({
            'color': color + '80',
            'outline_color': color,
            'outline_width': str(width)
        })
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root.appendChild(rule)

    block_layer.setRenderer(QgsRuleBasedRenderer(root))
    block_layer.triggerRepaint()
    print("")
    print("=== 집계 결과 필드 안내 ===")
    print("MTR_CNT  : 급수전 수  |  MTR_GRADE: 전수 판정")
    print("DAILY_USE: 일사용량   |  USE_GRADE: 사용량 판정")
    print("색상: 빨강=소규모(500전미만) / 초록=적정 / 주황=대규모(1500전초과)")
    print("[1순위] 완료")


# =====================================================
# [2순위] 블록 경계 제수밸브(경계밸브) 위치 확인
#         기준: 블록 경계선 상에 제수밸브 존재 여부
# =====================================================
print("")
print("=" * 60)
print("[2순위] 블록 경계 밸브 위치 확인 시작")
print("=" * 60)

from qgis.core import (
    QgsProject, QgsSpatialIndex, QgsVectorLayer,
    QgsFeature, QgsRuleBasedRenderer, QgsMarkerSymbol
)
BUFFER_DIST = 5.0  # 블록 경계선 버퍼 거리 (단위: m, EPSG:5186 기준)

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
valve_layer = QgsProject.instance().mapLayersByName(VALVE_LAYER)

if not block_layer:
    print("오류: " + BLOCK_LAYER + " 레이어를 찾을 수 없습니다.")
elif not valve_layer:
    print("오류: " + VALVE_LAYER + " 레이어를 찾을 수 없습니다.")
else:
    block_layer = block_layer[0]
    valve_layer = valve_layer[0]

    # 밸브 레이어 ID 필드 자동 탐지 (FTR_IDN 없을 수 있음)
    valve_field_names = [f.name() for f in valve_layer.fields()]
    print("제수밸브 레이어 필드: " + ", ".join(valve_field_names))

    VALVE_ID_FIELD = None
    for c in ['FTR_IDN', 'GID', 'ID', 'OBJECTID', 'OID', 'FEAT_ID']:
        if c in valve_field_names:
            VALVE_ID_FIELD = c
            break
    if VALVE_ID_FIELD is None:
        VALVE_ID_FIELD = valve_field_names[0]  # 없으면 첫 번째 필드 사용
    print("밸브 ID 필드: " + VALVE_ID_FIELD)

    # 제수밸브(SA200)만 필터
    gate_valves = {
        f.id(): f for f in valve_layer.getFeatures()
        if str(f.attribute(VALVE_CODE_FIELD)).strip() == GATE_VALVE_CODE
    }
    print("제수밸브 수: " + str(len(gate_valves)) + "개")
    valve_index = QgsSpatialIndex()
    for f in gate_valves.values():
        valve_index.addFeature(f)

    # 결과 레이어 생성
    RESULT_NAME = '경계밸브_확인결과'
    for old in QgsProject.instance().mapLayersByName(RESULT_NAME):
        QgsProject.instance().removeMapLayer(old.id())

    crs_str    = block_layer.crs().authid()
    res_layer  = QgsVectorLayer(
        'Point?crs=' + crs_str + '&field=BLOCK_ID:string&field=VALVE_ID:string&field=비고:string',
        RESULT_NAME, 'memory'
    )
    res_layer.startEditing()

    no_valve_blocks = []

    for block in block_layer.getFeatures():
        block_id   = block.attribute(BLOCK_ID_FIELD) or block.id()
        # 블록 경계선 추출 (폴리곤 외곽선, QGIS 4.0 호환)
        from qgis.core import QgsWkbTypes
        geom = block.geometry()
        if geom.isMultipart():
            rings = geom.asMultiPolygon()
            boundary_pts = rings[0][0] if rings else []
        else:
            rings = geom.asPolygon()
            boundary_pts = rings[0] if rings else []
        from qgis.core import QgsGeometry
        boundary   = QgsGeometry.fromPolylineXY(boundary_pts)
        buf_geom   = boundary.buffer(BUFFER_DIST, 5)
        bbox       = buf_geom.boundingBox()

        found = []
        for vid in valve_index.intersects(bbox):
            vf = gate_valves[vid]
            if buf_geom.contains(vf.geometry()):
                found.append(vf)

        if not found:
            no_valve_blocks.append(str(block_id))
            f = QgsFeature(res_layer.fields())
            f.setGeometry(block.geometry().centroid())
            f['BLOCK_ID'] = str(block_id)
            f['VALVE_ID'] = '-'
            f['비고']      = '경계밸브 없음 - 재검토 필요'
            res_layer.addFeature(f)
        else:
            for vf in found:
                f = QgsFeature(res_layer.fields())
                f.setGeometry(vf.geometry())
                f['BLOCK_ID'] = str(block_id)
                try:
                    f['VALVE_ID'] = str(vf.attribute(VALVE_ID_FIELD) or '')
                except Exception:
                    f['VALVE_ID'] = str(vf.id())
                f['비고'] = '경계밸브 확인'
                res_layer.addFeature(f)


    res_layer.commitChanges()

    # 심볼로지: 경계밸브 없음(빨강 X) vs 있음(초록 원)
    valve_rules = [
        ('경계밸브 없음 (재검토)', '"비고" LIKE \'%없음%\'', '#ff0000', 'x', '6'),
        ('경계밸브 확인',          '"비고" LIKE \'%확인%\'', '#00b050', 'circle', '4'),
    ]
    root = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, shape, size in valve_rules:
        sym = QgsMarkerSymbol.createSimple({'name': shape, 'color': color, 'size': size})
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root.appendChild(rule)

    res_layer.setRenderer(QgsRuleBasedRenderer(root))
    QgsProject.instance().addMapLayer(res_layer)

    print("경계밸브 없는 블록: " + str(len(no_valve_blocks)) + "개")
    if no_valve_blocks:
        print("  -> " + ", ".join(no_valve_blocks))
    print("[2순위] 완료 - '경계밸브_확인결과' 레이어 생성됨")


# =====================================================
# [3순위] 블록 경계 지형지물 적합성 시각화
#         하천/도로/행정구역 경계와 블록 경계 중첩 확인
# =====================================================
print("")
print("=" * 60)
print("[3순위] 블록 경계 지형지물 적합성 시각화")
print("=" * 60)

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsSymbol,
    QgsSingleSymbolRenderer, QgsLineSymbol
)

# 지형지물 레이어명 목록 (보유 레이어명으로 수정)
TERRAIN_LAYERS = {
    '하천': 'A0010000',       # 하천중심선 레이어명 (수정 필요)
    '도로': 'A0020000',       # 도로중심선 레이어명 (수정 필요)
    '행정경계': 'L_ADM_DONG', # 읍면동 경계 레이어명 (수정 필요)
}

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
if not block_layer:
    print("오류: " + BLOCK_LAYER + " 블록 경계 레이어를 찾을 수 없습니다.")
else:
    block_layer = block_layer[0]

    # 블록 경계 외곽선 레이어 생성 (경계선만 추출)
    BOUNDARY_NAME = '블록_경계선'
    for old in QgsProject.instance().mapLayersByName(BOUNDARY_NAME):
        QgsProject.instance().removeMapLayer(old.id())

    crs_str = block_layer.crs().authid()
    bnd_layer = QgsVectorLayer(
        'LineString?crs=' + crs_str + '&field=BLOCK_ID:string',
        BOUNDARY_NAME, 'memory'
    )
    bnd_layer.startEditing()

    for block in block_layer.getFeatures():
        block_id = block.attribute(BLOCK_ID_FIELD) or block.id()
        # 폴리곤 외곽선 추출 (QGIS 4.0 호환)
        from qgis.core import QgsGeometry
        geom = block.geometry()
        if geom.isMultipart():
            rings = geom.asMultiPolygon()
            boundary_pts = rings[0][0] if rings else []
        else:
            rings = geom.asPolygon()
            boundary_pts = rings[0] if rings else []
        boundary_geom = QgsGeometry.fromPolylineXY(boundary_pts)
        f = QgsFeature(bnd_layer.fields())
        f.setGeometry(boundary_geom)
        f['BLOCK_ID'] = str(block_id)
        bnd_layer.addFeature(f)

    bnd_layer.commitChanges()

    # 블록 경계선 빨간 굵은 선으로 표시
    sym = QgsLineSymbol.createSimple({
        'color': '#ff0000', 'width': '1.5',
        'line_style': 'dash', 'capstyle': 'round'
    })
    bnd_layer.setRenderer(QgsSingleSymbolRenderer(sym))
    QgsProject.instance().addMapLayer(bnd_layer)

    # 지형지물 레이어 존재 여부 확인
    print("지형지물 레이어 확인 결과:")
    for name, layer_name in TERRAIN_LAYERS.items():
        found = QgsProject.instance().mapLayersByName(layer_name)
        status = "확인" if found else "없음 (레이어명 확인 필요: " + layer_name + ")"
        print("  [" + name + "] " + status)

    print("")
    print("블록 경계선 레이어 '" + BOUNDARY_NAME + "' 생성 완료.")
    print("레이어 패널에서 하천/도로/행정경계와 블록 경계선을 겹쳐 시각 비교하세요.")
    print("[3순위] 완료")


# =====================================================
# [4순위] DEM 기반 블록 내 고저차 검토
#         기준: 40m 이상 고저차 시 고/저압 블록 분리 권고
# =====================================================
print("")
print("=" * 60)
print("[4순위] DEM 기반 블록 내 고저차 검토")
print("=" * 60)

from qgis.core import (
    QgsProject, QgsField, QgsRasterLayer,
    QgsRuleBasedRenderer, QgsFillSymbol
)
from qgis.analysis import QgsZonalStatistics
from qgis.PyQt.QtCore import QVariant

ELEV_DIFF_THRESHOLD = 40.0  # 고저차 기준 (m)

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
dem_layer   = QgsProject.instance().mapLayersByName(DEM_LAYER)

if not block_layer:
    print("오류: " + BLOCK_LAYER + " 레이어를 찾을 수 없습니다.")
elif not dem_layer:
    print("오류: DEM 레이어 '" + DEM_LAYER + "' 를 찾을 수 없습니다.")
    print("DEM 레이어를 프로젝트에 추가한 후 DEM_LAYER 변수를 수정하여 재실행하세요.")
else:
    block_layer = block_layer[0]
    dem_layer   = dem_layer[0]

    # 기존 통계 필드 제거
    for fname in ['ELEV_MAX', 'ELEV_MIN', 'ELEV_DIFF', 'ELEV_GRADE']:
        idx = block_layer.fields().indexFromName(fname)
        if idx != -1:
            block_layer.startEditing()
            block_layer.dataProvider().deleteAttributes([idx])
            block_layer.updateFields()
            block_layer.commitChanges()

    # ZonalStatistics로 블록별 최대/최소 표고 추출
    zs = QgsZonalStatistics(
        block_layer,
        dem_layer,
        'ELEV_',
        1,
        QgsZonalStatistics.Max | QgsZonalStatistics.Min
    )
    zs.calculateStatistics(None)
    block_layer.updateFields()

    # ELEV_DIFF(고저차) 및 ELEV_GRADE(판정) 필드 추가
    block_layer.startEditing()
    block_layer.dataProvider().addAttributes([
        QgsField('ELEV_DIFF',  QVariant.Double),
        QgsField('ELEV_GRADE', QVariant.String)
    ])
    block_layer.updateFields()

    diff_idx  = block_layer.fields().indexFromName('ELEV_DIFF')
    grade_idx = block_layer.fields().indexFromName('ELEV_GRADE')

    print("블록ID           최대표고   최소표고   고저차    판정")
    print("-" * 60)

    for block in block_layer.getFeatures():
        block_id = block.attribute(BLOCK_ID_FIELD) or block.id()
        try:
            e_max = float(block['ELEV_max'] or 0)
            e_min = float(block['ELEV_min'] or 0)
            diff  = e_max - e_min
            grade = "분리 권고" if diff >= ELEV_DIFF_THRESHOLD else "적정"
            block_layer.changeAttributeValue(block.id(), diff_idx,  round(diff, 1))
            block_layer.changeAttributeValue(block.id(), grade_idx, grade)
            print(str(block_id).ljust(16) +
                  str(round(e_max, 1)).rjust(8) +
                  str(round(e_min, 1)).rjust(9) +
                  str(round(diff, 1)).rjust(9) + "  " + grade)
        except Exception:
            print(str(block_id).ljust(16) + " 표고 데이터 없음")

    block_layer.commitChanges()

    # 고저차 기준 블록 색상 분류
    elev_rules = [
        ('고저차 40m 이상 (분리 권고)', '"ELEV_DIFF" >= 40', '#ff0000', 0.8),
        ('고저차 20-39m (모니터링)',    '"ELEV_DIFF" >= 20 AND "ELEV_DIFF" < 40', '#ff8c00', 0.5),
        ('고저차 20m 미만 (적정)',      '"ELEV_DIFF" < 20', '#00b050', 0.3),
    ]

    root = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in elev_rules:
        sym = QgsFillSymbol.createSimple({
            'color': color + '60',
            'outline_color': color,
            'outline_width': str(width)
        })
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root.appendChild(rule)

    block_layer.setRenderer(QgsRuleBasedRenderer(root))
    block_layer.triggerRepaint()

    print("")
    print("색상: 빨강=40m+ 분리권고 / 주황=20-39m 모니터링 / 초록=20m미만 적정")
    print("[4순위] 완료")

print("")
print("=" * 60)
print("2단계 블록 분할 계획 검토 전체 완료")
print("레이어 패널에서 생성된 결과 레이어를 확인하세요.")
print("=" * 60)
