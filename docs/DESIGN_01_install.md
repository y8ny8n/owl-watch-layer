# ① 설치·기동 설계 (OWL MVP)

> 상태: 확정 (2026-07)
> 범위: 설치 마법사(install.sh) + 기동 흐름 + 분석 대상 자동 감지
> 코드는 아직 없음 — 전체 설계 확정 후 구현.

---

## 0. 설정 계약 (고정 — 뒤 단계는 이 값을 전제로 설계)

마법사가 모아 `.env`에 쓰는 값. **제품 선택은 없음**(자동 감지로 대체).

```
AI_PROVIDER      ollama | endpoint | openai | gemini | anthropic
AI_MODEL         예: qwen2.5:3b
AI_BASE_URL      endpoint/사내 LLM일 때
AI_API_KEY       외부 API일 때만
ADMIN_PORT       기본 8099
DATA_SOURCE      db | mcp
DB_HOST/PORT/NAME/USER/PASSWORD   (db일 때)
MCP_URL / MCP_TOKEN               (mcp일 때, MVP는 옵션 노출)
ANALYSIS_WINDOW  1d | 7d | 30d   (렌즈 기본값)
ANALYSIS_CYCLE   daily | manual
```

---

## 1. 진입 & 전제
- 사용자: 리눅스 서버에서 clone/tar 풀고 `./install.sh` 한 줄.
- 전제: Docker + docker compose (없으면 감지해 안내만).
- 의존성 0 — 순수 bash `read` + 컬러 출력. (whiptail TUI는 선택, MVP는 plain)

## 2. 마법사 전체 흐름 (4단계)
```
헤더 → 사전점검(docker) → [4단계 질문] → 설정 요약·확인
→ .env 작성 → (로컬이면)모델 pull → compose up → 헬스체크 → 완료 안내
   분석 대상 제품은 "묻지 않고" 연결된 로그에서 자동 감지
```

## 3. 단계별 상세

### STEP 1 · AI 엔진
```
어떤 AI로 분석 요약을 만들까요?
  1) 로컬 Ollama      (권장 · 데이터 안 나감)
  2) 사내 자체 LLM    (운영 중 엔드포인트)
  3) 외부 API         (Claude / Gemini / OpenAI)
```
- 1 → 모델 선택(qwen2.5:3b 권장 / exaone3.5:2.4b / gemma2:9b) → 설치 중 `ollama pull`
- 2 → `AI_BASE_URL`, `AI_MODEL`(+선택 키)
- 3 → 벤더 택 → `AI_API_KEY`·`AI_MODEL` → **⚠️ "요약 신호만 외부로 전송, 원본 로그는 안 나감. 계속?" 확인**
- 기본값: `ollama / qwen2.5:3b`
- 불변식: **어떤 프로바이더든 입력은 signals_json(집계 신호)뿐, 원본 로그 아님.**

### STEP 2 · 관리 화면 포트
```
관리 화면 포트 [8099]:
```

### STEP 3 · 데이터 소스
```
분석할 로그를 어디서 읽을까요?
  1) DB 직접 접근
  2) MCP 커넥터로 연결   [확장 예정]
```
- 1 → host/port/dbname/user/password + 연결 테스트
- 2 → MCP_URL(+token). MVP: 항목 노출 + "확장 예정" 안내

### STEP 4 · 분석 설정
```
분석 기간(렌즈 기본값) [7일] : 1)1일 2)7일 3)30일
분석 주기            [매일] : 1)매일 새벽 3시  2)수동만
```

## 4. 설정 요약·확인
```
─ 확인 ─────────────────────
 AI      : 로컬 Ollama · qwen2.5:3b
 포트    : 8099
 데이터  : DB 직접 · pfdb@127.0.0.1
 분석    : 기간 7일 · 매일 새벽 3시
────────────────────────────
이대로 설치할까요? (Y/n)
```

## 5. 마법사가 실행하는 것
1. `.env` 작성
2. 로컬 AI면 `ollama pull <model>` (진행률)
3. `docker compose up -d`
4. 헬스체크 — 앱/DB/AI 기동 + 관리화면 200 대기
5. (선택) 첫 분석 1회 트리거

## 6. 완료 안내
```
✓ OWL 설치 완료
  관리 화면 : http://<서버IP>:8099
  분석 대상 : 연결된 로그 자동 감지 (유출 + 개인정보 오남용)
  분석 주기 : 매일 새벽 3시 (지금 보려면 "지금 분석")
  데이터    : 서버 밖으로 나가지 않습니다.
```

## 7. 재실행·설정 변경
- `./install.sh` 재실행 = 기존 `.env` 읽어 기본값 채움(idempotent). 엔터=유지.

## 8. 실패 처리 (경량)
- Docker 없음 → 설치 안내 후 중단
- DB 연결 실패 → 재입력 or 건너뛰기
- 모델 pull 실패 → 재시도 / 소형 모델 대체 제안
- 포트 충돌 → 다른 포트 제안

---

## 9. 분석 대상 자동 감지 (STEP4 제품선택을 대체하는 핵심)

### 왜 제품 선택 질문이 없나
- PCFILTER는 고객마다 스키마가 같음(고정) → 추측 불필요.
- DLP + 개인정보는 "민감정보 오남용" 한 덩어리 → 굳이 고르게 할 이유 없음.
- 묶어서 보면 **한 사람 기준 교차 신호**가 살아나 분석이 더 강함.

### 도메인 카탈로그 (우리가 작성하는 정본)
```
dlp     → [log_dlp_fileattach_t, media, website, sharedfolder, chatgpt] + exfil recipe   [동작]
privacy → [log_privacy_protect_t, search(+detail), watch]              + 오남용 recipe    [확장 1순위]
asset   → 현재 제외 (테이블 미확인 · MVP 범위 밖)
```

### 자동 감지 = "있는 모듈 켜기"
런타임에 "카탈로그의 테이블이 이 고객 DB에 존재+데이터 있나?" 확인 → 있으면 활성.
= 고객이 실제 쓰는 모듈을 감지 (없는 것 추측 아님).

### 확장 2갈래
- **A. PCFILTER 내부 모듈**: 카탈로그에 (테이블+recipe) 추가 = 설계 작업.
  - 개인정보: 테이블 확인됨, recipe(무엇이 오남용인가)만 설계하면 됨.
- **B. 타사/외부 제품**: 스키마 모름 → MCP·공통 API로 정규화 데이터 받음(OWL은 상대 테이블 몰라도 됨).

---

## 10. MVP 완전동작 범위
```
로컬 Ollama + DB 직접 + (유출 + 개인정보 자동감지) + 기간/주기
나머지(사내/외부 LLM, MCP, 개인정보 recipe, 자산)는 노출 or 확장 예정
```

## 확장성이 "보이는" 지점 (설계 의도)
- STEP 1(AI 3종)·STEP 3(DB/MCP)의 선택지 = 유연함 증명
- 완료 화면 "분석 대상: 유출 + 개인정보 오남용 · 자산 등 확장 예정"
- 재실행 idempotent = 운영 중 변경 용이
