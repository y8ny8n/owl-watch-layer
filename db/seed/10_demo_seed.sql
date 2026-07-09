-- ============================================================================
-- 온파일럿 데모 시드 데이터 (가명)
-- ----------------------------------------------------------------------------
-- 00_demo_schema.sql 다음에 자동 적용됨 (db/00_init.sh 참조). 계약 스키마 그대로 사용,
-- 신규 컬럼 없음.
--
-- 이 시드가 심어놓은 신호 요약 (기술설계 §3.1 신호코드 기준):
--
-- [유출자A] 김철수 (kim / 연구소, group_code=1) — 채널교차 시나리오
--   media_t     : file_name 설계도.dwg → dst_file_name 메모.txt (S1 확장자바꿔치기)
--                 zip_filelist 존재(S2), total_pri_cnt=120(S4), 야간 23시대(S6)
--   fileattach_t: category=7(클라우드, S5 비공식경로), is_block=false, 야간(S6)
--   chatgpt_t   : block_type=0, pri_cnt=5(S8 기밀 붙여넣기)
--   → media+fileattach+chatgpt = distinct_channels 3 (S7 채널교차, 30점)
--   → 예상 합산 S1(25)+S2(15)+S4(15)+S5(15)+S6(10)+S7(30)+S8(20) = 100(클립) → high
--
-- [유출자B] 이영희 (lee / 마케팅, group_code=2) — USB 단독 회피 시나리오 (media_t 3건)
--   3건 모두 is_block=false, 확장자바꿔치기(S1) + zip_filelist(S2) + total_pri_cnt 높음(S4)
--   2건은 hash_extract_fail_reason 존재(S3), 야간/주말 각 1건 이상(S6)
--   → 단일 채널(media)이지만 S1+S2+S3+S4+S6 겹침으로 임계(35) 초과 → high
--
-- [정상 사용자 6명] 박민수/최지훈/정수진/강동원/한가은/오세훈
--   각 1건, 채널 1개씩(5채널에 고르게 분산), 주간, 회피신호 없음, is_block/block_type 정상허용값
--   → 신호 0~1개만 fire, 임계(35) 미만 → 리포트 미적재 대상
--
-- [policy_t 베이스라인] §6 정책반영 UPDATE 대상 (media 부모정책 pid=0 + media_separate 개별정책 pid=1)
-- ============================================================================

-- 1) 라이선스 ------------------------------------------------------------------
INSERT INTO license_t (license_code, company_name)
VALUES ('DEMO0001', '경윤스타크데모');

-- 2) 조직 ----------------------------------------------------------------------
INSERT INTO group_t (group_code, license_code, group_name) VALUES
    (1, 'DEMO0001', '연구소'),
    (2, 'DEMO0001', '마케팅'),
    (3, 'DEMO0001', '영업'),
    (4, 'DEMO0001', '경영지원');

-- 3) 에이전트 (시나리오 인물 2명 + 정상 사용자 6명) ------------------------------
INSERT INTO agent_t (license_code, group_code, user_info) VALUES
    ('DEMO0001', 1, '{"user_id":"kim","user_name":"김철수"}'),   -- 유출자A
    ('DEMO0001', 2, '{"user_id":"lee","user_name":"이영희"}'),   -- 유출자B
    ('DEMO0001', 1, '{"user_id":"park","user_name":"박민수"}'),  -- 정상
    ('DEMO0001', 1, '{"user_id":"choi","user_name":"최지훈"}'),  -- 정상
    ('DEMO0001', 2, '{"user_id":"jung","user_name":"정수진"}'),  -- 정상
    ('DEMO0001', 3, '{"user_id":"kang","user_name":"강동원"}'),  -- 정상
    ('DEMO0001', 3, '{"user_id":"han","user_name":"한가은"}'),   -- 정상
    ('DEMO0001', 4, '{"user_id":"oh","user_name":"오세훈"}');    -- 정상

-- ============================================================================
-- 4) 유출자A 김철수 — 채널교차 (media + fileattach + chatgpt, 같은 주)
-- ============================================================================

-- media: 확장자 바꿔치기 + 압축은닉 + 대량 개인정보 + 야간(23시대, 2일 전)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kim'),
    date_trunc('day', now()) - interval '2 days' + interval '23 hours 10 minutes',
    '{"is_block":"false","media_type":"file","file_name":"설계도.dwg","dst_file_name":"메모.txt","file_size":15400000,"zip_filelist":"추가파일1.txt,추가파일2.txt","total_pri_cnt":120,"device_type":"USB"}'::jsonb,
    '{"id":"kim","name":"김철수","path":"C:\\PCFILTER\\Agent","com_name":"RND-KIM01"}'::jsonb
);

