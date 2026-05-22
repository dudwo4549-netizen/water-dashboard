# QGIS Python API로 model3 파일 생성 스크립트
# QGIS 콘솔에서 실행하면 올바른 형식의 .model3 파일이 자동 생성됩니다.

from qgis.core import (
    QgsProcessingModelAlgorithm,
    QgsProcessingModelChildAlgorithm,
    QgsProcessingModelChildParameterSource,
    QgsProcessingModelParameter,
    QgsProcessingModelOutput,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessing
)
import os

SAVE_DIR = r'C:\Users\채송이\Desktop\Antigravity(AI Work)\WaterBlockAnalyzer\models'
os.makedirs(SAVE_DIR, exist_ok=True)


# =====================================================
# MODEL 2: 관로 배치 검토
# =====================================================
def create_model2():
    model = QgsProcessingModelAlgorithm()
    model.setName("02_관로배치검토")
    model.setGroup("상수도블록검토")

    # ── 입력 파라미터 ──────────────────────────────
    p_pipe = QgsProcessingParameterVectorLayer(
        "INPUT_PIPE", "상수관로",
        [QgsProcessing.TypeVectorLine]
    )
    model.addModelParameter(p_pipe, QgsProcessingModelParameter("INPUT_PIPE"))
    param_src = QgsProcessingModelChildParameterSource.fromModelParameter

    # ── Step 1: 위상 검사 ──────────────────────────
    step1 = QgsProcessingModelChildAlgorithm("native:checkvalidity")
    step1.setChildId("chkval")
    step1.setDescription("Step1_위상검사")
    step1.setParameterSources({
        "INPUT_LAYER": [param_src("INPUT_PIPE")],
        "METHOD":      [QgsProcessingModelChildParameterSource.fromStaticValue(2)]
    })
    step1.modelOutput("ERROR_OUTPUT",
                      QgsProcessingModelOutput("위상오류레이어", "ERROR_OUTPUT"))
    model.addChildAlgorithm(step1)

    # ── Step 2: AGE_YEAR 계산 ─────────────────────
    step2 = QgsProcessingModelChildAlgorithm("native:fieldcalculator")
    step2.setChildId("calc_age")
    step2.setDescription("Step2_AGE_YEAR계산")
    step2.setParameterSources({
        "INPUT":           [param_src("INPUT_PIPE")],
        "FIELD_NAME":      [QgsProcessingModelChildParameterSource.fromStaticValue("AGE_YEAR")],
        "FIELD_TYPE":      [QgsProcessingModelChildParameterSource.fromStaticValue(1)],
        "FIELD_LENGTH":    [QgsProcessingModelChildParameterSource.fromStaticValue(4)],
        "FIELD_PRECISION": [QgsProcessingModelChildParameterSource.fromStaticValue(0)],
        "NEW_FIELD":       [QgsProcessingModelChildParameterSource.fromStaticValue(True)],
        "FORMULA":         [QgsProcessingModelChildParameterSource.fromStaticValue(
            "2026 - to_int(left(\"IST_YMD\", 4))"
        )]
    })
    model.addChildAlgorithm(step2)

    child_src = QgsProcessingModelChildParameterSource.fromChildOutput

    # ── Step 3~6: 노후도별 분류 ────────────────────
    age_classes = [
        ("ext_30", "Step3_30년이상",  "\"AGE_YEAR\" >= 30",                        "30년이상_불량관"),
        ("ext_20", "Step4_20-29년",   "\"AGE_YEAR\" >= 20 AND \"AGE_YEAR\" < 30",  "20-29년_보통관"),
        ("ext_10", "Step5_10-19년",   "\"AGE_YEAR\" >= 10 AND \"AGE_YEAR\" < 20",  "10-19년_양호관"),
        ("ext_00", "Step6_10년미만",  "\"AGE_YEAR\" < 10 OR \"AGE_YEAR\" IS NULL", "10년미만_최신관"),
    ]
    for cid, desc, expr, out_name in age_classes:
        s = QgsProcessingModelChildAlgorithm("native:extractbyexpression")
        s.setChildId(cid)
        s.setDescription(desc)
        s.setParameterSources({
            "INPUT":      [child_src("calc_age", "OUTPUT")],
            "EXPRESSION": [QgsProcessingModelChildParameterSource.fromStaticValue(expr)]
        })
        s.modelOutput("OUTPUT", QgsProcessingModelOutput(out_name, "OUTPUT"))
        model.addChildAlgorithm(s)

    # ── Step 7~10: 구경별 분류 ─────────────────────
    dia_classes = [
        ("dia_300", "Step7_D300이상",  "\"STD_DIP\" >= 300",                          "D300이상_대형간선"),
        ("dia_150", "Step8_D150-299", "\"STD_DIP\" >= 150 AND \"STD_DIP\" < 300",    "D150-299_중형간선"),
        ("dia_75",  "Step9_D75-149",  "\"STD_DIP\" >= 75  AND \"STD_DIP\" < 150",    "D75-149_소형지선"),
        ("dia_sm",  "Step10_D75미만", "\"STD_DIP\" < 75 OR \"STD_DIP\" IS NULL",     "D75미만_말단세관"),
    ]
    for cid, desc, expr, out_name in dia_classes:
        s = QgsProcessingModelChildAlgorithm("native:extractbyexpression")
        s.setChildId(cid)
        s.setDescription(desc)
        s.setParameterSources({
            "INPUT":      [child_src("calc_age", "OUTPUT")],
            "EXPRESSION": [QgsProcessingModelChildParameterSource.fromStaticValue(expr)]
        })
        s.modelOutput("OUTPUT", QgsProcessingModelOutput(out_name, "OUTPUT"))
        model.addChildAlgorithm(s)

    path = os.path.join(SAVE_DIR, "02_관로배치검토.model3")
    model.toFile(path)
    print("Model 2 저장 완료: " + path)
    return model


