-- ============================================================================
-- 온파일럿 데모 전용 최소 스키마 (계약서 contract)
-- ----------------------------------------------------------------------------
-- 왜 PCFILTER V3.0.sql 을 안 쓰나:
--   그 파일은 log_json 을 xml 타입으로 선언(구버전) → 실운영은 dbpatcher 로 jsonb 전환.
--   그대로 로드하면 우리 레시피의 jsonb 연산자(->>)가 전부 깨진다.
--   그래서 데모에 필요한 테이블만, jsonb 로 정확히 재정의한다.
-- 이 파일이 시드(S1b)·레시피(S2)·정책(S6)이 공유하는 단일 계약이다. 컬럼/키를 여기 기준으로.
-- ============================================================================

-- 라이선스(테넌트) --------------------------------------------------------------
CREATE TABLE license_t (
    license_code varchar(8) PRIMARY KEY,
    company_name varchar
);

-- 조직 ------------------------------------------------------------------------
CREATE TABLE group_t (
    group_code   int PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    group_name   varchar,
    parent_code  int
);

-- 에이전트(사용자 단말) --------------------------------------------------------
-- user_info 예: {"user_id":"kim","user_name":"김철수"}
CREATE TABLE agent_t (
    agent_id     bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    group_code   int,
    user_info    jsonb
);

-- 정책(§6 재사용 대상) ---------------------------------------------------------
-- policy_json 은 media_separate 개별정책 본문. pvn 은 정책버전(수정마다 +1).
CREATE TABLE policy_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    service_type varchar,                      -- 'dlp'
    policy_type  varchar NOT NULL,             -- 'media' | 'media_separate' ...
    pid          int DEFAULT 0,
    pvn          bigint DEFAULT 0,
    policy_json  jsonb,
    reg_json     jsonb,
    modify_json  jsonb
);

CREATE TABLE policy_sub_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL,
    pid          int NOT NULL,
    service_type varchar,
    policy_type  varchar NOT NULL,             -- 'media_separate'
    sub_name     varchar,                      -- 'target_user' | 'target_group' | 'target_user_id'
    sub_text     text[],                       -- 대상 배열 (target_user = agent_id 문자열배열)
    sub_json     jsonb
);

-- ============================================================================
-- DLP 로그 5채널 — 공통 형태: log_json(jsonb) 안에 채널별 필드.
-- agent_json = 로그 시점 사용자 스냅샷 {"id","name","path","com_name"}
-- ----------------------------------------------------------------------------
-- 허용(회색지대) 판별 규칙 (채널별로 다름! 스카우트 확인):
--   media/fileattach : log_json->>'is_block' = 'false'
--   website          : (log_json->>'block_type')::int = 1
--   sharedfolder     : (log_json->>'block_type')::int = 0
--   chatgpt          : (log_json->>'block_type')::int = 0
--   (capture 는 전량 차단이라 데모 제외)
-- ============================================================================

-- USB 외부매체 ----------------------------------------------------------------
-- log_json 키: is_block, media_type('device'|'file'), file_name, dst_file_name,
--             file_size, zip_filelist, hash_extract_fail_reason, total_pri_cnt, device_type
CREATE TABLE log_dlp_media_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    agent_id     bigint NOT NULL REFERENCES agent_t(agent_id) ON DELETE CASCADE,
    log_type     varchar NOT NULL DEFAULT 'dlp_media_log',
    log_time     timestamp with time zone,
    log_json     jsonb,
    agent_json   jsonb
);

-- 메일/파일첨부 ---------------------------------------------------------------
-- log_json 키: is_block, category(1웹하드/2메신저/6메일/7클라우드/10원격/100브라우저...),
--             file_name, dst_file_name, file_size, browser_url, zip_filelist,
--             hash_extract_fail_reason, total_pri_cnt, is_approve
CREATE TABLE log_dlp_fileattach_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    agent_id     bigint NOT NULL REFERENCES agent_t(agent_id) ON DELETE CASCADE,
    log_type     varchar NOT NULL DEFAULT 'dlp_fileattach_log',
    log_time     timestamp with time zone,
    log_json     jsonb,
    agent_json   jsonb
);

-- 웹 업로드 -------------------------------------------------------------------
-- log_json 키: block_type(1허용경고/2차단), category(1웹메일/8SNS/9웹하드/11생성형AI...),
--             sub_url, host_url, checked_type
CREATE TABLE log_dlp_website_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    agent_id     bigint NOT NULL REFERENCES agent_t(agent_id) ON DELETE CASCADE,
    log_type     varchar NOT NULL DEFAULT 'dlp_website_log',
    log_time     timestamp with time zone,
    log_json     jsonb,
    agent_json   jsonb
);

-- 공유폴더 -------------------------------------------------------------------
-- log_json 키: block_type(0허용/1차단), category_type(0공유폴더/1네트워크드라이브/2SMB),
--             file_name, file_path, current_user
CREATE TABLE log_dlp_sharedfolder_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    agent_id     bigint NOT NULL REFERENCES agent_t(agent_id) ON DELETE CASCADE,
    log_type     varchar NOT NULL DEFAULT 'dlp_sharedfolder_log',
    log_time     timestamp with time zone,
    log_json     jsonb,
    agent_json   jsonb
);

-- 생성형 AI -------------------------------------------------------------------
-- log_json 키: block_type(0허용/2차단), type(서비스코드), url, payload(프롬프트원문), pri_cnt
CREATE TABLE log_dlp_chatgpt_t (
    pno          bigserial PRIMARY KEY,
    license_code varchar(8) NOT NULL REFERENCES license_t(license_code) ON DELETE CASCADE,
    agent_id     bigint NOT NULL REFERENCES agent_t(agent_id) ON DELETE CASCADE,
    log_type     varchar NOT NULL DEFAULT 'dlp_chatgpt_log',
    log_time     timestamp with time zone,
    log_json     jsonb,
    agent_json   jsonb
);

-- 조회 최적화 (설계문서 §1.1 최적화 레버) --------------------------------------
CREATE INDEX idx_media_lic_time        ON log_dlp_media_t(license_code, log_time);
CREATE INDEX idx_fileattach_lic_time   ON log_dlp_fileattach_t(license_code, log_time);
CREATE INDEX idx_website_lic_time      ON log_dlp_website_t(license_code, log_time);
CREATE INDEX idx_sharedfolder_lic_time ON log_dlp_sharedfolder_t(license_code, log_time);
CREATE INDEX idx_chatgpt_lic_time      ON log_dlp_chatgpt_t(license_code, log_time);
