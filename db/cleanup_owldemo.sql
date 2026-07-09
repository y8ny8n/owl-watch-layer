-- OWL 테스트 데이터 정리 (oa233262 실 라이선스 — 배치/태그/pid 기준, 실데이터 보존)
-- 에이전트+로그는 gen_agents.py --cleanup owl-demo 로 지우는 게 정석(FK cascade).
-- 이 SQL은 정책/리포트/잔여로그 마무리용.
DELETE FROM policy_sub_t         WHERE license_code='oa233262' AND pid=9001;
DELETE FROM policy_t             WHERE license_code='oa233262' AND pid=9001;
DELETE FROM ai_analysis_result_t WHERE license_code='oa233262';
DELETE FROM log_dlp_media_t        WHERE license_code='oa233262' AND log_json->>'_td'='owl-demo';
DELETE FROM log_dlp_fileattach_t   WHERE license_code='oa233262' AND log_json->>'_td'='owl-demo';
DELETE FROM log_dlp_website_t      WHERE license_code='oa233262' AND log_json->>'_td'='owl-demo';
DELETE FROM log_dlp_sharedfolder_t WHERE license_code='oa233262' AND log_json->>'_td'='owl-demo';
DELETE FROM log_dlp_chatgpt_t      WHERE license_code='oa233262' AND log_json->>'_td'='owl-demo';
