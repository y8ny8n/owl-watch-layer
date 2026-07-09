# 온파일럿 (OnPilot)

> PCFILTER 서버에 얹는 온프레미스 로컬 AI. 이미 허용으로 통과된 로그(회색지대)를
> 채널 교차·회피정황으로 채점해, 봐줄 만한 후보를 사람 말 리포트로 올리고,
> 관리자가 승인하면 기존 정책엔진이 실제로 막는다.
>
> **모토: 데이터가 제대로 활용되어야 가치있다.** / 팀 경윤스타크

- 설계 정본: [`../온파일럿_데모_기술설계.md`](../온파일럿_데모_기술설계.md)
- 세션별 작업 지도: [`SESSION_GUIDE.md`](SESSION_GUIDE.md)

## 빠른 시작

```bash
cp .env.example .env          # 값 채우기 (DEMO_LICENSE_CODE 등)
docker compose up --build     # onpilot(8080) + ollama(11434) + pfdb(5432)

# 부팅 확인
curl http://localhost:8080/health      # {"status":"ok"}

# Gemma 모델 사전 다운로드 (최초 1회, 망분리 반입 전 필수)
docker exec -it onpilot-ollama ollama pull gemma:2b
```

## 구조

```
onpilot/
├─ docker-compose.yml     컨테이너 3종 (onpilot/ollama/pfdb)
├─ .env.example           설정 템플릿
├─ db/
│  ├─ 00_init.sh          pfdb 최초기동 시 schema→seed 순 적재
│  ├─ schema/             10_ai_analysis_result_t.sql (+ PCFILTER 기본스키마 넣을 것)
│  └─ seed/               가명 시드 데이터 [세션]
└─ app/                   FastAPI
   ├─ main.py             진입점 (라우터 엮기 + /health)
   ├─ config.py, db.py    설정 / pfdb 연결 (완성)
   ├─ recipes/            신호 SQL 레시피 [세션]
   ├─ scoring.py          점수/심각도 [세션]
   ├─ analyzer.py         분석 루프 [세션]
   ├─ ollama_client.py    Gemma 호출 2역할 [세션]
   ├─ policy.py           정책 반영(media_separate 재사용) [세션]
   ├─ routes/             reports/chat/policy API [세션]
   └─ web/                UI 템플릿/정적 [세션]
```

`[세션]` = 아직 stub. `SESSION_GUIDE.md` 의 순서대로 각 세션이 하나씩 채운다.

## 안전벨트 (절대 안 넘김)
- 탐지 = SQL / AI = 요약·설명만 / 실행 = 검증된 PCFILTER 엔진 / 방아쇠 = 사람
- 최종 정책 JSON 은 코드가 조립 (AI 는 슬롯만 추출) → 환각 리스크 0
- 데이터 외부 유출 0 (로컬 Ollama)
