# QGIS 교육 제1장 - 관로 배치 검토 실행 스크립트 (실행 전용, 주석만 포함)
# 좌표계: EPSG:5186 (중부원점 TM) 필수
# 실행: QGIS Python 콘솔 편집기에서 열고 실행(Ctrl+Enter)

# =====================================================
# [1] 관로 연결성 - 단절 노드(Dangling Node) 탐지
# =====================================================
from qgis.core import QgsProject
from collections import Counter

PIPE_LAYER = 'WTL_PIPE_LM'  # 레이어명 확인 후 수정
SNAP_TOL = 0.1  # 단위: m

pipe_layer = QgsProject.instance().mapLayersByName(PIPE_LAYER)
if not pipe_layer:
    print("오류: " + PIPE_LAYER + " 레이어를 찾을 수 없습니다. 레이어명을 확인하세요.")
else:
    pipe_layer = pipe_layer[0]

    def nkey(pt):
        return (round(pt.x(), 1), round(pt.y(), 1))

    node_count = Counter()
    for feat in pipe_layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue

        # MultiLineString 타입 처리 (첫 번째 파트만 사용)
        from qgis.core import QgsWkbTypes, QgsGeometry
        if QgsWkbTypes.isMultiType(geom.wkbType()):
            parts = geom.asMultiPolyline()
            if not parts:
                continue
            geom = QgsGeometry.fromPolylineXY(parts[0])

        pts = geom.asPolyline()
        if len(pts) < 2:
            continue
        node_count[nkey(pts[0])] += 1
        node_count[nkey(pts[-1])] += 1

    dangling = [k for k, v in node_count.items() if v == 1]
    print("단절 노드(관말) 후보: " + str(len(dangling)) + "개")
    for pt in dangling[:20]:
        print("  좌표: " + str(pt[0]) + ", " + str(pt[1]))
    print("완료 - 총 관로 피처: " + str(pipe_layer.featureCount()) + "개")


# =====================================================
# [2] 관경별 색상 시각화
# =====================================================
from qgis.core import QgsProject, QgsRuleBasedRenderer, QgsLineSymbol

PIPE_LAYER = 'WTL_PIPE_LM'
DIA_FIELD  = 'STD_DIP'  # 실제 관경 필드명

pipe_layer = QgsProject.instance().mapLayersByName(PIPE_LAYER)
if not pipe_layer:
    print("오류: 레이어를 찾을 수 없습니다.")
else:
    pipe_layer = pipe_layer[0]

    dia_rules = [
        ('300mm 이상 (대형관)', '"' + DIA_FIELD + '" >= 300',                              '#e60026', 2.0),
        ('150-299mm (중형관)', '"' + DIA_FIELD + '" >= 150 AND "' + DIA_FIELD + '" < 300', '#ff8c00', 1.5),
        ('75-149mm (소형관)',  '"' + DIA_FIELD + '" >= 75  AND "' + DIA_FIELD + '" < 150', '#ffd700', 1.0),
        ('75mm 미만 (세관)',   '"' + DIA_FIELD + '" < 75',                                 '#aaaaaa', 0.5),
    ]

    root_rule = QgsRuleBasedRenderer.Rule(None)
    for label, expression, color, width in dia_rules:
        sym = QgsLineSymbol.createSimple({'color': color, 'width': str(width), 'capstyle': 'round'})
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expression)
        root_rule.appendChild(rule)

    pipe_layer.setRenderer(QgsRuleBasedRenderer(root_rule))
    pipe_layer.triggerRepaint()
    print("관경별 심볼로지 적용 완료")


# =====================================================
# [3] 블록별 관로 연장 집계
# =====================================================
from qgis.core import QgsProject, QgsSpatialIndex

PIPE_LAYER  = 'WTL_PIPE_LM'
BLOCK_LAYER = '블록_경계'  # 블록 경계 레이어명 수정 필요
BLOCK_ID_FIELD = 'BLOCK_ID'  # 블록 ID 필드명 수정 필요

pipe_layer  = QgsProject.instance().mapLayersByName(PIPE_LAYER)
block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)