-- fileattach: 클라우드(비공식경로) 업로드 허용 + 야간(3일 전)
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kim'),
    date_trunc('day', now()) - interval '3 days' + interval '22 hours 40 minutes',
    '{"is_block":"false","category":7,"file_name":"설계자료.pdf","dst_file_name":"설계자료.pdf","file_size":8200000,"browser_url":"https://drive.google.com/upload"}'::jsonb,
    '{"id":"kim","name":"김철수","path":"C:\\PCFILTER\\Agent","com_name":"RND-KIM01"}'::jsonb
);

-- chatgpt: 허용 + 기밀 문구 붙여넣기 (1일 전 낮)
INSERT INTO log_dlp_chatgpt_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kim'),
    date_trunc('day', now()) - interval '1 days' + interval '15 hours 20 minutes',
    '{"block_type":0,"type":"chatgpt","url":"https://chat.openai.com/","payload":"우리 회사 신제품 설계 스펙인데 요약해줘: 배터리 용량 5000mAh, 방열구조 특허출원 중, 양산 원가 12만원","pri_cnt":5}'::jsonb,
    '{"id":"kim","name":"김철수","path":"C:\\PCFILTER\\Agent","com_name":"RND-KIM01"}'::jsonb
);

-- [지속성 S9] 김철수 과거 반복 반출 — 2주 전 / 3주 전 (확장자바꿔치기+야간)
--   → 이번 주 포함 서로 다른 3주에 걸쳐 의심 반출 = "지속 반복 탐지(3주)" 성립
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES
(
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kim'),
    date_trunc('day', now()) - interval '10 days' + interval '23 hours 30 minutes',
    '{"is_block":"false","media_type":"file","file_name":"회로도_v2.dwg","dst_file_name":"사진.png","file_size":9200000,"zip_filelist":"회로도_사본.zip","total_pri_cnt":40,"device_type":"USB"}'::jsonb,
    '{"id":"kim","name":"김철수","path":"C:\\PCFILTER\\Agent","com_name":"RND-KIM01"}'::jsonb
),
(
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kim'),
    date_trunc('day', now()) - interval '18 days' + interval '22 hours 50 minutes',
    '{"is_block":"false","media_type":"file","file_name":"설계도_v1.dwg","dst_file_name":"readme.txt","file_size":8800000,"total_pri_cnt":55,"device_type":"USB"}'::jsonb,
    '{"id":"kim","name":"김철수","path":"C:\\PCFILTER\\Agent","com_name":"RND-KIM01"}'::jsonb
);

-- ============================================================================
-- 5) 유출자B 이영희 — USB 단독 회피 (media_t 3건, 같은 주)
-- ============================================================================

-- B1: 확장자 바꿔치기 + 압축은닉 + 암호화회피 + 대량개인정보 + 야간(2일 전 23:40)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='lee'),
    date_trunc('day', now()) - interval '2 days' + interval '23 hours 40 minutes',
    '{"is_block":"false","media_type":"file","file_name":"급여명세서.xlsx","dst_file_name":"배경화면.jpg","file_size":9800000,"zip_filelist":"급여명세서_사본.zip","hash_extract_fail_reason":"password_protected_archive","total_pri_cnt":95,"device_type":"USB"}'::jsonb,
    '{"id":"lee","name":"이영희","path":"C:\\PCFILTER\\Agent","com_name":"MKT-LEE02"}'::jsonb
);

-- B2: 확장자 바꿔치기 + 압축은닉 + 암호화회피 + 대량개인정보 + 주말 낮(최근 토요일 14:00)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='lee'),
    date_trunc('day', now()) - make_interval(days => ((extract(dow from now())::int + 1) % 7)) + interval '14 hours',
    '{"is_block":"false","media_type":"file","file_name":"고객DB.xlsx","dst_file_name":"favicon.ico","file_size":21000000,"zip_filelist":"고객DB_백업.zip","hash_extract_fail_reason":"encrypted_zip","total_pri_cnt":110,"device_type":"USB"}'::jsonb,
    '{"id":"lee","name":"이영희","path":"C:\\PCFILTER\\Agent","com_name":"MKT-LEE02"}'::jsonb
);

-- B3: 확장자 바꿔치기 + 압축은닉 + 개인정보 반출 + 야간(4일 전 02:15)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='lee'),
    date_trunc('day', now()) - interval '4 days' + interval '2 hours 15 minutes',
    '{"is_block":"false","media_type":"file","file_name":"마케팅전략.pptx","dst_file_name":"temp.dat","file_size":6400000,"zip_filelist":"전략자료.zip","total_pri_cnt":60,"device_type":"USB"}'::jsonb,
    '{"id":"lee","name":"이영희","path":"C:\\PCFILTER\\Agent","com_name":"MKT-LEE02"}'::jsonb
);

