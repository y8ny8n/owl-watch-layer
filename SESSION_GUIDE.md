# 세션별 작업 지도 (SESSION_GUIDE)

여러 세션이 각자 한 조각씩 병렬로 물고 간다. 각 세션은 이 파일 + 설계문서(§)만 읽으면
독립적으로 작업 가능. **stub 에는 `raise NotImplementedError(...설계문서 §...)` 로 착지점이 박혀있다.**

설계 정본: `../온파일럿_데모_기술설계.md`

## 의존 순서 (권장)

```
S0 준비 ──┬─→ S1 시드데이터 ──→ S2 신호SQL ──→ S3 스코어링 ──┐
          │                                                  ├─→ S5 분석루프 ──→ S7 UI
          └─→ S4 Ollama ─────────────────────────────────────┘
                                    S6 정책반영 ──(S8 UI에서 호출)
```
S2·S3·S4 는 서로 독립이라 **병렬 세션 가능**. S5 는 S2/S3/S4 를 엮음. S6 은 독립. S7 은 마지막.

## 세션 목록

| ID | 세션 주제 | 채울 파일 | 설계 § | 완료 기준 |
|----|----------|----------|-------|----------|
| S0 | 환경 준비 | (실행만) `.env`, `docker compose up`, `ollama pull` | §7-1 | `/health` ok + Gemma pull 완료 |
| S1a | 데모 스키마(계약) | `db/schema/00_demo_schema.sql` (완료됨 — 필요 테이블만 jsonb) | §2 | 5채널+policy 테이블 생성 |
| S1b | 가명 시드데이터 | `db/seed/*.sql` | §7-2 | 채널교차 유출자1+USB유출자1+정상 다수, 계약 스키마 기준 |
| S2 | 신호 SQL 레시피 | `app/recipes/exfil.py` | §3.1, §3.3 | 시드에서 유출자만 fired, 정상 안 걸림 |
| S3 | 스코어링 | `app/scoring.py` (`build_signals_json`) | §2, §3.2 | 단위테스트: 단일신호 high 불가 검증 |
| S4 | Ollama 호출 | `app/ollama_client.py` (`summarize`,`extract_slots`) | §4 | 한국어 서사 정상 + 슬롯 JSON 파싱 |
| S5 | 분석 루프 | `app/analyzer.py` | §1.2, §7-4 | 실행 시 ai_analysis_result_t 적재됨 |
| S6 | 정책 반영 | `app/policy.py` | §6 | policy_t/policy_sub_t + pvn+1 확인 |
| S7 | UI | `app/web/`, `app/routes/reports.py` | §5-1,2 | 피드→상세(겹침 시각화) 브라우저 확인 |
| S8 | 챗→정책 동선 | `app/routes/chat.py`,`policy.py` | §5-3,4, §4.2 | 자연어→미리보기→승인→반영 E2E |
| S9 | 발표 안정성 | 리포트 미리굽기 + 캐싱 + 오프라인 리허설 | §7-7 | 랜선 뽑고 전 동선 재생 |

## 각 세션 시작 문구 예시
> "온파일럿 S2(신호 SQL) 작업할게. `SESSION_GUIDE.md`랑 설계문서 §3.3 읽고 `app/recipes/exfil.py` 채워줘."

## 공통 규칙
- 안전벨트 준수: 탐지=SQL / AI=요약만 / 최종 정책 JSON은 코드 조립.
- 새 신호는 `recipes/base.py` REGISTRY 에 등록(단일 정본).
- 미결 사항은 설계문서 §9 참조 (Gemma 모델 확정, media_pid 실제값, setAgentCashModify 등).
