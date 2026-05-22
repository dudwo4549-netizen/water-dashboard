# QGIS 교육 제3장 - 유량계 설치 계획 검토
# 근거: 상수도 설계기준(KDS 57 00 00), K-water MNF 분석 기준
# 실행: QGIS Python 콘솔 편집기에서 열고 실행(Ctrl+Enter)

# =====================================================
# 레이어명 / 필드명 설정 (실제 환경에 맞게 수정)
# =====================================================
BLOCK_LAYER      = '소블록 경계_2025'  # 블록 경계 폴리곤
FLOWMETER_LAYER  = '유량계'            # 유량계 포인트 레이어 (수정 필요)
BLOCK_ID_FIELD   = 'ID'               # 블록 ID 필드
METER_CNT_FIELD  = 'MTR_CNT'          # 급수전 수 필드 (2단계에서 계산된 값)

# 유량계 속성 필드명 (실제 필드명으로 수정)
FM_ID_FIELD     = 'FM_ID'     # 유량계 ID
FM_TYPE_FIELD   = 'FM_TYPE'   # 계량 방식 (전자식/초음파/전자기 등)
FM_COMM_FIELD   = 'FM_COMM'   # 통신 방식 (TM/TC, NB-IoT 등)
FM_INTV_FIELD   = 'FM_INTV'   # 측정 주기 (분 단위)
FM_ACC_FIELD    = 'FM_ACC'    # 정확도 (% 단위)

# MNF CSV 파일 경로 (시계열 데이터, 없으면 None)
MNF_CSV_PATH    = None  # 예: 'C:/data/flowmeter_timeseries.csv'
MNF_TIME_COL    = 'DATETIME'   # 시간 컬럼명
MNF_FLOW_COL    = 'FLOW_LPM'  # 유량 컬럼명 (L/분)
MNF_ID_COL      = 'FM_ID'     # 유량계 ID 컬럼명


# =====================================================
# [3-1] 블록별 유량계 설치 현황 집계
#        기준: 소블록 유입부 1개소 원칙
# =====================================================
print("=" * 60)
print("[3-1] 블록별 유량계 설치 현황 집계")
print("=" * 60)

from qgis.core import (
    QgsProject, QgsSpatialIndex, QgsField,
    QgsRuleBasedRenderer, QgsFillSymbol,
    QgsMarkerSymbol, QgsSingleSymbolRenderer,
    QgsVectorLayer, QgsFeature
)
from qgis.PyQt.QtCore import QVariant

block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
fm_layer    = QgsProject.instance().mapLayersByName(FLOWMETER_LAYER)

if not block_layer:
    print("오류: " + BLOCK_LAYER + " 블록 경계 레이어를 찾을 수 없습니다.")
elif not fm_layer:
    print("오류: '" + FLOWMETER_LAYER + "' 유량계 레이어를 찾을 수 없습니다.")
    print("유량계 레이어명을 FLOWMETER_LAYER 변수에서 수정하세요.")
    print("현재 프로젝트 레이어 목록:")
    for lyr in QgsProject.instance().mapLayers().values():
        print("  - " + lyr.name())