-- ============================================================================
-- 6) 정상 사용자 6명 — 채널당 1건, 주간, 회피신호 없음 (임계 미만)
-- ============================================================================

-- 박민수 (연구소): media, 정상 업무자료 이동, 주간(1일 전 14:00)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='park'),
    date_trunc('day', now()) - interval '1 days' + interval '14 hours',
    '{"is_block":"false","media_type":"file","file_name":"회의자료.pptx","dst_file_name":"회의자료.pptx","file_size":1200000,"total_pri_cnt":0,"device_type":"USB"}'::jsonb,
    '{"id":"park","name":"박민수","path":"C:\\PCFILTER\\Agent","com_name":"RND-PARK03"}'::jsonb
);

-- 최지훈 (연구소): fileattach, 메일(category=6) 정상 발송, 주간(1일 전 11:00)
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='choi'),
    date_trunc('day', now()) - interval '1 days' + interval '11 hours',
    '{"is_block":"false","category":6,"file_name":"주간보고.docx","dst_file_name":"주간보고.docx","file_size":500000}'::jsonb,
    '{"id":"choi","name":"최지훈","path":"C:\\PCFILTER\\Agent","com_name":"RND-CHOI04"}'::jsonb
);

-- 정수진 (마케팅): website, 웹메일(category=1) 허용, 주간(2일 전 10:30)
INSERT INTO log_dlp_website_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='jung'),
    date_trunc('day', now()) - interval '2 days' + interval '10 hours 30 minutes',
    '{"block_type":1,"category":1,"sub_url":"mail.company.com/send","host_url":"mail.company.com","checked_type":"normal"}'::jsonb,
    '{"id":"jung","name":"정수진","path":"C:\\PCFILTER\\Agent","com_name":"MKT-JUNG05"}'::jsonb
);

-- 강동원 (영업): sharedfolder, 공유폴더 정상 접근, 주간(1일 전 09:20)
INSERT INTO log_dlp_sharedfolder_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kang'),
    date_trunc('day', now()) - interval '1 days' + interval '9 hours 20 minutes',
    '{"block_type":0,"category_type":0,"file_name":"견적서.xlsx","file_path":"\\\\FILESERVER\\sales\\견적서.xlsx","current_user":"kang"}'::jsonb,
    '{"id":"kang","name":"강동원","path":"C:\\PCFILTER\\Agent","com_name":"SALES-KANG06"}'::jsonb
);

-- 한가은 (영업): chatgpt, 개인정보 없는 일반 질의 허용, 주간(2일 전 16:00)
INSERT INTO log_dlp_chatgpt_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='han'),
    date_trunc('day', now()) - interval '2 days' + interval '16 hours',
    '{"block_type":0,"type":"chatgpt","url":"https://chat.openai.com/","payload":"엑셀 함수 VLOOKUP 사용법 알려줘","pri_cnt":0}'::jsonb,
    '{"id":"han","name":"한가은","path":"C:\\PCFILTER\\Agent","com_name":"SALES-HAN07"}'::jsonb
);

-- 오세훈 (경영지원): fileattach, 브라우저(category=100) 정상 업로드, 주간(3일 전 13:40)
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json)
VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='oh'),
    date_trunc('day', now()) - interval '3 days' + interval '13 hours 40 minutes',
    '{"is_block":"false","category":100,"file_name":"품의서.pdf","dst_file_name":"품의서.pdf","file_size":300000}'::jsonb,
    '{"id":"oh","name":"오세훈","path":"C:\\PCFILTER\\Agent","com_name":"ADM-OH08"}'::jsonb
);

-- ============================================================================
-- 7) policy_t 베이스라인 (§6 정책반영 UPDATE 대상)
-- ============================================================================

-- 부모 매체정책 (pid=0)
INSERT INTO policy_t (license_code, service_type, policy_type, pid, pvn, policy_json)
VALUES ('DEMO0001', 'dlp', 'media', 0, 0, '{"name":"기본 매체제어정책","use":true}'::jsonb);

-- 개별정책 (media_separate, pid=1) — 온파일럿 승인 시 policy_json/pvn UPDATE 대상
INSERT INTO policy_t (license_code, service_type, policy_type, pid, pvn, policy_json)
VALUES ('DEMO0001', 'dlp', 'media_separate', 1, 0, '{}'::jsonb);
