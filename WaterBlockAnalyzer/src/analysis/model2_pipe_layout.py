# =====================================================
# MODEL 2: 관로 배치 검토 - processing.run() 순차 실행
# Model Designer API 대신 안전한 processing.run() 방식
# 실행: QGIS Python 콘솔 편집기에서 열고 실행
# =====================================================

import processing
from qgis.core import QgsProject, QgsVectorLayer, QgsSingleSymbolRenderer, QgsLineSymbol

PIPE_LAYER_NAME = '상수관로'
DIA_FIELD       = 'STD_DIP'
YMD_FIELD       = 'IST_YMD'
CURRENT_YEAR    = 2026
SAVE_TEMP       = True   # True: 메모리 레이어 / False: 파일 저장

pipe_layer = QgsProject.instance().mapLayersByName(PIPE_LAYER_NAME)
if not pipe_layer:
    print("오류: '" + PIPE_LAYER_NAME + "' 레이어를 찾을 수 없습니다.")
else:
    pipe_layer = pipe_layer[0]
    print("=" * 55)
    print("MODEL 2: 관로 배치 검토 시작")
    print("=" * 55)

    # ─── STEP 1: 위상 검사 ─────────────────────────────
    print("\n[STEP 1] 위상 검사 (Check Validity)...")
    result = processing.run("native:checkvalidity", {
        'INPUT_LAYER': pipe_layer,
        'METHOD': 2,
        'VALID_OUTPUT':   'TEMPORARY_OUTPUT',
        'INVALID_OUTPUT': 'TEMPORARY_OUTPUT',
        'ERROR_OUTPUT':   'TEMPORARY_OUTPUT',
    })
    err_layer = result['ERROR_OUTPUT']
    if isinstance(err_layer, QgsVectorLayer) and err_layer.featureCount() > 0:
        err_layer.setName('관로_위상오류')
        QgsProject.instance().addMapLayer(err_layer)
        print("  위상 오류: " + str(err_layer.featureCount()) + "건 → '관로_위상오류' 레이어 생성")
    else:
        print("  위상 오류: 없음 (정상)")

    # ─── STEP 2: AGE_YEAR 필드 계산 ────────────────────
    print("\n[STEP 2] AGE_YEAR 계산 (부설연도 → 경과년수)...")
    result = processing.run("native:fieldcalculator", {
        'INPUT':           pipe_layer,
        'FIELD_NAME':      'AGE_YEAR',
        'FIELD_TYPE':      1,   # Integer
        'FIELD_LENGTH':    4,
        'FIELD_PRECISION': 0,
        'NEW_FIELD':       True,
        'FORMULA':         "2026 - to_int(left(\"" + YMD_FIELD + "\", 4))",
        'OUTPUT':          'TEMPORARY_OUTPUT',
    })
    age_layer = result['OUTPUT']
    age_layer.setName('관로_AGE계산완료')
    print("  AGE_YEAR 계산 완료: " + str(age_layer.featureCount()) + "건")

    # ─── STEP 3~6: 노후도별 분류 레이어 생성 ───────────
    print("\n[STEP 3~6] 노후도별 분류...")
    age_classes = [
        ("30년이상_불량관",  "\"AGE_YEAR\" >= 30",                        "#ff0000"),
        ("20-29년_보통관",   "\"AGE_YEAR\" >= 20 AND \"AGE_YEAR\" < 30",  "#ff8c00"),
        ("10-19년_양호관",   "\"AGE_YEAR\" >= 10 AND \"AGE_YEAR\" < 20",  "#ffd700"),
        ("10년미만_최신관",  "\"AGE_YEAR\" < 10 OR \"AGE_YEAR\" IS NULL", "#00b050"),
    ]
    for name, expr, color in age_classes:
        r = processing.run("native:extractbyexpression", {
            'INPUT':      age_layer,
            'EXPRESSION': expr,
            'OUTPUT':     'TEMPORARY_OUTPUT',
        })
        lyr = r['OUTPUT']
        lyr.setName(name)
        sym = QgsLineSymbol.createSimple({'color': color, 'width': '1.2'})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        QgsProject.instance().addMapLayer(lyr)
        print("  " + name + ": " + str(lyr.featureCount()) + "건")

    # ─── STEP 7~10: 구경별 분류 레이어 생성 ────────────
    print("\n[STEP 7~10] 구경별 분류...")
    dia_classes = [
        ("D300이상_대형간선", "\"" + DIA_FIELD + "\" >= 300",                                       "#c00000", "3.0"),
        ("D150-299_중형간선", "\"" + DIA_FIELD + "\" >= 150 AND \"" + DIA_FIELD + "\" < 300",      "#e46c0a", "2.0"),
        ("D75-149_소형지선",  "\"" + DIA_FIELD + "\" >= 75  AND \"" + DIA_FIELD + "\" < 150",      "#ffc000", "1.2"),
        ("D75미만_말단세관",  "\"" + DIA_FIELD + "\" < 75 OR \"" + DIA_FIELD + "\" IS NULL",       "#7f7f7f", "0.6"),
    ]
    for name, expr, color, width in dia_classes:
        r = processing.run("native:extractbyexpression", {
            'INPUT':      age_layer,
            'EXPRESSION': expr,
            'OUTPUT':     'TEMPORARY_OUTPUT',
        })
        lyr = r['OUTPUT']
        lyr.setName(name)
        sym = QgsLineSymbol.createSimple({'color': color, 'width': width})
        lyr.setRenderer(QgsSingleSymbolRenderer(sym))
        QgsProject.instance().addMapLayer(lyr)
        print("  " + name + ": " + str(lyr.featureCount()) + "건")

    print("\n" + "=" * 55)
    print("MODEL 2 완료 - 레이어 패널에서 결과 확인하세요.")
    print("노후도: 30년+ / 20-29 / 10-19 / 10년미만 (4개 레이어)")
    print("구경:   D300+ / D150-299 / D75-149 / D75미만 (4개 레이어)")
    print("=" * 55)