else:
    block_layer = block_layer[0]
    fm_layer    = fm_layer[0]

    # 유량계 필드 확인
    fm_fields = [f.name() for f in fm_layer.fields()]
    print("유량계 레이어 필드: " + ", ".join(fm_fields))
    print("유량계 총 수: " + str(fm_layer.featureCount()) + "개")

    # 공간 인덱스
    fm_index = QgsSpatialIndex(fm_layer.getFeatures())
    fm_cache = {f.id(): f for f in fm_layer.getFeatures()}

    # 기존 유량계 집계 필드 초기화
    for fname in ['FM_COUNT', 'FM_GRADE']:
        idx = block_layer.fields().indexFromName(fname)
        if idx != -1:
            block_layer.startEditing()
            block_layer.dataProvider().deleteAttributes([idx])
            block_layer.updateFields()
            block_layer.commitChanges()

    block_layer.startEditing()
    block_layer.dataProvider().addAttributes([
        QgsField('FM_COUNT', QVariant.Int),    # 블록 내 유량계 수
        QgsField('FM_GRADE', QVariant.String), # 설치 판정
    ])
    block_layer.updateFields()
    block_layer.commitChanges()

    fc_idx = block_layer.fields().indexFromName('FM_COUNT')
    fg_idx = block_layer.fields().indexFromName('FM_GRADE')

    block_layer.startEditing()

    no_fm_blocks  = []   # 유량계 미설치 블록
    multi_fm_blocks = [] # 다중 유량계 블록

    print("")
    print("블록ID   유량계수  판정")
    print("-" * 35)

    for block in block_layer.getFeatures():
        block_geom = block.geometry()
        block_id   = block.attribute(BLOCK_ID_FIELD) or block.id()
        fm_count   = 0

        for fid in fm_index.intersects(block_geom.boundingBox()):
            if block_geom.contains(fm_cache[fid].geometry()):
                fm_count += 1

        if fm_count == 0:
            fm_grade = "미설치(재검토)"
            no_fm_blocks.append(str(block_id))
        elif fm_count == 1:
            fm_grade = "적정(1개소)"
        else:
            fm_grade = "다중설치(" + str(fm_count) + "개소)"
            multi_fm_blocks.append(str(block_id))

        block_layer.changeAttributeValue(block.id(), fc_idx, fm_count)
        block_layer.changeAttributeValue(block.id(), fg_idx, fm_grade)
        print(str(block_id).ljust(8) + str(fm_count).rjust(5) + "  " + fm_grade)

    block_layer.commitChanges()

    # 유량계 설치 현황 심볼로지
    fm_rules = [
        ('미설치 (재검토 필요)',  '"FM_GRADE" LIKE \'%미설치%\'',  '#ff0000', 0.8),
        ('적정 (1개소)',          '"FM_GRADE" LIKE \'%적정%\'',    '#00b050', 0.5),
        ('다중설치 (합산 검토)',  '"FM_GRADE" LIKE \'%다중%\'',   '#0070ff', 0.6),
    ]
    root = QgsRuleBasedRenderer.Rule(None)
    for label, expr, color, width in fm_rules:
        sym = QgsFillSymbol.createSimple({
            'color': color + '70',
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
    print("유량계 미설치 블록: " + str(len(no_fm_blocks)) + "개 -> " + (", ".join(no_fm_blocks) if no_fm_blocks else "없음"))
    print("다중설치 블록:      " + str(len(multi_fm_blocks)) + "개 -> " + (", ".join(multi_fm_blocks) if multi_fm_blocks else "없음"))
    print("색상: 빨강=미설치 / 초록=적정 / 파랑=다중설치")
    print("[3-1] 완료")


# =====================================================
# [3-2] 유량계 속성 검토
#        계량방식 / 통신방식 / 측정주기 기준 분류
# =====================================================
print("")
print("=" * 60)
print("[3-2] 유량계 속성 검토 (계량방식 / 통신방식)")
print("=" * 60)

fm_layer = QgsProject.instance().mapLayersByName(FLOWMETER_LAYER)
if not fm_layer:
    print("오류: 유량계 레이어를 찾을 수 없습니다.")
else:
    fm_layer  = fm_layer[0]
    fm_fields = [f.name() for f in fm_layer.fields()]

    # 속성 필드 존재 여부 확인
    checked = {}
    for alias, field in [
        ('계량방식', FM_TYPE_FIELD),
        ('통신방식', FM_COMM_FIELD),
        ('측정주기', FM_INTV_FIELD),
        ('정확도',   FM_ACC_FIELD),
    ]:
        checked[alias] = field if field in fm_fields else None
        status = "확인" if checked[alias] else "없음(필드명 수정 필요: " + field + ")"
        print("[" + alias + "] " + status)

    print("")

    # 속성이 있는 경우만 집계 출력
    ok_count = 0
    warn_list = []

    for feat in fm_layer.getFeatures():
        fm_id = feat.attribute(FM_ID_FIELD) if FM_ID_FIELD in fm_fields else str(feat.id())
        issues = []

        if checked['측정주기']:
            intv = feat[FM_INTV_FIELD]
            if intv is not None and int(intv) > 15:
                issues.append("측정주기 " + str(intv) + "분 (기준: 15분)")

        if checked['정확도']:
            acc = feat[FM_ACC_FIELD]
            try:
                if float(acc) > 2.0:
                    issues.append("정확도 " + str(acc) + "% (기준: 2% 이내)")
            except Exception:
                pass

        if issues:
            warn_list.append(str(fm_id) + ": " + " / ".join(issues))
        else:
            ok_count += 1

    print("속성 기준 적합: " + str(ok_count) + "개소")
    if warn_list:
        print("속성 기준 부적합: " + str(len(warn_list)) + "개소")
        for w in warn_list:
            print("  -> " + w)
    else:
        print("속성 기준 부적합: 없음 (또는 속성 필드 미입력)")
    print("[3-2] 완료")


# =====================================================
# [3-3] MNF(야간최소유량) 분석
#        CSV 시계열 데이터 → 새벽 2-4시 최소유량 추출
#        MNF(L/연결/시간) = 최소유량(L/h) / 급수전 수
#        K-water 기준:
#          양호: < 0.5 L/연결/시간
#          보통: 0.5 ~ 1.5 L/연결/시간
#          불량: > 1.5 L/연결/시간
# =====================================================
print("")
print("=" * 60)
print("[3-3] 야간최소유량(MNF) 분석")
print("=" * 60)

if MNF_CSV_PATH is None:
    print("MNF_CSV_PATH 가 설정되지 않았습니다.")
    print("CSV 파일 경로를 상단 MNF_CSV_PATH 변수에 입력 후 재실행하세요.")
    print("")
    print("=== CSV 파일 형식 안내 ===")
    print("필수 컬럼: DATETIME(YYYY-MM-DD HH:MM), FLOW_LPM(L/분), FM_ID")
    print("예시:")
    print("  DATETIME,FLOW_LPM,FM_ID")
    print("  2025-01-15 02:00,125.3,FM-001")
    print("  2025-01-15 02:15,118.7,FM-001")
else:
    import csv
    from datetime import datetime

    block_layer = QgsProject.instance().mapLayersByName(BLOCK_LAYER)
    fm_layer    = QgsProject.instance().mapLayersByName(FLOWMETER_LAYER)

    if not block_layer or not fm_layer:
        print("오류: 블록 또는 유량계 레이어를 찾을 수 없습니다.")
    else:
        block_layer = block_layer[0]
        fm_layer    = fm_layer[0]

        # CSV 로드 및 새벽 2-4시 데이터 추출
        mnf_data = {}  # {fm_id: [유량값 리스트]}
        try:
            with open(MNF_CSV_PATH, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt  = datetime.strptime(row[MNF_TIME_COL], '%Y-%m-%d %H:%M')
                        hr  = dt.hour
                        if 2 <= hr < 4:   # 새벽 2시~4시 (MNF 시간대)
                            fid = row[MNF_ID_COL]
                            lpm = float(row[MNF_FLOW_COL])
                            mnf_data.setdefault(fid, []).append(lpm)
                    except Exception:
                        pass
            print("CSV 로드 완료 - 유량계 " + str(len(mnf_data)) + "개소 데이터 확인")
        except Exception as e:
            print("CSV 로드 실패: " + str(e))
            mnf_data = {}

        if mnf_data:
            # 블록별 MNF 필드 추가
            for fname in ['MNF_LPH', 'MNF_RATE', 'MNF_GRADE']:
                idx = block_layer.fields().indexFromName(fname)
                if idx != -1:
                    block_layer.startEditing()
                    block_layer.dataProvider().deleteAttributes([idx])
                    block_layer.updateFields()
                    block_layer.commitChanges()

            block_layer.startEditing()
            block_layer.dataProvider().addAttributes([
                QgsField('MNF_LPH',   QVariant.Double),  # L/연결/시간
                QgsField('MNF_GRADE', QVariant.String),  # 양호/보통/불량
            ])
            block_layer.updateFields()
            block_layer.commitChanges()

            ml_idx = block_layer.fields().indexFromName('MNF_LPH')
            mg_idx = block_layer.fields().indexFromName('MNF_GRADE')

            # 유량계 -> 블록 매핑
            fm_fields = [f.name() for f in fm_layer.fields()]
            fm_index  = QgsSpatialIndex(fm_layer.getFeatures())
            fm_cache  = {f.id(): f for f in fm_layer.getFeatures()}

            block_layer.startEditing()
            print("")
            print("블록ID   최소유량(L/h)  연결수   MNF(L/연/h)  판정")
            print("-" * 58)

            for block in block_layer.getFeatures():
                block_geom = block.geometry()
                block_id   = block.attribute(BLOCK_ID_FIELD) or block.id()
                mtr_cnt    = block.attribute(METER_CNT_FIELD) or 0

                # 블록 내 유량계 찾기
                block_flows = []
                for fid in fm_index.intersects(block_geom.boundingBox()):
                    fm = fm_cache[fid]
                    if block_geom.contains(fm.geometry()):
                        fm_id = str(fm.attribute(FM_ID_FIELD) if FM_ID_FIELD in fm_fields else fm.id())
                        if fm_id in mnf_data:
                            min_lpm = min(mnf_data[fm_id])
                            block_flows.append(min_lpm)

                if not block_flows or mtr_cnt == 0:
                    print(str(block_id).ljust(8) + " 데이터 없음")
                    continue

                # 다중 유입 시 합산
                total_min_lph = sum(block_flows) * 60  # L/분 -> L/시간
                mnf_rate      = total_min_lph / mtr_cnt  # L/연결/시간

                if mnf_rate < 0.5:
                    mnf_grade = "양호"
                elif mnf_rate <= 1.5:
                    mnf_grade = "보통"
                else:
                    mnf_grade = "불량(누수의심)"

                block_layer.changeAttributeValue(block.id(), ml_idx, round(mnf_rate, 3))
                block_layer.changeAttributeValue(block.id(), mg_idx, mnf_grade)

                print(str(block_id).ljust(8) +
                      str(round(total_min_lph, 1)).rjust(12) +
                      str(mtr_cnt).rjust(8) +
                      str(round(mnf_rate, 3)).rjust(13) + "  " +
                      mnf_grade)

            block_layer.commitChanges()

            # MNF 등급 심볼로지
            mnf_rules = [
                ('불량 (누수 의심, >1.5)',  '"MNF_GRADE" = \'불량(누수의심)\'', '#ff0000', 0.8),
                ('보통 (0.5~1.5)',          '"MNF_GRADE" = \'보통\'',           '#ff8c00', 0.5),
                ('양호 (<0.5)',             '"MNF_GRADE" = \'양호\'',           '#00b050', 0.3),
            ]
            root = QgsRuleBasedRenderer.Rule(None)
            for label, expr, color, width in mnf_rules:
                sym = QgsFillSymbol.createSimple({
                    'color': color + '70',
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
            print("색상: 빨강=불량(누수의심) / 주황=보통 / 초록=양호")
            print("MNF 기준 (K-water): 양호<0.5 / 보통 0.5~1.5 / 불량>1.5 L/연결/시간")

print("")
print("=" * 60)
print("3단계 유량계 설치 계획 검토 완료")
print("MNF CSV 데이터가 없으면 [3-1], [3-2]만 활용 가능합니다.")
print("=" * 60)
