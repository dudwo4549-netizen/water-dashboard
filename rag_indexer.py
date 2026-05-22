import os
import json
import time
import sys
from pypdf import PdfReader

# Windows 콘솔 출력 인코딩 오류 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

GUIDELINES_DIR = r"c:\Users\채송이\Desktop\Antigravity(AI Work)\기술지침_보관함"
CACHE_FILE = os.path.join(GUIDELINES_DIR, "guidelines_cache.json")
MAX_FILE_SIZE_MB = 15  # 인덱싱할 최대 파일 크기 (너무 큰 파일은 스킵하거나 앞부분만 인덱싱)
MAX_PAGES_PER_LARGE_PDF = 30  # 큰 PDF의 경우 인덱싱할 최대 페이지 수

def clean_text(text):
    if not text:
        return ""
    # 연속된 공백 및 줄바꿈 정리
    lines = [line.strip() for line in text.splitlines()]
    return " ".join([l for l in lines if l])

def index_md_file(file_path):
    chunks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 헤더나 문단 단위 분할 (간단히 빈 줄 두 개 이상으로 분할)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            if len(para) > 50:  # 최소 길이 필터
                chunks.append({
                    "file": os.path.basename(file_path),
                    "page": idx + 1,
                    "text": para
                })
    except Exception as e:
        print(f"Error indexing MD {file_path}: {e}")
    return chunks

def index_pdf_file(file_path):
    chunks = []
    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
        
        # 너무 큰 PDF는 페이지 제한 적용
        pages_to_read = num_pages
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        if file_size > MAX_FILE_SIZE_MB:
            pages_to_read = min(num_pages, MAX_PAGES_PER_LARGE_PDF)
            print(f"Large PDF detected ({file_size:.1f}MB). Limiting to first {pages_to_read} pages: {os.path.basename(file_path)}")
            
        for page_num in range(pages_to_read):
            page = reader.pages[page_num]
            text = page.extract_text()
            cleaned = clean_text(text)
            
            # 페이지 내에서 문단 나누기 (줄바꿈이나 마침표 기준)
            sentences = cleaned.split(". ")
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                current_chunk.append(sentence)
                current_length += len(sentence)
                if current_length > 400:  # 약 400자 내외로 청킹
                    text_block = ". ".join(current_chunk) + "."
                    chunks.append({
                        "file": os.path.basename(file_path),
                        "page": page_num + 1,
                        "text": text_block
                    })
                    current_chunk = []
                    current_length = 0
            
            if current_chunk:
                text_block = ". ".join(current_chunk)
                if len(text_block) > 50:
                    chunks.append({
                        "file": os.path.basename(file_path),
                        "page": page_num + 1,
                        "text": text_block
                    })
    except Exception as e:
        print(f"Error indexing PDF {file_path}: {e}")
    return chunks

def run_indexer():
    print("🔍 RAG 인덱서가 지침 보관함을 스캔 중입니다...")
    
    # 기존 캐시 로드
    cache_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as e:
            print(f"Failed to load existing cache: {e}")
            cache_data = {}
            
    files_in_cache = cache_data.get("files", {})
    all_chunks = cache_data.get("chunks", [])
    
    updated = False
    
    # 보관함 파일 목록 스캔
    for filename in os.listdir(GUIDELINES_DIR):
        file_path = os.path.join(GUIDELINES_DIR, filename)
        if not os.path.isfile(file_path):
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".md"]:
            continue
            
        mtime = os.path.getmtime(file_path)
        
        # 파일이 신규이거나 수정되었는지 체크
        if filename not in files_in_cache or files_in_cache[filename]["mtime"] < mtime:
            print(f"🆕 인덱싱 대상 파일 감지: {filename}")
            
            # 기존 캐시에서 해당 파일 관련 청크 제거
            all_chunks = [c for c in all_chunks if c["file"] != filename]
            
            # 인덱싱 시작
            new_chunks = []
            if ext == ".md":
                new_chunks = index_md_file(file_path)
            elif ext == ".pdf":
                new_chunks = index_pdf_file(file_path)
                
            all_chunks.extend(new_chunks)
            files_in_cache[filename] = {
                "mtime": mtime,
                "chunk_count": len(new_chunks)
            }
            updated = True
            print(f"✅ 완료: {filename} ({len(new_chunks)} 청크 생성)")

    if updated:
        # 캐시 저장
        output = {
            "files": files_in_cache,
            "chunks": all_chunks,
            "last_updated": time.time()
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"💾 guidelines_cache.json 업데이트 완료! 총 {len(all_chunks)}개 청크 보관 중.")
    else:
        print("✅ 변경 사항 없음. 캐시가 최신 상태입니다.")

if __name__ == "__main__":
    run_indexer()
