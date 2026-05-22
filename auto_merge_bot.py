import os
import pandas as pd
from datetime import datetime
import warnings

# pandas의 엑셀 관련 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
warnings.simplefilter(action='ignore', category=FutureWarning)

# 파일 경로 설정 (팀장님 작업 환경 기준)
WORKSPACE = r"c:\Users\채송이\Desktop\Antigravity(AI Work)"
MASTER_FILE = os.path.join(WORKSPACE, "목표유수율_통합관리_양식_V2.xlsx")
INPUT_FOLDER = os.path.join(WORKSPACE, "현장데이터_취합방")

def merge_excel_files():
    print("🚀 [서용이 봇] 현장 데이터 자동 취합 프로세스를 시작합니다...")
    
    if not os.path.exists(INPUT_FOLDER):
        os.makedirs(INPUT_FOLDER)
        print(f"❗ 취합방 폴더가 없어서 새로 생성했습니다. ({INPUT_FOLDER})")
        print("❗ 이곳에 현장 엑셀 파일들을 넣고 다시 실행해 주십시오.")
        return

    # 1. 기존 마스터 파일 읽기
    try:
        # 마스터 엑셀의 '실적_RawData' 시트만 불러옵니다.
        df_master_raw = pd.read_excel(MASTER_FILE, sheet_name='실적_RawData')
    except Exception as e:
        print(f"❌ 에러: 마스터 파일을 읽을 수 없습니다. ({e})")
        return

    new_data_list = []
    processed_files = []

    # 2. 취합방 폴더 내의 모든 엑셀 파일 순회
    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith(".xlsx") and not filename.startswith("~$"):
            file_path = os.path.join(INPUT_FOLDER, filename)
            try:
                # 현장 파일에서 '실적_RawData' 시트를 읽어옵니다.
                df_field = pd.read_excel(file_path, sheet_name='실적_RawData')
                new_data_list.append(df_field)
                processed_files.append(filename)
            except Exception as e:
                print(f"⚠️ 경고: {filename} 파일을 읽는 중 오류가 발생했습니다. (내용 확인 필요) - {e}")

    # 3. 마스터 파일에 병합 (Append)
    if new_data_list:
        # 새로 들어온 현장 데이터들을 하나로 합침
        df_new_all = pd.concat(new_data_list, ignore_index=True)
        # 기존 마스터 데이터 밑에 새로운 데이터 병합
        df_updated_raw = pd.concat([df_master_raw, df_new_all], ignore_index=True)
        
        # 마스터 파일 업데이트 (기존 RawData 시트를 덮어쓰기)
        with pd.ExcelWriter(MASTER_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_updated_raw.to_excel(writer, sheet_name='실적_RawData', index=False)
            
        print(f"\n✅ 성공!! 총 {len(processed_files)}개의 현장 실적이 마스터 파일에 병합되었습니다.")
        
        # 4. 중복 취합 방지를 위해 처리된 파일은 '취합완료_보관함'으로 이동
        archive_folder = os.path.join(INPUT_FOLDER, "취합완료_보관함")
        os.makedirs(archive_folder, exist_ok=True)
        for filename in processed_files:
            # 타임스탬프를 붙여서 이동 (동일 파일명 충돌 방지)
            timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
            new_name = f"완료_{timestamp}_{filename}"
            os.rename(os.path.join(INPUT_FOLDER, filename), os.path.join(archive_folder, new_name))
        print("📦 취합이 완료된 파일들은 '취합완료_보관함'으로 안전하게 이동되었습니다.")
        
    else:
        print("\n💤 취합할 새로운 현장 데이터 파일이 없습니다. 폴더를 확인해 주십시오.")

if __name__ == "__main__":
    merge_excel_files()
