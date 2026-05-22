import os
import math
from pypdf import PdfReader, PdfWriter

DIRECTORY = r"c:\Users\채송이\Desktop\Antigravity(AI Work)\기술지침_보관함"
MAX_SIZE_MB = 45 # 구글 업로드 안정성을 위해 45MB 기준으로 분할
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
OUTPUT_DIR = os.path.join(DIRECTORY, "분할완료_업로드용")

def split_pdf(file_path, file_name, file_size):
    print(f"🚨 초거대 파일 감지: {file_name} ({file_size / 1024 / 1024:.1f}MB)")
    num_parts = math.ceil(file_size / MAX_SIZE_BYTES)
    
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
    except Exception as e:
        print(f"  ❌ 읽기 실패 (암호화 등): {e}")
        return

    pages_per_part = math.ceil(total_pages / num_parts)
    base_name, ext = os.path.splitext(file_name)
    
    suffixes = ["상권", "하권"] if num_parts == 2 else ["상권", "중권", "하권"] if num_parts == 3 else [f"{i+1}권" for i in range(num_parts)]
    
    for i in range(num_parts):
        writer = PdfWriter()
        start_page = i * pages_per_part
        end_page = min((i + 1) * pages_per_part, total_pages)
        
        for p in range(start_page, end_page):
            writer.add_page(reader.pages[p])
            
        part_suffix = suffixes[i]
        output_name = f"{base_name}_{part_suffix}{ext}"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        
        print(f"  ✅ 분할 완료: {output_name} ({start_page+1}~{end_page}페이지)")

def main():
    print("========================================")
    print("✂️ NotebookLM 업로드용 PDF 분할 작업 시작 ✂️")
    print("========================================")
    
    count = 0
    for file_name in os.listdir(DIRECTORY):
        if not file_name.lower().endswith(".pdf"):
            continue
            
        file_path = os.path.join(DIRECTORY, file_name)
        if not os.path.isfile(file_path):
            continue
            
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_SIZE_BYTES:
            count += 1
            split_pdf(file_path, file_name, file_size)
            
    print("========================================")
    print(f"🎉 총 {count}개의 거대 파일 분할이 완료되었습니다!")
    print(f"저장 위치: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
