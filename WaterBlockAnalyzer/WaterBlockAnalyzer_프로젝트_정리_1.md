# QGIS 상수도 통합 진단 시스템 (WaterBlockAnalyzer) 프로젝트 정리

> 작성일: 2026년 5월  
> 프로젝트: QGIS + Python 기반 상수도 운영관리 통합 도구 개발  
> 목표: 단계시험, 단수밸브 분석, 종단면도, 간접평가, 보고서 자동화를 하나의 시스템으로 통합

---

## 📋 목차

1. [텔레그램 챗봇 24시간 운영](#1-텔레그램-챗봇-24시간-운영)
2. [QGIS 단계시험 자동화](#2-qgis-단계시험-자동화)
3. [조판 대장 양식 자동 생성](#3-조판-대장-양식-자동-생성)
4. [최단경로 + 종단면도 생성](#4-최단경로--종단면도-생성)
5. [조판 도형 자동 생성 (양식 빌더)](#5-조판-도형-자동-생성-양식-빌더)
6. [프로젝트 시작 - 데이터 점검 및 폴더 구조](#6-프로젝트-시작---데이터-점검-및-폴더-구조)
7. [간접평가 자동화](#7-간접평가-자동화)
8. [엑셀 데이터 연동](#8-엑셀-데이터-연동)
9. [일정 조정 (10년 근속 휴가)](#9-일정-조정-10년-근속-휴가)
10. [한글 보고서 자동화](#10-한글-보고서-자동화)
11. [QGIS 플러그인 제작 로드맵](#11-qgis-플러그인-제작-로드맵)
12. [추가 플러그인 3종](#12-추가-플러그인-3종)

---

## 1. 텔레그램 챗봇 24시간 운영

### 문제
PC를 끄면 텔레그램 봇이 응답하지 않음

### 해결 방안

**1. 클라우드 VPS (가장 일반적)**
- **Oracle Cloud Free Tier**: ARM 서버 4코어/24GB 메모리 평생 무료 (추천)
- **AWS EC2 t2.micro**: 1년 무료, 이후 월 1만원 내외
- **국내 VPS**: 카페24, 가비아 등 월 5천원~1만원대

**2. 라즈베리파이**
- 5만~10만원대 초기비용, 전기료 월 1천원 수준
- 직접 관리 선호 시 적합

**3. 무료 호스팅 플랫폼**
- Render, Railway, Fly.io (무료 티어는 sleep 이슈)
- PythonAnywhere (외부 네트워크 제한 있음)

**추천**: Oracle Cloud Free Tier + Ubuntu + systemd 서비스 등록

---

## 2. QGIS 단계시험 자동화

### 전체 워크플로우

```
폴리곤(시험구간) + 유량값 입력
        ↓
구간 내 관로 추출 (공간 교차)
        ↓
관로 연장 자동 계산
        ↓
단위연장당 유량 산정 (Q/L)
        ↓
양호/보통/불량 자동 판정
```

### 누수 판정 기준 (K-water 참고)

| 구분 | 단위유량 (L/min/km) | 판정 |
|------|---------------------|------|
| 양호 | < 50 | Good |
| 보통 | 50 ~ 100 | Fair |
| 불량 | > 100 | Poor |

### PyQGIS 핵심 코드

```python
from qgis.core import QgsSpatialIndex, QgsGeometry

def analyze_step_test(pipe_layer, zone_layer, 
                      good_threshold=50, fair_threshold=100):
    """단계시험 구간별 누수 판정"""
    zone_layer.startEditing()
    
    for zone in zone_layer.getFeatures():
        zone_geom = zone.geometry()
        total_length = 0.0
        
        for pipe in pipe_layer.getFeatures():
            if zone_geom.intersects(pipe.geometry()):
                intersection = zone_geom.intersection(pipe.geometry())
                total_length += intersection.length()
        
        length_km = total_length / 1000
        unit_flow = zone['flow_loss'] / length_km if length_km > 0 else 0
        
        if unit_flow < good_threshold:
            grade = '양호'
        elif unit_flow < fair_threshold:
            grade = '보통'
        else:
            grade = '불량'
        
        zone['pipe_length_m'] = total_length
        zone['unit_flow'] = unit_flow
        zone['grade'] = grade
        zone_layer.updateFeature(zone)
    
    zone_layer.commitChanges()
```

### 주의사항
- **좌표계**: EPSG:5186 (중부원점) 같은 투영좌표계 필수
- 지리좌표계(WGS84)는 거리 계산 부정확

---

## 3. 조판 대장 양식 자동 생성

### 구현 방법 3가지

**방법 1: QGIS 조판 템플릿(.qpt) 직접 제작 (추천)**
- 한 번 디자인 후 `[% "필드명" %]` 표현식으로 동적 필드 연결
- Atlas(아틀라스) 기능으로 구간별 자동 페이지 생성

**방법 2: 기존 양식 이미지/PDF를 배경으로 사용**
- 회사 표준 양식을 PNG/PDF로 변환 → 조판 배경
- 빈칸 위치에 텍스트 요소만 얹어 좌표 매칭

**방법 3: 엑셀 양식 → openpyxl로 채우기**
- 한국 공공기관 양식이 엑셀 기반이면 유리

### 자동 대장 생성 코드

```python
from qgis.core import (QgsProject, QgsLayoutExporter, 
                      QgsPrintLayout, QgsReadWriteContext)
from qgis.PyQt.QtXml import QDomDocument

def generate_zone_reports(zone_layer, template_path, output_dir):
    """단계시험 구간별 대장 PDF 자동 생성"""
    project = QgsProject.instance()
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    document = QDomDocument()
    document.setContent(template_content)
    
    for feature in zone_layer.getFeatures():
        layout = QgsPrintLayout(project)
        layout.loadFromTemplate(document, QgsReadWriteContext())
        
        zone_layer.selectByIds([feature.id()])
        
        atlas = layout.atlas()
        atlas.setCoverageLayer(zone_layer)
        atlas.setEnabled(True)
        atlas.setFilterFeatures(True)
        atlas.setFilterExpression(f'"id" = {feature.id()}')
        
        exporter = QgsLayoutExporter(layout)
        zone_name = feature['zone_name']
        output_path = os.path.join(output_dir, f'대장_{zone_name}.pdf')
        
        settings = QgsLayoutExporter.PdfExportSettings()
        exporter.exportToPdf(output_path, settings)
```

---

## 4. 최단경로 + 종단면도 생성

### 전체 구조

```
[관로 클릭] → [Dijkstra 최단경로] → [지반고/관저고 추출] → [종단면도 작도] → [PDF 출력]
```

### 최단경로 탐색

```python
from qgis.analysis import (QgsVectorLayerDirector, 
                          QgsNetworkDistanceStrategy,
                          QgsGraphBuilder, QgsGraphAnalyzer)

def find_shortest_path(pipe_layer, start_point, end_point):
    """클릭 지점에서 블록 유입점까지 최단경로 탐색"""
    director = QgsVectorLayerDirector(
        pipe_layer, -1, '', '', '', 
        QgsVectorLayerDirector.DirectionBoth
    )
    strategy = QgsNetworkDistanceStrategy()
    director.addStrategy(strategy)
    
    builder = QgsGraphBuilder(pipe_layer.crs())
    tied_points = director.makeGraph(
        builder, [start_point, end_point]
    )
    graph = builder.graph()
    
    start_id = graph.findVertex(tied_points[0])
    end_id = graph.findVertex(tied_points[1])
    
    tree, cost = QgsGraphAnalyzer.dijkstra(graph, start_id, 0)
    
    if tree[end_id] == -1:
        return None
    
    path_points = []
    curr = end_id
    while curr != start_id:
        path_points.append(graph.vertex(curr).point())
        curr = graph.vertex(graph.edge(tree[curr]).fromVertex()).point()
    path_points.append(start_point)
    path_points.reverse()
    
    return path_points, cost
```

### 종단면도 작도 (matplotlib)

```python
import matplotlib.pyplot as plt

def draw_profile(profile_data, output_path):
    fig, ax = plt.subplots(figsize=(16, 8))
    
    distances = [p['distance'] for p in profile_data]
    grounds = [p['ground'] for p in profile_data]
    inverts = [p['invert'] for p in profile_data]
    
    ax.plot(distances, grounds, 'k-', linewidth=2, label='지반고')
    ax.fill_between(distances, grounds, min(inverts)-2, 
                     color='#D2B48C', alpha=0.3)
    ax.plot(distances, inverts, 'b-', linewidth=2.5, label='관저고')
    
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('누적거리 (m)', fontsize=11)
    ax.set_ylabel('표고 EL.(m)', fontsize=11)
    ax.set_title('관로 종단면도', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
```

---

## 5. 조판 도형 자동 생성 (양식 빌더)

### 가능한 도형 요소

| 요소 | 클래스 | 용도 |
|------|--------|------|
| 사각형/표 셀 | `QgsLayoutItemShape` | 양식 테두리, 칸 |
| 직선 | `QgsLayoutItemShape` (Line) | 구분선 |
| 텍스트 | `QgsLayoutItemLabel` | 제목, 필드명, 값 |
| 지도 프레임 | `QgsLayoutItemMap` | 위치도, 평면도 |
| 이미지 | `QgsLayoutItemPicture` | 로고, 사진, 종단면도 |
| 표(동적) | `QgsLayoutItemAttributeTable` | 속성표 |

### JSON 명세 → 양식 자동 생성

```python
def create_form_template(layout_name, form_spec):
    """딕셔너리 명세로 조판 양식 자동 생성"""
    project = QgsProject.instance()
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)
    
    for item in form_spec['items']:
        if item['type'] == 'rect':
            add_rectangle(layout, item)
        elif item['type'] == 'label':
            add_label(layout, item)
        elif item['type'] == 'map':
            add_map_frame(layout, item)
    
    project.layoutManager().addLayout(layout)
```

### 양식 JSON 예시

```json
{
  "page": {"size": "A4", "orientation": "landscape"},
  "items": [
    {"type": "rect", "x": 10, "y": 10, "w": 277, "h": 15},
    {"type": "label", "x": 10, "y": 10, "w": 277, "h": 15,
     "text": "단계시험 점검 대장", "size": 18, "align": "center"},
    {"type": "label", "x": 70, "y": 30, "w": 80, "h": 8,
     "text": "[% \"zone_name\" %]", "size": 10}
  ]
}
```

---

## 6. 프로젝트 시작 - 데이터 점검 및 폴더 구조

### 데이터 점검 체크리스트

```markdown
## 관로 레이어
- [ ] 관경 필드명
- [ ] 관종 필드명
- [ ] 부설년도 필드명
- [ ] 관 ID 필드명
- [ ] 지반고/관저고 필드 (없으면 DEM에서 추출)
- [ ] 좌표계 (EPSG:5186 권장)

## 밸브/맨홀 레이어
- [ ] 밸브 레이어 존재 여부
- [ ] 종류 구분 필드
- [ ] 블록 유입점 정보

## 보조 데이터
- [ ] DEM 래스터
- [ ] 블록 경계 폴리곤
- [ ] 회사 표준 대장 양식
```

### 폴더 구조 자동 생성 코드

```python
import os

base = r'D:\Projects\WaterBlockAnalyzer'

folders = [
    'data/gis',                 # 원본 shp/gpkg
    'data/excel',               # 원본 엑셀
    'data/converted',           # 엑셀→GIS 변환 결과
    'data/samples',             # 테스트 샘플
    'src/core',                 # 공통 유틸
    'src/actions',              # QGIS 액션
    'src/reports',              # 보고서 생성
    'src/evaluation',           # 평가 엔진
    'src/data_processing',      # 데이터 변환
    'templates',                # 양식 JSON, .qpt
    'output/pdf',               # PDF 결과
    'output/images',            # 이미지 결과
    'tests',
    'docs',
]

for folder in folders:
    path = os.path.join(base, folder)
    os.makedirs(path, exist_ok=True)
    print(f'✅ {path}')
```

---

## 7. 간접평가 자동화

### 평가 항목 (상수도관망 기술진단 매뉴얼 기준)

```
1. 관 재질 (DCIP, SP, PE, ACP 등)
2. 부설년도 (경과년수)
3. 관경
4. 매설심도/토피
5. 도로상태 (포장종류, 교통하중)
6. 토양환경 (부식성)
7. 누수이력 (단위연장당 누수건수)
8. 민원이력 (수질/단수 민원)
9. 수압 적정성
10. 유수율 / 누수율 (블록 단위)
```

### 평가 엔진 코드

```python
def evaluate_indirect(pipe_layer, criteria_config):
    """간접평가 자동 산정"""
    pipe_layer.startEditing()
    
    for pipe in pipe_layer.getFeatures():
        scores = {}
        
        scores['material'] = score_material(
            pipe['MAT'], criteria_config['material'])
        
        age = 2026 - pipe['INST_YEAR']
        scores['age'] = score_age(age, criteria_config['age'])
        
        scores['diameter'] = score_diameter(
            pipe['DIA'], criteria_config['diameter'])
        
        leak_count = count_leaks_nearby(pipe, leak_layer, buffer=5)
        scores['leak'] = score_leak(
            leak_count, pipe.geometry().length())
        
        total = sum(s * criteria_config[k]['weight'] 
                   for k, s in scores.items())
        
        grade = classify_grade(total)
        
        pipe['eval_total'] = total
        pipe['eval_grade'] = grade
        pipe_layer.updateFeature(pipe)
    
    pipe_layer.commitChanges()
```

### 평가 기준 JSON

```json
{
  "material": {
    "weight": 20,
    "scores": {
      "ACP": 100, "GP": 90, "CIP": 80,
      "DCIP": 30, "SP": 40, "PE": 20
    }
  },
  "age": {
    "weight": 25,
    "ranges": [
      {"min": 0, "max": 10, "score": 10},
      {"min": 10, "max": 20, "score": 40},
      {"min": 20, "max": 30, "score": 70},
      {"min": 30, "max": 999, "score": 100}
    ]
  },
  "grade_thresholds": {
    "양호": 30,
    "보통": 50,
    "불량": 70,
    "매우불량": 100
  }
}
```

### 등급별 색상 자동 적용

```python
from qgis.core import (QgsCategorizedSymbolRenderer, 
                      QgsRendererCategory, QgsSymbol)
from qgis.PyQt.QtGui import QColor

def apply_grade_symbology(pipe_layer):
    grade_colors = {
        '양호': QColor(0, 176, 80),
        '보통': QColor(255, 255, 0),
        '불량': QColor(255, 153, 0),
        '매우불량': QColor(255, 0, 0),
    }
    
    categories = []
    for grade, color in grade_colors.items():
        symbol = QgsSymbol.defaultSymbol(pipe_layer.geometryType())
        symbol.setColor(color)
        symbol.setWidth(1.2)
        categories.append(
            QgsRendererCategory(grade, symbol, grade))
    
    renderer = QgsCategorizedSymbolRenderer('eval_grade', categories)
    pipe_layer.setRenderer(renderer)
    pipe_layer.triggerRepaint()
```

---

## 8. 엑셀 데이터 연동

### 3가지 케이스별 처리

**케이스 1: 엑셀에 좌표가 있는 경우**
```python
import pandas as pd

def excel_to_point_layer(excel_path, x_col='X', y_col='Y', 
                         crs='EPSG:5186', layer_name='누수이력'):
    df = pd.read_excel(excel_path)
    
    fields_str = '&'.join([f'field={col}:string' 
                          for col in df.columns])
    layer = QgsVectorLayer(
        f'Point?crs={crs}&{fields_str}', layer_name, 'memory')
    
    layer.startEditing()
    for idx, row in df.iterrows():
        if pd.notna(row[x_col]) and pd.notna(row[y_col]):
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(
                QgsPointXY(row[x_col], row[y_col])))
            for col in df.columns:
                feat[col] = str(row[col]) if pd.notna(row[col]) else ''
            layer.addFeature(feat)
    layer.commitChanges()
    
    return layer
```

**케이스 2: 관 ID로 연결**
- 속성 조인으로 즉시 연결

**케이스 3: 블록/지번 단위 집계**
- 블록 폴리곤과 속성 조인 → 블록 내 관로에 일괄 적용

### 누수이력 → 관로 집계

```python
def aggregate_leak_to_pipe(pipe_layer, leak_layer, 
                          buffer_dist=5, years=3):
    """관로별 누수 건수 집계"""
    spatial_index = QgsSpatialIndex(leak_layer.getFeatures())
    
    pipe_layer.startEditing()
    if pipe_layer.fields().indexFromName('leak_count') == -1:
        pipe_layer.dataProvider().addAttributes([
            QgsField('leak_count', QVariant.Int),
            QgsField('leak_per_km', QVariant.Double),
        ])
        pipe_layer.updateFields()
    
    for pipe in pipe_layer.getFeatures():
        pipe_geom = pipe.geometry()
        buffered = pipe_geom.buffer(buffer_dist, 5)
        candidates = spatial_index.intersects(buffered.boundingBox())
        
        leak_count = sum(
            1 for leak_id in candidates 
            if buffered.contains(leak_layer.getFeature(leak_id).geometry())
        )
        
        length_km = pipe_geom.length() / 1000
        leak_per_km = leak_count / length_km / years if length_km > 0 else 0
        
        pipe['leak_count'] = leak_count
        pipe['leak_per_km'] = leak_per_km
        pipe_layer.updateFeature(pipe)
    
    pipe_layer.commitChanges()
```

### 엑셀 표준화 양식

**누수이력**
```
columns = ['leak_id', 'leak_date', 'address', 'x_coord', 'y_coord',
           'pipe_id', 'pipe_dia', 'pipe_mat', 'leak_cause', 
           'leak_amount', 'repair_method']
```

**민원이력**
```
columns = ['complaint_id', 'date', 'block_name', 'address',
           'category', 'detail', 'status']
```

**수압측정**
```
columns = ['station_id', 'date', 'x_coord', 'y_coord',
           'block_name', 'pressure', 'flow']
```

---

## 9. 일정 조정 (10년 근속 휴가)

### 옵션 C: 분할 전략 (추천)

```
🟢 5월 후반 (휴가 전, 2~3주)
   - 폴더 구조 + GIS 데이터 점검
   - 엑셀 파일 3개 컬럼 구조 정리
   - 단계시험 분석 스크립트 검증
   - Plugin Builder로 뼈대 생성

🌴 6월 (10년 근속 휴가 한 달)
   - 휴식 우선
   - 여유 있을 때만 가볍게 학습
   - 블로그 글감 메모

🔵 7월 복귀 후 (3~4주)
   - 수압 분석 시각화 플러그인 ⭐ 첫 작품
   - QGIS 공식 저장소 등록 도전
   - 블로그 시리즈 작성

🟣 8월~
   - 두 번째 플러그인 (고립 밸브)
   - 점진적 확장
```

---

## 10. 한글 보고서 자동화

### 추천: pyhwpx (한컴 공식 COM API)

**설치**
```bash
pip install pyhwpx
```

**기본 사용법**
```python
from pyhwpx import Hwp

hwp = Hwp(visible=False)
hwp.open(r'D:/templates/평가보고서_양식.hwpx')

# 누름틀(필드)에 값 채우기
hwp.put_field_text('블록명', 'B-105')
hwp.put_field_text('관연장', '287.5')
hwp.put_field_text('평가등급', '불량')

# 이미지 삽입
hwp.move_to_field('평면도위치')
hwp.insert_picture(r'D:/output/images/profile_B105.png')

hwp.save_as(r'D:/output/평가보고서_B105.hwpx')
hwp.close()
```

### 양식 분리 전략

```
📑 최종 보고서 (.hwpx)
│
├── 📄 본문/표 → pyhwpx로 자동 채우기
├── 🗺️ 평면도 → QGIS 조판에서 PNG export → 한글에 삽입
├── 📊 종단면도 → matplotlib PNG → 한글에 삽입
├── 📈 그래프 → matplotlib PNG → 한글에 삽입
└── 📋 통계표 → pandas → 한글 표에 삽입
```

### 양식 작성 규칙

**한글에서 "누름틀" 기능 사용**
- 한글 메뉴: 입력 → 누름틀 → 필드 이름 지정
- `put_field_text('필드명', '값')`으로 정확히 채워짐
- 위치/서식 안 흐트러짐

---

## 11. QGIS 플러그인 제작 로드맵

### 플러그인 개발 학습 경로

**1단계: Plugin Builder로 뼈대 생성**
```
QGIS → 플러그인 → Plugin Builder
→ 이름/카테고리 입력
→ 자동 뼈대 생성
```

**2단계: Qt Designer로 UI 만들기**
- 드래그앤드롭으로 다이얼로그 디자인
- .ui 파일로 저장 후 Python에서 자동 로드

**3단계: 분석 로직 연결**
- 검증된 스크립트를 `core/analyzer.py`에 이식

**4단계: 테스트 및 배포**
- QGIS Plugin Repository 업로드 또는 ZIP 배포

### 기본 플러그인 구조

```
PluginName/
├── __init__.py              # 진입점
├── metadata.txt             # 플러그인 정보
├── plugin_main.py           # 메인 클래스
├── plugin_dialog.py         # UI 다이얼로그
├── plugin_dialog.ui         # Qt Designer UI
├── core/
│   ├── analyzer.py          # 분석 엔진
│   └── styler.py            # 심볼로지
├── resources/
│   ├── icon.png
│   └── resources.qrc
└── README.md
```

---

## 12. 추가 플러그인 3종

### 종합 평가

| 플러그인 | 난이도 | 개발기간 | 차별성 |
|---------|--------|---------|--------|
| **1. 이상 수용가 확인** | ⭐⭐⭐⭐ | 14~20일 | 매우 높음 |
| **2. 고립확인 밸브 추출** | ⭐⭐⭐ | 7~10일 | 높음 |
| **3. 수압 측정/분석 시각화** | ⭐⭐ | 5~7일 | 보통 |

**추천 개발 순서**: 3 → 2 → 1 (쉬운 것부터)

### 🔵 플러그인 3: 수압 분석 시각화 (첫 작품 추천)

**기능**
- 시계열 통계 (평균/최대/최소/표준편차)
- 이상치 탐지 (3σ 룰, IQR)
- 기준 압력 대비 적정성 평가 (0.15~0.40 MPa)
- 압력 분포 히트맵

**핵심 코드**
```python
class PressureAnalyzer:
    def calculate_statistics(self):
        return self.df.groupby(self.m['station'])[
            self.m['pressure']].agg(['mean', 'std', 'min', 'max'])
    
    def detect_outliers(self, method='iqr'):
        outliers = []
        for station, group in self.df.groupby(self.m['station']):
            pressures = group[self.m['pressure']]
            q1, q3 = pressures.quantile([0.25, 0.75])
            iqr = q3 - q1
            mask = (pressures < q1 - 1.5*iqr) | (pressures > q3 + 1.5*iqr)
            outliers.append(group[mask])
        return pd.concat(outliers) if outliers else pd.DataFrame()
    
    def evaluate_adequacy(self, min_p=0.15, max_p=0.40):
        result = self.df.copy()
        conditions = [
            result[self.m['pressure']] < min_p,
            result[self.m['pressure']] > max_p,
        ]
        result['adequacy'] = np.select(
            conditions, ['부족', '과다'], default='적정')
        return result
```

### 🟡 플러그인 2: 고립 밸브 추출

**기능**
- 네트워크 분석으로 격리 가능한 최소 밸브 조합 찾기
- 격리 시 영향받는 수용가 범위 계산
- 대체 공급경로 존재 여부 확인 (환상망)

**핵심 알고리즘**
```python
class IsolationFinder:
    def find_isolation_valves(self, target_point):
        """대상 지점을 격리하는 최소 밸브 조합"""
        target_vertex = self._find_nearest_vertex(target_point)
        valves_to_close = []
        visited = set()
        queue = [target_vertex]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            for edge_id in self.graph.vertex(current).outgoingEdges():
                edge = self.graph.edge(edge_id)
                edge_geom = self._edge_to_geometry(edge)
                
                valve_on_edge = self._find_valve_on_edge(edge_geom)
                if valve_on_edge:
                    valves_to_close.append(valve_on_edge)
                else:
                    next_vertex = edge.toVertex()
                    if next_vertex not in visited:
                        queue.append(next_vertex)
        
        return valves_to_close
```

### 🔴 플러그인 1: 이상 수용가 확인

**기능**
- 전월/전년 대비 증감률 계산
- Z-score 기반 이상값 탐지
- 관경별/용도별 사용 패턴 비교
- Isolation Forest로 미묘한 패턴 변화 탐지
- 누수의심/도수의심/검토필요 자동 분류

**핵심 코드**
```python
from sklearn.ensemble import IsolationForest

class CustomerAnomalyDetector:
    def detect_month_over_month(self, threshold_pct=50):
        df = self.usage.sort_values(['customer_id', 'year_month'])
        df['prev_usage'] = df.groupby('customer_id')['usage'].shift(1)
        df['mom_change_pct'] = (
            (df['usage'] - df['prev_usage']) / df['prev_usage'] * 100
        )
        anomalies = df[abs(df['mom_change_pct']) > threshold_pct].copy()
        anomalies['type'] = np.where(
            anomalies['mom_change_pct'] > 0, '급증', '급감')
        return anomalies
    
    def detect_pattern_change(self):
        pivot = self.usage.pivot(
            index='customer_id', columns='year_month', values='usage')
        recent_12 = pivot.iloc[:, -12:].fillna(0)
        prev_12 = pivot.iloc[:, -24:-12].fillna(0)
        features = recent_12.values - prev_12.values
        
        iso = IsolationForest(contamination=0.05, random_state=42)
        anomaly_score = iso.fit_predict(features)
        
        result = recent_12.copy()
        result['is_anomaly'] = anomaly_score == -1
        return result[result['is_anomaly']]
```

---

## 📅 최종 1년 로드맵

```
🟢 5월 후반: 데이터 정리 + 단계시험 스크립트
🌴 6월: 10년 근속 휴가 (충전!)
🔵 7월: 수압 분석 시각화 플러그인 ⭐ 첫 작품
🟡 8월: 고립 밸브 추출 플러그인
🟢 9월: 단계시험 분석기 플러그인
🔴 10~12월: 이상 수용가 확인 플러그인
🌟 다음 해: 통합 시스템 (WaterBlockAnalyzer)으로 묶기
```

---

## 🏗️ 최종 통합 시스템 구조

```
WaterBlockAnalyzer/
├── data/
│   ├── gis/                    # 원본 shp/gpkg
│   ├── excel/                  # 원본 엑셀
│   ├── converted/              # 변환 결과
│   └── samples/                # 테스트 샘플
│
├── src/
│   ├── core/                   # 공통 유틸
│   ├── actions/
│   │   ├── valve_finder.py     # 단수밸브
│   │   ├── shortest_path.py    # 최단경로
│   │   └── step_test.py        # 단계시험
│   ├── evaluation/
│   │   ├── indirect_eval.py    # 간접평가
│   │   ├── grade_renderer.py   # 등급 시각화
│   │   └── leak_analysis.py    # 누수 분석
│   ├── analysis/
│   │   ├── pressure.py         # 수압 분석
│   │   ├── isolation.py        # 고립 밸브
│   │   └── anomaly.py          # 이상 수용가
│   ├── reports/
│   │   ├── form_builder.py     # 양식 빌더
│   │   ├── profile_drawer.py   # 종단면도
│   │   ├── pdf_exporter.py     # PDF 출력
│   │   └── hwp_report.py       # 한글 보고서
│   └── data_processing/
│       └── excel_converter.py  # 엑셀 변환
│
├── templates/
│   ├── eval_criteria.json      # 평가 기준
│   ├── ledger_form.json        # 대장 양식
│   └── *.qpt                   # QGIS 조판 템플릿
│
├── output/
│   ├── pdf/
│   └── images/
│
├── tests/
└── docs/
```

---

## 💡 핵심 원칙

1. **MVP부터 시작**: 완벽하게 설계하고 시작하면 절대 못 끝낸다
2. **단계별 검증**: 각 단계가 동작해야 다음으로 넘어간다
3. **데이터 표준화 먼저**: 엑셀 데이터 양식 통일이 자동화의 시작
4. **재사용 가능한 모듈**: 각 플러그인은 독립적이면서 통합 가능하게
5. **블로그로 기록**: "독학 설계" 시리즈로 단계별 정리
6. **버전 관리 필수**: Git private 저장소 활용

---

## 📚 참고 자료

- 환경부 상수도관망 기술진단 매뉴얼 (2021)
- 상수관로 정밀조사 매뉴얼 (2020.6)
- KDS 57 00 00 상수도설계기준
- QGIS Python API 문서: https://qgis.org/pyqgis/
- pyhwpx: https://github.com/martiniifun/pyhwpx

---

*이 문서는 안티그라비티 등 외부 IDE에서도 활용할 수 있도록 정리된 프로젝트 가이드입니다.*  
*프로젝트 진행 중 지속적으로 업데이트하세요.*