# =====================================================
# MODEL 3: 블록 분할 계획 검토
# =====================================================
def create_model3():
    model = QgsProcessingModelAlgorithm()
    model.setName("03_블록분할검토")
    model.setGroup("상수도블록검토")

    param_src  = QgsProcessingModelChildParameterSource.fromModelParameter
    static_src = QgsProcessingModelChildParameterSource.fromStaticValue
    child_src  = QgsProcessingModelChildParameterSource.fromChildOutput

    # ── 입력 파라미터 ──────────────────────────────
    model.addModelParameter(
        QgsProcessingParameterVectorLayer("INPUT_BLOCK", "블록 경계 (폴리곤)",
                                          [QgsProcessing.TypeVectorPolygon]),
        QgsProcessingModelParameter("INPUT_BLOCK")
    )
    model.addModelParameter(
        QgsProcessingParameterVectorLayer("INPUT_METER", "수도계량기 (포인트)",
                                          [QgsProcessing.TypeVectorPoint]),
        QgsProcessingModelParameter("INPUT_METER")
    )
    model.addModelParameter(
        QgsProcessingParameterVectorLayer("INPUT_VALVE", "제수밸브 (포인트)",
                                          [QgsProcessing.TypeVectorPoint]),
        QgsProcessingModelParameter("INPUT_VALVE")
    )
    p_weight = QgsProcessingParameterField(
        "WEIGHT_FIELD", "일평균 사용량 필드 (일평균2)",
        defaultValue="일평균2",
        parentLayerParameterName="INPUT_METER",
        optional=True
    )
    model.addModelParameter(p_weight, QgsProcessingModelParameter("WEIGHT_FIELD"))

    # ── Step 1: 급수전 수 + 사용량 합계 집계 ───────
    step1 = QgsProcessingModelChildAlgorithm("native:countpointsinpolygon")
    step1.setChildId("cnt_meter")
    step1.setDescription("Step1_급수전수+사용량집계")
    step1.setParameterSources({
        "POLYGONS": [param_src("INPUT_BLOCK")],
        "POINTS":   [param_src("INPUT_METER")],
        "WEIGHT":   [param_src("WEIGHT_FIELD")],
        "FIELD":    [static_src("MTR_CNT")]
    })
    model.addChildAlgorithm(step1)

    # ── Step 2: 급수전 수 판정(MTR_GRADE) ──────────
    step2 = QgsProcessingModelChildAlgorithm("native:fieldcalculator")
    step2.setChildId("grade_mtr")
    step2.setDescription("Step2_급수전수판정")
    step2.setParameterSources({
        "INPUT":           [child_src("cnt_meter", "OUTPUT")],
        "FIELD_NAME":      [static_src("MTR_GRADE")],
        "FIELD_TYPE":      [static_src(2)],
        "FIELD_LENGTH":    [static_src(20)],
        "FIELD_PRECISION": [static_src(0)],
        "NEW_FIELD":       [static_src(True)],
        "FORMULA":         [static_src(
            "CASE WHEN \"MTR_CNT\" < 500 THEN '소규모(기준미달)' "
            "WHEN \"MTR_CNT\" <= 1500 THEN '적정' "
            "ELSE '대규모(기준초과)' END"
        )]
    })
    model.addChildAlgorithm(step2)

    # ── Step 3: 사용량 판정(USE_GRADE) ────────────
    step3 = QgsProcessingModelChildAlgorithm("native:fieldcalculator")
    step3.setChildId("grade_use")
    step3.setDescription("Step3_사용량판정")
    step3.setParameterSources({
        "INPUT":           [child_src("grade_mtr", "OUTPUT")],
        "FIELD_NAME":      [static_src("USE_GRADE")],
        "FIELD_TYPE":      [static_src(2)],
        "FIELD_LENGTH":    [static_src(20)],
        "FIELD_PRECISION": [static_src(0)],
        "NEW_FIELD":       [static_src(True)],
        "FORMULA":         [static_src(
            "CASE WHEN \"일평균2\" < 500 THEN '사용량부족' "
            "WHEN \"일평균2\" <= 3000 THEN '적정' "
            "ELSE '사용량초과' END"
        )]
    })
    step3.modelOutput("OUTPUT", QgsProcessingModelOutput("블록_급수전_집계결과", "OUTPUT"))
    model.addChildAlgorithm(step3)

    # ── Step 4: 블록 폴리곤 → 경계선 변환 ─────────
    step4 = QgsProcessingModelChildAlgorithm("native:polygonstolines")
    step4.setChildId("poly2line")
    step4.setDescription("Step4_경계선추출")
    step4.setParameterSources({
        "INPUT": [param_src("INPUT_BLOCK")]
    })
    model.addChildAlgorithm(step4)

    # ── Step 5: 경계선 5m 버퍼 ────────────────────
    step5 = QgsProcessingModelChildAlgorithm("native:buffer")
    step5.setChildId("buf_5m")
    step5.setDescription("Step5_경계선5m버퍼")
    step5.setParameterSources({
        "INPUT":           [child_src("poly2line", "OUTPUT")],
        "DISTANCE":        [static_src(5.0)],
        "SEGMENTS":        [static_src(5)],
        "END_CAP_STYLE":   [static_src(0)],
        "JOIN_STYLE":      [static_src(0)],
        "MITER_LIMIT":     [static_src(2.0)],
        "DISSOLVE":        [static_src(False)]
    })
    model.addChildAlgorithm(step5)

    # ── Step 6: 버퍼 내 제수밸브 추출 ─────────────
    step6 = QgsProcessingModelChildAlgorithm("native:extractbylocation")
    step6.setChildId("ext_valve")
    step6.setDescription("Step6_경계밸브추출")
    step6.setParameterSources({
        "INPUT":     [param_src("INPUT_VALVE")],
        "PREDICATE": [static_src([0])],
        "INTERSECT": [child_src("buf_5m", "OUTPUT")]
    })
    model.addChildAlgorithm(step6)

    # ── Step 7: 블록별 경계 밸브 수 집계 ──────────
    step7 = QgsProcessingModelChildAlgorithm("native:countpointsinpolygon")
    step7.setChildId("cnt_valve")
    step7.setDescription("Step7_경계밸브수집계")
    step7.setParameterSources({
        "POLYGONS": [child_src("grade_use", "OUTPUT")],
        "POINTS":   [child_src("ext_valve", "OUTPUT")],
        "FIELD":    [static_src("VALVE_CNT")]
    })
    model.addChildAlgorithm(step7)

    # ── Step 8: 경계 밸브 판정(VALVE_GRADE) ────────
    step8 = QgsProcessingModelChildAlgorithm("native:fieldcalculator")
    step8.setChildId("grade_valve")
    step8.setDescription("Step8_경계밸브판정")
    step8.setParameterSources({
        "INPUT":           [child_src("cnt_valve", "OUTPUT")],
        "FIELD_NAME":      [static_src("VALVE_GRADE")],
        "FIELD_TYPE":      [static_src(2)],
        "FIELD_LENGTH":    [static_src(20)],
        "FIELD_PRECISION": [static_src(0)],
        "NEW_FIELD":       [static_src(True)],
        "FORMULA":         [static_src(
            "CASE WHEN \"VALVE_CNT\" = 0 THEN '미설치(재검토)' "
            "WHEN \"VALVE_CNT\" = 1 THEN '적정(1개소)' "
            "ELSE '다중설치(' || to_string(\"VALVE_CNT\") || '개소)' END"
        )]
    })
    step8.modelOutput("OUTPUT", QgsProcessingModelOutput("블록_최종분석결과", "OUTPUT"))
    model.addChildAlgorithm(step8)

    path = os.path.join(SAVE_DIR, "03_블록분할검토.model3")
    model.toFile(path)
    print("Model 3 저장 완료: " + path)
    return model


# ── 실행 ───────────────────────────────────────────
print("Model 생성 시작...")
try:
    create_model2()
except Exception as e:
    print("Model 2 오류: " + str(e))

try:
    create_model3()
except Exception as e:
    print("Model 3 오류: " + str(e))

print("")
print("완료! QGIS 그래픽 모델러에서 파일을 열어 확인하세요.")
print("경로: " + SAVE_DIR)
