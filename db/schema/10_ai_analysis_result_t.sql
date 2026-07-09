-- 온파일럿 분석 결과(리포트) 테이블 — 신규 1개.
-- 설계문서 §2 참조. PCFILTER 컨벤션(bigserial pno / license_code / timestamptz / jsonb) 준수.
--
-- 선행 조건: 00_demo_schema.sql 이 먼저 적재되어 license_t 가 존재해야 FK가 성립한다.
--   (파일명 정렬상 00_ → 10_ 순서로 자동 적용됨)

CREATE TABLE IF NOT EXISTS ai_analysis_result_t
(
    pno                   bigserial       NOT NULL,
    license_code          varchar(8)      NOT NULL,
    analysis_type         varchar         NOT NULL,          -- 'exfil_candidate' (확장: 'server_health' 등)
    target_agent_id       bigint,                            -- 리포트 대상 에이전트 (nullable)
    target_user_id        varchar,                           -- 표시용 스냅샷 (agent_json->>'id')
    target_user_name      varchar,                           -- 표시용 스냅샷 (agent_json->>'name')
    period_start          timestamp with time zone,          -- 분석 창 시작
    period_end            timestamp with time zone,          -- 분석 창 끝
    risk_score            int             DEFAULT 0,         -- 0~100
    severity              varchar,                           -- 'low' | 'mid' | 'high'
    signals_json          jsonb,                             -- 걸린 신호 + 증거 (설계문서 §2)
    summary_text          text,                              -- Ollama 생성 사람 말 서사
    suggested_action_json jsonb,                             -- 제안 정책 슬롯(있으면), nullable
    status                varchar         DEFAULT 'new',     -- 'new'|'reviewed'|'actioned'|'dismissed'
    analysis_window       varchar(8)      DEFAULT '7d',      -- '1d'|'7d'|'30d' (일/주/월 기간 렌즈)
    model_name            varchar,                           -- 'gemma:...' (추적/재현용)
    reg_time              timestamp with time zone DEFAULT now(),
    PRIMARY KEY (pno),
    CONSTRAINT ai_analysis_result_t_license_fkey
        FOREIGN KEY (license_code) REFERENCES license_t(license_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_result_license_time
    ON ai_analysis_result_t(license_code, reg_time DESC);