if not pipe_layer or not block_layer:
    print("오류: 레이어를 찾을 수 없습니다. 레이어명을 확인하세요.")
else:
    pipe_layer  = pipe_layer[0]
    block_layer = block_layer[0]

    pipe_index = QgsSpatialIndex(pipe_layer.getFeatures())
    pipe_cache = {f.id(): f for f in pipe_layer.getFeatures()}

    print("블록ID           관로연장(m)  관로연장(km)  판정")
    print("-" * 55)

    for block in block_layer.getFeatures():
        block_geom = block.geometry()
        block_id   = block.attribute(BLOCK_ID_FIELD) or block.id()
        total_len  = 0.0

        for pid in pipe_index.intersects(block_geom.boundingBox()):
            pipe_geom = pipe_cache[pid].geometry()
            if block_geom.intersects(pipe_geom):
                clipped = block_geom.intersection(pipe_geom)
                total_len += clipped.length()

        km = total_len / 1000.0
        if km < 1.0:
            grade = "소규모 재검토"
        elif km <= 10.0:
            grade = "적정"
        else:
            grade = "대규모 재검토"

        print(str(block_id).ljust(16) + str(round(total_len, 1)).rjust(12) +
              str(round(km, 3)).rjust(13) + "  " + grade)


# =====================================================
# [4] 레이어 분리 시각화
#     - 원본 레이어 (WTL_PIPE_LM)      : 구경(DIA) 기준 색상 분류
#     - 복사 레이어 (WTL_PIPE_LM_노후도): 부설연도 기준 색상 분류
# =====================================================
from qgis.core import (
    QgsProject, QgsField, QgsFeature, QgsVectorLayer,
    QgsRuleBasedRenderer, QgsLineSymbol
)
from qgis.PyQt.QtCore import QVariant

PIPE_LAYER   = 'WTL_PIPE_LM'
YMD_FIELD    = 'IST_YMD'   # YYYYMMDD 형식 부설일자 필드
CURRENT_YEAR = 2026

pipe_layer = QgsProject.instance().mapLayersByName(PIPE_LAYER)
if not pipe_layer:
    print("오류: " + PIPE_LAYER + " 레이어를 찾을 수 없습니다.")
