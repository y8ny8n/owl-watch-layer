# 온파일럿 (OnPilot)

> PCFILTER 서버에 얹는 온프레미스 로컬 AI. 이미 허용으로 통과된 로그(회색지대)를
> 채널 교차·회피정황으로 채점해, 봐줄 만한 후보를 사람 말 리포트로 올리고,
> 관리자가 승인하면 기존 정책엔진이 실제로 막는다.
>
> **모토: 데이터가 제대로 활용되어야 가치있다.** / 팀 경윤스타크

- 설계 정본: [`../온파일럿_데모_기술설계.md`](../온파일럿_데모_기술설계.md)
- 세션별 작업 지도: [`SESSION_GUIDE.md`](SESSION_GUIDE.md)

## 빠른 시작

도커 데모는 **`.env` 없이도** 자체완결로 뜬다(compose 가 pfdb/ollama 호스트와 DEMO0001 시드,
모델 태그를 직접 지정). 시드 로그는 `now()` 상대시간이라 **기동할 때마다 최신 7일 창 안**에 들어온다.

```bash
docker compose up --build     # onpilot(8080) + ollama(11434) + pfdb(5432)

# 부팅 확인
curl http://localhost:8080/health      # {"status":"ok"}

# Gemma 모델 사전 다운로드 (최초 1회) — compose 기본 태그와 일치
docker exec -it onpilot-ollama ollama pull gemma2:2b
```

첫 접속(`http://localhost:8080`)은 **설치 마법사**로 시작한다. AI엔진·데이터소스·민감도를
고르고 완료하면 메인 화면으로 넘어간다. 이후 **[지금 분석]** 을 누르면 시드에서 유출 후보를
채점해 피드에 올린다(김철수=채널교차 high, 이영희=USB 단독 high).

> **모델 품질을 높이려면(gemma2:9b)**: 컨테이너 CPU 추론은 9b 가 느리다. 두 가지 방법 —
> ① 컨테이너에서 `ollama pull gemma2:9b` 후 마법사에서 9b 선택(느림, 폴백 방지용 타임아웃 120s).
> ② 맥 네이티브 ollama(GPU, 이미 9b 보유)를 재사용: `docker-compose.override.yml` 을 만들어
> onpilot 의 `OLLAMA_URL` 을 `http://host.docker.internal:11434` 로 지정(빠름, 로컬 전용·gitignore됨).

> **마법사를 다시 보고 싶으면**: `rm app/data/owl_setup.json` 후 재접속(이 파일은 런타임 마커라 gitignore).

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
