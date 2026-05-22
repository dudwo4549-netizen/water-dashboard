# 💧 상수도 통합 성과관리 대시보드 - 깃허브 배포 가이드 (GitHub Pages)

본 대시보드는 백엔드 서버가 필요 없는 **완전한 정적(Serverless) 웹 애플리케이션**으로 설계되었습니다. 따라서 깃허브 페이지(GitHub Pages)를 통해 무료로 호스팅하고 다른 사람들과 즉시 공유할 수 있습니다.

---

## 🚀 깃허브 페이지 배포 단계

### 1단계: 깃허브 저장소(Repository) 생성
1. [GitHub](https://github.com)에 로그인합니다.
2. 우측 상단의 **`New`** 버튼 또는 `Repositories` 탭에서 **`New`**를 클릭하여 새 저장소를 생성합니다.
3. **Repository name**에 원하는 이름(예: `water-loss-dashboard`)을 기입합니다.
4. **Public**으로 설정합니다. (GitHub Pages 무료 호스팅을 위해서는 Public 저장소여야 합니다.)
5. 다른 설정(README, .gitignore 추가 등)은 건드리지 않고 맨 아래 **`Create repository`**를 클릭합니다.

### 2단계: 로컬 dashboard 폴더 업로드
Git이 설치된 환경(또는 Git Bash / PowerShell)에서 `dashboard` 폴더 위치로 이동한 뒤 아래 명령어를 실행하여 파일들을 업로드합니다.

```bash
# dashboard 폴더로 이동 (이미 폴더 내부라면 생략)
cd "c:\Users\채송이\Desktop\Antigravity(AI Work)\dashboard"

# Git 저장소 초기화
git init

# 브랜치 이름을 main으로 변경
git branch -M main

# 모든 파일 추가 (html, css, js 및 json 데이터 파일들)
git add .

# 첫 커밋 작성
git commit -m "Initial commit of static dashboard"

# 생성한 깃허브 원격 저장소 주소 연결 (본인의 깃허브 ID와 저장소명으로 수정)
git remote add origin https://github.com/본인의깃허브ID/water-loss-dashboard.git

# 원격 저장소로 푸시
git push -u origin main
```

*(참고: 10MB 크기의 지침서 데이터 `guidelines_cache.json` 파일도 깃허브의 파일 크기 제한인 100MB 이내이므로 정상적으로 업로드됩니다.)*

### 3단계: 깃허브 페이지(GitHub Pages) 활성화
1. 깃허브 웹사이트의 해당 저장소 화면으로 이동합니다.
2. 상단 탭 중 **`⚙️ Settings`** (설정)를 클릭합니다.
3. 좌측 사이드바 메뉴에서 **`Pages`**를 클릭합니다.
4. **Build and deployment** 섹션 아래의 **Source**가 `Deploy from a branch`로 설정되어 있는지 확인합니다.
5. **Branch** 설정에서 `None`으로 되어 있는 드롭다운을 클릭하여 **`main`** 브랜치로 변경하고, 우측의 폴더 경로는 **`/ (root)`**로 둔 채 **`Save`** 버튼을 클릭합니다.
6. 1~2분 정도 기다리면 설정 화면 상단에 배포 완료 알림과 함께 공개 접속 주소(URL)가 나타납니다.
   - 예시 주소: `https://본인의깃허브ID.github.io/water-loss-dashboard/`

---

## 🔒 보안 및 공유 방법

### 1. Gemini API Key 보안 정책
- 이 대시보드는 정적 웹페이지이므로 코드 내에 API Key가 하드코딩되어 있지 않습니다.
- 따라서 타인에게 배포 URL을 공유하더라도 **개인의 API Key가 유출될 염려가 전혀 없습니다.**
- 대시보드를 공유받은 사용자는 화면 우측 상단의 **`⚙️ 설정`** 버튼을 클릭하여 본인의 Google Gemini API Key를 입력해야 AI 기술자문 기능을 사용할 수 있습니다.
- 입력된 Key는 브라우저의 로컬 저장소(`localStorage` / `sessionStorage`)에만 임시 저장되며, 외부 서버로 공유되지 않고 Google 공식 API 서버로 직접 요청을 보낼 때만 사용됩니다.

### 2. 정적 데이터 업데이트 방법
- 주차별 엑셀 보고서(`목표유수율 현황 보고`)에 새로운 데이터가 추가된 경우, 로컬에서 `python scratch/compile_static_data.py`를 실행하여 `data.json`과 `schedule.json`을 갱신합니다.
- 갱신된 파일들을 깃허브에 다시 푸시하면 대시보드에 자동으로 최신 데이터가 반영됩니다:
  ```bash
  git add data.json schedule.json
  git commit -m "Update weekly water flow rate data"
  git push origin main
  ```