else:
    pipe_layer = pipe_layer[0]
    field_names = [f.name() for f in pipe_layer.fields()]

    # 구경 필드 자동 탐지 (STD_DIP 우선)
    DIA_FIELD = 'STD_DIP'
    for c in ['STD_DIP', 'PIPE_DIA', 'DIA', 'DIAMETER', 'D', 'PIPEDIA', 'DIAM']:
        if c in field_names:
            DIA_FIELD = c
            break
    print("구경 필드: " + DIA_FIELD + " / 부설일자 필드: " + YMD_FIELD)

    # ==========================================================
    # [4-A] 원본 레이어: 구경(DIA) 기준 분류
    # ==========================================================
    dia_rules = [
        ('D300mm 이상 (대형 간선)', '"' + DIA_FIELD + '" >= 300',
         '#c00000', 3.0),
        ('D150-299mm (중형 간선)', '"' + DIA_FIELD + '" >= 150 AND "' + DIA_FIELD + '" < 300',
         '#e46c0a', 2.0),
        ('D75-149mm (소형 지선)',  '"' + DIA_FIELD + '" >= 75  AND "' + DIA_FIELD + '" < 150',
         '#ffc000', 1.2),
        ('D75mm 미만 (말단 세관)', '"' + DIA_FIELD + '" < 75  OR  "' + DIA_FIELD + '" IS NULL',
         '#7f7f7f', 0.6),
    ]

    root_dia = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in dia_rules:
        sym = QgsLineSymbol.createSimple({'color': color, 'width': str(width), 'capstyle': 'round'})
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root_dia.appendChild(rule)

    pipe_layer.setRenderer(QgsRuleBasedRenderer(root_dia))
    pipe_layer.triggerRepaint()
    print("원본 레이어 - 구경별 분류 적용 완료")

    # ==========================================================
    # [4-B] 복사 레이어 생성 후 노후도(연도) 기준 분류
    # ==========================================================
    COPY_LAYER_NAME = 'WTL_PIPE_LM_노후도'

    # 기존 동일 이름 레이어 제거
    for old in QgsProject.instance().mapLayersByName(COPY_LAYER_NAME):
        QgsProject.instance().removeMapLayer(old.id())

    # 메모리 레이어 생성 (원본 CRS + 원본 필드 + AGE_YEAR 추가)
    crs_str   = pipe_layer.crs().authid()
    field_defs = '&'.join(
        'field=' + f.name() + ':' + (
            'integer' if f.typeName() in ('Integer', 'Integer64') else
            'double'  if f.typeName() == 'Real' else
            'string'
        )
        for f in pipe_layer.fields()
    )
    copy_layer = QgsVectorLayer(
        'LineString?crs=' + crs_str + '&' + field_defs + '&field=AGE_YEAR:integer',
        COPY_LAYER_NAME,
        'memory'
    )

    # 원본 피처 복사 + AGE_YEAR 계산
    copy_layer.startEditing()
    ok_count   = 0
    skip_count = 0

    from qgis.core import QgsWkbTypes, QgsGeometry
    for src_feat in pipe_layer.getFeatures():
        new_feat = QgsFeature(copy_layer.fields())

        # 지오메트리 복사 (MultiLineString 처리 포함)
        geom = src_feat.geometry()
        if geom and QgsWkbTypes.isMultiType(geom.wkbType()):
            parts = geom.asMultiPolyline()
            if parts:
                geom = QgsGeometry.fromPolylineXY(parts[0])
        new_feat.setGeometry(geom)

        # 속성 복사
        for f in pipe_layer.fields():
            new_feat[f.name()] = src_feat[f.name()]

        # AGE_YEAR 계산 (IST_YMD YYYYMMDD -> 연도 추출)
        try:
            raw  = src_feat[YMD_FIELD]
            year = int(str(raw)[:4])
            if 1900 <= year <= CURRENT_YEAR:
                new_feat['AGE_YEAR'] = CURRENT_YEAR - year
                ok_count += 1
            else:
                skip_count += 1
        except Exception:
            skip_count += 1

        copy_layer.addFeature(new_feat)

    copy_layer.commitChanges()
    print("복사 레이어 생성 완료: " + str(ok_count) + "건 / 건너뜀: " + str(skip_count) + "건")

    # 노후도 심볼로지 적용 (복사 레이어)
    age_rules = [
        ('30년 이상 (불량 - 즉시 검토)', '"AGE_YEAR" >= 30',                       '#ff0000', 2.0),
        ('20-29년 (보통 - 중기 계획)',   '"AGE_YEAR" >= 20 AND "AGE_YEAR" < 30',  '#ff8c00', 1.5),
        ('10-19년 (양호 - 모니터링)',    '"AGE_YEAR" >= 10 AND "AGE_YEAR" < 20',  '#ffd700', 1.0),
        ('10년 미만 (최신 - 유지관리)',  '"AGE_YEAR" < 10 OR "AGE_YEAR" IS NULL', '#00b050', 0.8),
    ]

    root_age = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in age_rules:
        sym = QgsLineSymbol.createSimple({'color': color, 'width': str(width), 'capstyle': 'round'})
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root_age.appendChild(rule)

    copy_layer.setRenderer(QgsRuleBasedRenderer(root_age))
    QgsProject.instance().addMapLayer(copy_layer)
    print("복사 레이어 - 노후도 분류 적용 완료")
    print("")
    print("=== 레이어 패널 구성 ===")
    print("[원본] " + PIPE_LAYER + " -> 색상: 구경 기준")
    print("       빨강=D300+ / 주황=D150-299 / 노랑=D75-149 / 회색=D75미만")
    print("[복사] " + COPY_LAYER_NAME + " -> 색상: 노후도 기준")
    print("       빨강=30년+ / 주황=20-29년 / 노랑=10-19년 / 초록=10년미만")
    print("")
    print("레이어 패널에서 두 레이어를 켜고 끄며 비교 검토하세요.")

