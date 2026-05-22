import os
import sys
import json
import pandas as pd
import random
import re
import google.generativeai as genai
from flask import Flask, jsonify, send_from_directory, request

# Windows 콘솔 및 내부 문자열 인코딩 에러 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder='dashboard')
WORKSPACE = r"c:\Users\채송이\Desktop\Antigravity(AI Work)"
EXCEL_FILE = os.path.join(WORKSPACE, "목표유수율_통합관리_양식_V2.xlsx")
CACHE_FILE = os.path.join(WORKSPACE, "기술지침_보관함", "guidelines_cache.json")

# 위경도 더미 생성기 (지도 표시용)
def get_dummy_coords(site_name):
    random.seed(site_name)
    lat = 35.5 + random.random() * 2.0 # 한국 위도 범위 일부
    lng = 127.0 + random.random() * 2.0 # 한국 경도 범위 일부
    return [lat, lng]

# RAG 지침서 검색 함수
def search_guidelines(query, top_k=5):
    if not os.path.exists(CACHE_FILE):
        return []
    
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
    except Exception as e:
        print(f"Error loading cache for search: {e}")
        return []
        
    chunks = cache_data.get("chunks", [])
    if not chunks:
        return []
        
    # 쿼리에서 명사/영문/숫자 키워드 분리
    keywords = re.findall(r'[가-힣a-zA-Z0-9]+', query.lower())
    if not keywords:
        return []
        
    scores = []
    for chunk in chunks:
        score = 0
        text_lower = chunk["text"].lower()
        for kw in keywords:
            if kw in text_lower:
                # 키워드 출현 횟수만큼 점수 부여
                score += text_lower.count(kw) * 5
                # 완전 단어 매칭 시 추가 가산점
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    score += 10
        if score > 0:
            scores.append((score, chunk))
            
    # 높은 점수순 정렬 후 상위 반환
    scores.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scores[:top_k]]

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# 1. 기존 유수율 실적 조회 API
@app.route('/api/data')
def get_data():
    try:
        df_master = pd.read_excel(EXCEL_FILE, sheet_name='현장_마스터')
        df_raw = pd.read_excel(EXCEL_FILE, sheet_name='실적_RawData')
        
        df_latest = df_raw.sort_values('입력일자').groupby('현장명').last().reset_index()
        df_merged = pd.merge(df_latest, df_master[['현장명', '사업구분', '목표 유수율 (%)']], on='현장명', how='left')
        
        latest_result = []
        for _, row in df_merged.iterrows():
            target = float(row['목표 유수율 (%)']) if pd.notnull(row['목표 유수율 (%)']) else 0
            current = float(row['누적 유수율 (%)']) if pd.notnull(row['누적 유수율 (%)']) else (float(row['현재 유수율 (%)']) if pd.notnull(row['현재 유수율 (%)']) else 0)
            gap = float(row['누적 미달률 (%)']) if pd.notnull(row['누적 미달률 (%)']) else round(target - current, 2)
            
            status = 'success'
            if gap >= 3.0: status = 'danger'
            elif gap > 0: status = 'warning'
                
            latest_result.append({
                'name': str(row['현장명']),
                'type': str(row['사업구분']) if pd.notnull(row['사업구분']) else "기타",
                'target': target,
                'current': current,
                'gap': gap,
                'status': status,
                'coords': get_dummy_coords(str(row['현장명']))
            })
            
        monthly_stats = {
            'labels': ['1월', '2월', '3월', '4월', '5월', '6월'],
            'avg_nrw': [78.5, 79.2, 80.1, 81.5, 82.4, 83.1]
        }
        
        return jsonify({
            'latest': latest_result,
            'monthly': monthly_stats
        })
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

