# =====================================================
# MODEL 3: 블록 분할 계획 검토 - processing.run() 순차 실행
# Model Designer API 대신 안전한 processing.run() 방식
# 실행: QGIS Python 콘솔 편집기에서 열고 실행
# =====================================================

import processing
from qgis.core import (
    QgsProject, QgsVectorLayer,
    QgsRuleBasedRenderer, QgsFillSymbol, QgsMarkerSymbol
)

BLOCK_LAYER  = '소블록 경계_2025'
METER_LAYER  = '수도계량기'
VALVE_LAYER  = '제수밸브'
BLOCK_ID     = 'ID'
USE_FIELD    = '일평균2'
BUFFER_DIST  = 5.0

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
meter_layer = QgsProject.instance().mapLayersByName(METER_LAYER)
valve_layer = QgsProject.instance().mapLayersByName(VALVE_LAYER)

if not block_layer:
    print("오류: '" + BLOCK_LAYER + "' 레이어를 찾을 수 없습니다.")
elif not meter_layer:
    print("오류: '" + METER_LAYER + "' 레이어를 찾을 수 없습니다.")
elif not valve_layer:
    print("오류: '" + VALVE_LAYER + "' 레이어를 찾을 수 없습니다.")
else:
    block_layer = block_layer[0]
    meter_layer = meter_layer[0]
    valve_layer = valve_layer[0]

    print("=" * 55)
    print("MODEL 3: 블록 분할 계획 검토 시작")
    print("=" * 55)

    # ─── STEP 1: 급수전 수 집계 ────────────────────────
    print("\n[STEP 1] 급수전 수 집계 (Count Points in Polygon)...")
    result = processing.run("native:countpointsinpolygon", {
        'POLYGONS': block_layer,
        'POINTS':   meter_layer,
        'WEIGHT':   USE_FIELD,
        'FIELD':    'MTR_CNT',
        'OUTPUT':   'TEMPORARY_OUTPUT',
    })
    step1 = result['OUTPUT']
    print("  집계 완료: " + str(step1.featureCount()) + "개 블록")

    # ─── STEP 2: 급수전 수 판정 필드 추가 ──────────────
    print("\n[STEP 2] 급수전 수 판정 (MTR_GRADE) 계산...")
    result = processing.run("native:fieldcalculator", {
        'INPUT':           step1,
        'FIELD_NAME':      'MTR_GRADE',
        'FIELD_TYPE':      2,   # String
        'FIELD_LENGTH':    20,
        'FIELD_PRECISION': 0,
        'NEW_FIELD':       True,
        'FORMULA':         (
            "CASE WHEN \"MTR_CNT\" < 500 THEN '소규모(기준미달)' "
            "WHEN \"MTR_CNT\" <= 1500 THEN '적정' "
            "ELSE '대규모(기준초과)' END"
        ),
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })
    step2 = result['OUTPUT']

    # ─── STEP 3: 사용량 판정 필드 추가 ─────────────────
    print("\n[STEP 3] 사용량 판정 (USE_GRADE) 계산...")
    result = processing.run("native:fieldcalculator", {
        'INPUT':           step2,
        'FIELD_NAME':      'USE_GRADE',
        'FIELD_TYPE':      2,
        'FIELD_LENGTH':    20,
        'FIELD_PRECISION': 0,
        'NEW_FIELD':       True,
        'FORMULA':         (
            "CASE WHEN \"일평균2\" < 500 THEN '사용량부족' "
            "WHEN \"일평균2\" <= 3000 THEN '적정' "
            "ELSE '사용량초과' END"
        ),
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })
    step3 = result['OUTPUT']

    # ─── STEP 4: 경계선 추출 ────────────────────────────
    print("\n[STEP 4] 블록 경계선 추출 (Polygons to Lines)...")
    result = processing.run("native:polygonstolines", {
        'INPUT':  block_layer,
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })
    boundary = result['OUTPUT']

    # ─── STEP 5: 경계선 5m 버퍼 ────────────────────────
    print("\n[STEP 5] 경계선 " + str(BUFFER_DIST) + "m 버퍼 생성...")
    result = processing.run("native:buffer", {
        'INPUT':         boundary,
        'DISTANCE':      BUFFER_DIST,
        'SEGMENTS':      5,
        'END_CAP_STYLE': 0,
        'JOIN_STYLE':    0,
        'MITER_LIMIT':   2.0,
        'DISSOLVE':      False,
        'OUTPUT':        'TEMPORARY_OUTPUT',
    })
    buf = result['OUTPUT']

    # ─── STEP 6: 경계 내 제수밸브 추출 ─────────────────
    print("\n[STEP 6] 경계 내 제수밸브 추출...")
    result = processing.run("native:extractbylocation", {
        'INPUT':     valve_layer,
        'PREDICATE': [0],   # intersects
        'INTERSECT': buf,
        'OUTPUT':    'TEMPORARY_OUTPUT',
    })
    boundary_valves = result['OUTPUT']
    print("  경계 밸브 수: " + str(boundary_valves.featureCount()) + "개")

    # ─── STEP 7: 블록별 경계 밸브 수 집계 ──────────────
    print("\n[STEP 7] 블록별 경계 밸브 수 집계...")
    result = processing.run("native:countpointsinpolygon", {
        'POLYGONS': step3,
        'POINTS':   boundary_valves,
        'FIELD':    'VALVE_CNT',
        'OUTPUT':   'TEMPORARY_OUTPUT',
    })
    step7 = result['OUTPUT']

    # ─── STEP 8: 경계 밸브 판정 필드 추가 ──────────────
    print("\n[STEP 8] 경계 밸브 판정 (VALVE_GRADE) 계산...")
    result = processing.run("native:fieldcalculator", {
        'INPUT':           step7,
        'FIELD_NAME':      'VALVE_GRADE',
        'FIELD_TYPE':      2,
        'FIELD_LENGTH':    20,
        'FIELD_PRECISION': 0,
        'NEW_FIELD':       True,
        'FORMULA':         (
            "CASE WHEN \"VALVE_CNT\" = 0 THEN '미설치(재검토)' "
            "WHEN \"VALVE_CNT\" = 1 THEN '적정(1개소)' "
            "ELSE '다중설치(' || to_string(\"VALVE_CNT\") || '개소)' END"
        ),
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })
    final = result['OUTPUT']
    final.setName('블록_분석_최종결과')

    # ─── 심볼로지 적용 ──────────────────────────────────
    rules_data = [
        ('소규모 (500전 미만)',   '"MTR_GRADE" = \'소규모(기준미달)\'',  '#ff0000', 0.8),
        ('적정 (500~1500전)',     '"MTR_GRADE" = \'적정\'',              '#00b050', 0.5),
        ('대규모 (1500전 초과)', '"MTR_GRADE" = \'대규모(기준초과)\'',  '#ff8c00', 0.8),
    ]
    root = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in rules_data:
        sym = QgsFillSymbol.createSimple({
            'color': color + '80',
            'outline_color': color,
            'outline_width': str(width)
        })
        rule = QgsRuleBasedRenderer.Rule(sym)
        rule.setLabel(label)
        rule.setFilterExpression(expr)
        root.appendChild(rule)
    final.setRenderer(QgsRuleBasedRenderer(root))

    QgsProject.instance().addMapLayer(final)

    # 결과 요약 출력
    print("\n" + "=" * 55)
    print("MODEL 3 완료")
    print("=" * 55)
    print("블록ID  급수전수  전수판정         밸브수  밸브판정")
    print("-" * 55)
    for f in final.getFeatures():
        bid   = f.attribute(BLOCK_ID) or f.id()
        mtr   = f['MTR_CNT']   or 0
        mgrp  = f['MTR_GRADE'] or '-'
        vcnt  = f['VALVE_CNT'] or 0
        vgrp  = f['VALVE_GRADE'] or '-'
        print(str(bid).ljust(7) +
              str(mtr).rjust(6) + "  " +
              str(mgrp).ljust(16) +
              str(vcnt).rjust(4) + "  " +
              str(vgrp))

    print("\n'블록_분석_최종결과' 레이어를 레이어 패널에서 확인하세요.")
    print("색상: 빨강=소규모 / 초록=적정 / 주황=대규모")
