# WaterBlockAnalyzer 🐉

**QGIS + Python 기반 상수도 운영관리 통합 진단 시스템**

> 개발팀: 서용이 사단 (서용이, 청룡, 동룡, 옥룡)
> 기반 설계: Claude Code Work(AI) - WaterBlockAnalyzer_프로젝트_정리.md
> Antigravity 이관일: 2026-05-15

---

## 📦 폴더 구조

```
WaterBlockAnalyzer/
├── files/                        # Claude Code 원본 설계 파일
│   ├── CLAUDE_updated.md         # 프로젝트 전체 규칙 (CLAUDE.md)
│   └── WaterBlockAnalyzer_ClaudeCode_setup/
├── plugins/                      # QGIS 플러그인 모음
│   └── valve_isolation_plugin/   # ✅ 완성: 고립 밸브 자동 추출
├── src/
│   ├── core/                     # 공통 유틸리티
│   ├── analysis/                 # 분석 엔진
│   │   ├── pressure.py           # 🟡 예정: 수압 분석 시각화
│   │   ├── isolation.py          # ✅ 완성: 고립 밸브 (플러그인으로 이식됨)
│   │   └── anomaly.py            # 🔴 예정: 이상 수용가 확인
│   ├── reports/                  # 보고서 자동화
│   └── data_processing/          # 엑셀 ↔ GIS 변환
├── templates/                    # 평가 기준 JSON, QGIS 조판 템플릿
├── data/
│   └── samples/                  # 테스트용 익명화 샘플 데이터
├── output/
│   └── pdf/                      # 자동 생성 보고서 출력
└── docs/                         # 문서 및 블로그 초안
```

---

## ✅ 개발 현황

| 플러그인 | 난이도 | 상태 | 비고 |
|:---|:---:|:---:|:---|
| **고립 밸브 자동 추출** | ⭐⭐⭐ | ✅ **완성** | 오늘(2026-05-15) 완성! |
| **수압 분석 시각화** | ⭐⭐ | 🟡 다음 작업 | Claude Code 코드 이식 예정 |
| **이상 수용가 확인** | ⭐⭐⭐⭐ | 🔴 대기 | sklearn 필요 |

---

## 🚀 다음 작업 목표: 수압 분석 시각화 플러그인

### 핵심 기능 (Claude Code 설계 기준)
- 시계열 통계 (평균/최대/최소/표준편차)
- 이상치 탐지 (IQR, 3σ 룰)
- 기준 압력 대비 적정성 평가 (0.15 ~ 0.40 MPa)
- 압력 분포 히트맵

### 작업 분담
- **옥룡**: 분석 로직 (`PressureAnalyzer` 클래스)
- **청룡**: 플러그인 UI 패키징 + 아이콘 디자인

---

## 📋 CLAUDE.md 핵심 규칙 요약

1. **좌표계**: 거리 계산은 무조건 EPSG:5186
2. **Qt 호환**: `from qgis.PyQt` 사용 (QGIS 4.0 Qt6 호환)
3. **레이어 편집**: `startEditing()` / `commitChanges()` 쌍 필수
4. **대용량 처리**: 100건 이상은 `QgsSpatialIndex` 필수
5. **로깅**: `QgsMessageLog.logMessage()` 사용

---

*이 문서는 청룡이 Antigravity 작업 환경으로 이관하며 작성하였습니다. 🐉✨*