# 2. WBS 공정 및 일정 조회 API
@app.route('/api/schedule')
def get_schedule():
    try:
        df_master = pd.read_excel(EXCEL_FILE, sheet_name='현장_마스터')
        df_raw = pd.read_excel(EXCEL_FILE, sheet_name='실적_RawData')
        
        df_latest = df_raw.sort_values('입력일자').groupby('현장명').last().reset_index()
        df_merged = pd.merge(df_master, df_latest, on='현장명', how='left')
        
        def parse_dt(val, default_val):
            if pd.isnull(val):
                return default_val
            if hasattr(val, 'strftime'):
                return val.strftime('%Y-%m-%d')
            try:
                dt = pd.to_datetime(val)
                if pd.notnull(dt):
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            return str(val).split()[0] if val else default_val

        schedule_result = []
        for _, row in df_merged.iterrows():
            # 날짜 변환 및 포맷팅
            start_date = parse_dt(row['착수일'], "2026-01-01")
            end_date = parse_dt(row['준공일'], "2026-12-31")
            target_date = parse_dt(row['성과판정(달성) 기준일'], "2026-11-30")
            
            # WBS 진행 지표 수치화
            block_total = float(row['블록 대상 수량']) if pd.notnull(row['블록 대상 수량']) else 1.0
            block_done = float(row['블록구축 완료 수량']) if pd.notnull(row['블록구축 완료 수량']) else 0.0
            block_progress = min(100.0, round((block_done / block_total) * 100, 1))
            
            leak_target = float(row['목표 누수탐사 건수']) if pd.notnull(row['목표 누수탐사 건수']) else 1.0
            leak_done = float(row['누적 누수탐사 건수']) if pd.notnull(row['누적 누수탐사 건수']) else 0.0
            leak_progress = min(100.0, round((leak_done / leak_target) * 100, 1))
            
            # 종합 공정률 계산 (WBS 가중치 대략 적용: WBS 1~3단계 40%, 4단계 40%, 5~6단계 20%)
            overall_progress = round((block_progress * 0.4) + (leak_progress * 0.4) + 20.0, 1)
            if block_progress == 0 and leak_progress == 0:
                overall_progress = 10.0 # 착수 및 기존 자료 수집 상태
            elif overall_progress >= 95.0:
                overall_progress = 98.0 if block_done < block_total or leak_done < leak_target else 100.0
                
            # WBS 단계 매핑
            wbs_phase = "1.1 사업 착수"
            if overall_progress < 20.0:
                wbs_phase = "1.1 착수 및 자료수집"
            elif overall_progress < 40.0:
                wbs_phase = "1.2 기초 조사 및 모델링"
            elif overall_progress < 70.0:
                wbs_phase = "1.3 블록 구축 및 고립"
            elif overall_progress < 90.0:
                wbs_phase = "1.4 관망 정비 및 누수 탐사"
            elif overall_progress < 98.0:
                wbs_phase = "1.5 성과 판정 평가"
            else:
                wbs_phase = "1.6 사업 완료 및 인계"
                
            schedule_result.append({
                'name': str(row['현장명']),
                'manager': str(row['팀장']) if pd.notnull(row['팀장']) else "미지정",
                'type': str(row['사업구분']) if pd.notnull(row['사업구분']) else "기타",
                'startDate': start_date,
                'endDate': end_date,
                'targetDate': target_date,
                'blockTotal': int(block_total),
                'blockDone': int(block_done),
                'blockProgress': block_progress,
                'leakTarget': int(leak_target),
                'leakDone': int(leak_done),
                'leakProgress': leak_progress,
                'progress': overall_progress,
                'wbsPhase': wbs_phase,
                'remarks': str(row['특이사항']) if pd.notnull(row['특이사항']) else "",
                'direction': str(row['개선방향']) if pd.notnull(row['개선방향']) else ""
            })
            
        return jsonify(schedule_result)
    except Exception as e:
        print(f"Schedule API Error: {e}")
        return jsonify({"error": str(e)}), 500

# 3. RAG 기반 기술 지침서 상담 AI API
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        query = data.get("query", "")
        user_api_key = data.get("apiKey") or os.environ.get("GEMINI_API_KEY")
        
        if not query:
            return jsonify({"error": "질문 내용이 없습니다."}), 400
            
        if not user_api_key:
            return jsonify({
                "response": "⚠️ **Gemini API Key가 설정되지 않았습니다.** 대시보드 화면 우측 상단의 ⚙️ 설정 아이콘을 클릭하여 API Key를 등록해 주시거나 시스템 환경변수 `GEMINI_API_KEY`를 설정해 주십시오."
            })
            
        # 1. RAG 유사 지침 문장 검색
        retrieved = search_guidelines(query, top_k=4)
        
        # 2. 콘텍스트 결합
        context_str = ""
        sources = []
        for c in retrieved:
            context_str += f"\n[{c['file']} - {c['page']}페이지]:\n{c['text']}\n"
            source_info = f"{c['file']} (p.{c['page']})"
            if source_info not in sources:
                sources.append(source_info)
                
        # 3. Gemini 프롬프트 작성
        prompt = f"""
당신은 상하수도 지침 및 설계 법규, 기술 자문을 담당하는 **AI 챗봇**입니다. 
제공되는 [기술지침서 및 매뉴얼 발췌본] 자료를 바탕으로 질문에 상세하고 친절히 조언하십시오.

[답변 가이드라인]:
1. 전문 기술 자문관답게 논리적이고 차분한 신뢰감을 주도록 기술 기준에 기반해 답변합니다.
2. 질문에 구체적인 설계 기준, 절차, 노하우(예: 차단 순서, MNF 분석법, 밸브 세팅 등)가 있다면 본문 근거를 최대한 보강해서 설명하십시오.
3. 답변 마지막에는 반드시 참고한 파일들과 페이지 정보(출처)를 명확히 나열하십시오.
4. 만약 아래 제공된 지침서 발췌본에 직접적인 언급이 없다면, 억지로 답변을 꾸며내지 말고 "자료실 문서에 해당 구절이 없으나 상하수도 일반설계기준(KDS) 및 현장 노하우를 바탕으로 자문하자면..." 형태로 솔직하면서도 깊이 있게 조언하십시오.

[기술지침서 및 매뉴얼 발췌본]:
{context_str if context_str else "(일치하는 로컬 지침서 데이터가 검색되지 않았습니다. 일반 지식을 토대로 자문해 드립니다.)"}

[질문]:
{query}
"""
        
        # 4. Gemini API 호출
        genai.configure(api_key=user_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')  # 최신 경량 모델
        response = model.generate_content(prompt)
        
        # 5. 응답 구성
        source_suffix = ""
        if sources:
            source_suffix = "\n\n---\n**📚 참고 지침 문서 출처:**\n" + "\n".join([f"- {s}" for s in sources])
            
        final_answer = response.text + source_suffix
        return jsonify({"response": final_answer})
        
    except Exception as e:
        print(f"Chat API Error: {e}")
        return jsonify({"response": f"❌ **서용이 봇 처리 오류 발생:** {str(e)}"}), 500

if __name__ == '__main__':
    print("🚀 공정관리 및 목표유수율 RAG 통합 대시보드 서버 가동 중...")
    app.run(host='0.0.0.0', port=5000)
