-- ============================================================================
-- 온파일럿 다양성 보강 시드 (11_) — 원본 10_demo_seed.sql 위에 얹는 추가분.
--   생성: gen_diverse_seed.py (단일 진실원천, 스코어 분포 검증 완료).
--   원본 미수정. license/그룹1~4/기존 8명은 10_ 이 이미 생성. 여기선 그룹5~6 +
--   신규 18명 + 기존 박민수 로그 1건(관심등급 승격)만 추가한다.
--   시간은 KST(Asia/Seoul) 명시 계산 → 서버 타임존 무관하게 야간/주말 판정 결정적.
--   기대 분포(kim/lee 포함): high 7 · mid 4 · watch 3 · low(리포트X) 12.
-- ============================================================================

-- 1) 추가 조직 ----------------------------------------------------------------
INSERT INTO group_t (group_code, license_code, group_name) VALUES
    (5, 'DEMO0001', '개발'),
    (6, 'DEMO0001', '인사');

-- 2) 신규 에이전트 (기존 박민수 제외 18명) -----------------------------------
INSERT INTO agent_t (license_code, group_code, user_info) VALUES
    ('DEMO0001', 5, '{"user_id": "shin", "user_name": "신동현"}'),
    ('DEMO0001', 2, '{"user_id": "hanj", "user_name": "한지민"}'),
    ('DEMO0001', 5, '{"user_id": "ohj", "user_name": "오지은"}'),
    ('DEMO0001', 3, '{"user_id": "moon", "user_name": "문상철"}'),
    ('DEMO0001', 6, '{"user_id": "baesuji", "user_name": "배수지"}'),
    ('DEMO0001', 6, '{"user_id": "cho", "user_name": "조현우"}'),
    ('DEMO0001', 2, '{"user_id": "yoon", "user_name": "윤서연"}'),
    ('DEMO0001', 3, '{"user_id": "lim", "user_name": "임재현"}'),
    ('DEMO0001', 5, '{"user_id": "kwak", "user_name": "곽태영"}'),
    ('DEMO0001', 6, '{"user_id": "seo", "user_name": "서지훈"}'),
    ('DEMO0001', 3, '{"user_id": "nam", "user_name": "남기훈"}'),
    ('DEMO0001', 6, '{"user_id": "yoo", "user_name": "유하늘"}'),
    ('DEMO0001', 4, '{"user_id": "baewj", "user_name": "배우진"}'),
    ('DEMO0001', 5, '{"user_id": "kangy", "user_name": "강예린"}'),
    ('DEMO0001', 2, '{"user_id": "jungw", "user_name": "정우성"}'),
    ('DEMO0001', 6, '{"user_id": "sonye", "user_name": "손예진"}'),
    ('DEMO0001', 5, '{"user_id": "leedh", "user_name": "이도현"}'),
    ('DEMO0001', 3, '{"user_id": "ryu", "user_name": "류준열"}');

-- 3) 로그 -------------------------------------------------------------------
-- 신동현 / shin
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='shin'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - make_interval(days => ((extract(dow from now() AT TIME ZONE 'Asia/Seoul')::int + 1) % 7))
        + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "소스코드.zip", "dst_file_name": "사진모음.zip", "file_size": 1000000, "total_pri_cnt": 130, "device_type": "USB", "zip_filelist": "repo_full.zip"}'::jsonb,
    '{"id": "shin", "name": "신동현", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-SHIN"}'::jsonb
);
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='shin'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - make_interval(days => ((extract(dow from now() AT TIME ZONE 'Asia/Seoul')::int + 1) % 7))
        + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "category": 7, "file_name": "빌드산출물.7z", "dst_file_name": "빌드산출물.7z", "file_size": 1000000, "total_pri_cnt": 0, "is_approve": false, "browser_url": "https://drive.google.com/upload"}'::jsonb,
    '{"id": "shin", "name": "신동현", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-SHIN"}'::jsonb
);

-- 한지민 / hanj
INSERT INTO log_dlp_chatgpt_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='hanj'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '21 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 0, "type": "chatgpt", "url": "https://chat.openai.com/", "payload": "신규 캠페인 고객 데이터 요약: 홍길동 010-..., 김영수 010-...", "pri_cnt": 8}'::jsonb,
    '{"id": "hanj", "name": "한지민", "path": "C:\\PCFILTER\\Agent", "com_name": "MKT-HANJ"}'::jsonb
);
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='hanj'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '22 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "category": 7, "file_name": "고객리스트.xlsx", "dst_file_name": "고객리스트.xlsx", "file_size": 1000000, "total_pri_cnt": 160, "is_approve": false, "browser_url": "https://drive.google.com/upload"}'::jsonb,
    '{"id": "hanj", "name": "한지민", "path": "C:\\PCFILTER\\Agent", "com_name": "MKT-HANJ"}'::jsonb
);

-- 오지은 / ohj
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='ohj'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '23 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "전체설계.zip", "dst_file_name": "전체설계.zip", "file_size": 1000000, "total_pri_cnt": 220, "device_type": "USB", "zip_filelist": "설계_백업.zip"}'::jsonb,
    '{"id": "ohj", "name": "오지은", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-OHJ"}'::jsonb
);
INSERT INTO log_dlp_sharedfolder_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='ohj'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '23 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 0, "category_type": 0, "file_name": "이관자료.zip", "file_path": "\\\\FILESERVER\\share\\이관자료.zip", "current_user": "ohj"}'::jsonb,
    '{"id": "ohj", "name": "오지은", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-OHJ"}'::jsonb
);

-- 문상철 / moon
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='moon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "고객사도면.dwg", "dst_file_name": "회의록.txt", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "moon", "name": "문상철", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-MOON"}'::jsonb
);
INSERT INTO log_dlp_website_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='moon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 1, "category": 1, "sub_url": "mail.company.com/send", "host_url": "mail.company.com", "checked_type": "normal"}'::jsonb,
    '{"id": "moon", "name": "문상철", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-MOON"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='moon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '9 days' + interval '16 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "도면_2.dwg", "dst_file_name": "메모.txt", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "moon", "name": "문상철", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-MOON"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='moon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '16 days' + interval '16 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "도면_3.dwg", "dst_file_name": "노트.txt", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "moon", "name": "문상철", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-MOON"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='moon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '23 days' + interval '16 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "도면_4.dwg", "dst_file_name": "사본.txt", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "moon", "name": "문상철", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-MOON"}'::jsonb
);

-- 배수지 / baesuji
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baesuji'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "인사평가.xlsx", "dst_file_name": "배경.jpg", "file_size": 1000000, "total_pri_cnt": 5, "device_type": "USB", "zip_filelist": "평가_사본.zip"}'::jsonb,
    '{"id": "baesuji", "name": "배수지", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-BAESUJI"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baesuji'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '8 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "인사_2.xlsx", "dst_file_name": "사진.jpg", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "baesuji", "name": "배수지", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-BAESUJI"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baesuji'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '15 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "인사_3.xlsx", "dst_file_name": "그림.jpg", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "baesuji", "name": "배수지", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-BAESUJI"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baesuji'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '22 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "인사_4.xlsx", "dst_file_name": "캡처.jpg", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "baesuji", "name": "배수지", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-BAESUJI"}'::jsonb
);
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baesuji'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '29 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "인사_5.xlsx", "dst_file_name": "이미지.jpg", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "baesuji", "name": "배수지", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-BAESUJI"}'::jsonb
);

-- 조현우 / cho
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='cho'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "급여기준.xlsx", "dst_file_name": "메모.txt", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "cho", "name": "조현우", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-CHO"}'::jsonb
);
INSERT INTO log_dlp_website_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='cho'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '14 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 1, "category": 1, "sub_url": "mail.company.com/send", "host_url": "mail.company.com", "checked_type": "normal"}'::jsonb,
    '{"id": "cho", "name": "조현우", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-CHO"}'::jsonb
);

-- 윤서연 / yoon
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='yoon'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '22 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "광고주계약.pdf", "dst_file_name": "사진.jpg", "file_size": 1000000, "total_pri_cnt": 90, "device_type": "USB"}'::jsonb,
    '{"id": "yoon", "name": "윤서연", "path": "C:\\PCFILTER\\Agent", "com_name": "MKT-YOON"}'::jsonb
);

-- 임재현 / lim
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='lim'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '3 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "견적모음.zip", "dst_file_name": "견적모음.zip", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB", "zip_filelist": "견적_전체.zip"}'::jsonb,
    '{"id": "lim", "name": "임재현", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-LIM"}'::jsonb
);
INSERT INTO log_dlp_website_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='lim'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '3 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 1, "category": 1, "sub_url": "mail.company.com/send", "host_url": "mail.company.com", "checked_type": "normal"}'::jsonb,
    '{"id": "lim", "name": "임재현", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-LIM"}'::jsonb
);

-- 곽태영 / kwak
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kwak'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "빌드.zip", "dst_file_name": "빌드.zip", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB", "zip_filelist": "빌드_사본.zip", "hash_extract_fail_reason": "password_protected_archive"}'::jsonb,
    '{"id": "kwak", "name": "곽태영", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-KWAK"}'::jsonb
);

-- 박민수 / park (기존 agent — INSERT 없이 로그만)
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='park'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '23 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "회의자료.pptx", "dst_file_name": "회의자료.pptx", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB", "zip_filelist": "회의_사본.zip"}'::jsonb,
    '{"id": "park", "name": "박민수", "path": "C:\\PCFILTER\\Agent", "com_name": "RND-PARK"}'::jsonb
);

-- 서지훈 / seo
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='seo'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '2 days' + interval '23 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "증빙.pdf", "dst_file_name": "증빙.pdf", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB", "hash_extract_fail_reason": "encrypted_zip"}'::jsonb,
    '{"id": "seo", "name": "서지훈", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-SEO"}'::jsonb
);

-- 남기훈 / nam
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='nam'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '15 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "계약서.pdf", "dst_file_name": "계약서.pdf", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB", "hash_extract_fail_reason": "password_protected_archive"}'::jsonb,
    '{"id": "nam", "name": "남기훈", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-NAM"}'::jsonb
);

-- 유하늘 / yoo
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='yoo'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "급여대장.xlsx", "dst_file_name": "급여대장.xlsx", "file_size": 1000000, "total_pri_cnt": 480, "device_type": "사내NAS"}'::jsonb,
    '{"id": "yoo", "name": "유하늘", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-YOO"}'::jsonb
);

-- 배우진 / baewj
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='baewj'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '13 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "category": 6, "file_name": "정기보고.pdf", "dst_file_name": "정기보고.pdf", "file_size": 1000000, "total_pri_cnt": 60, "is_approve": true}'::jsonb,
    '{"id": "baewj", "name": "배우진", "path": "C:\\PCFILTER\\Agent", "com_name": "ADM-BAEWJ"}'::jsonb
);

-- 강예린 / kangy
INSERT INTO log_dlp_media_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='kangy'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "media_type": "file", "file_name": "문서.docx", "dst_file_name": "문서.docx", "file_size": 1000000, "total_pri_cnt": 0, "device_type": "USB"}'::jsonb,
    '{"id": "kangy", "name": "강예린", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-KANGY"}'::jsonb
);

-- 정우성 / jungw
INSERT INTO log_dlp_website_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='jungw'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 1, "category": 1, "sub_url": "mail.company.com/send", "host_url": "mail.company.com", "checked_type": "normal"}'::jsonb,
    '{"id": "jungw", "name": "정우성", "path": "C:\\PCFILTER\\Agent", "com_name": "MKT-JUNGW"}'::jsonb
);

-- 손예진 / sonye
INSERT INTO log_dlp_chatgpt_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='sonye'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 0, "type": "chatgpt", "url": "https://chat.openai.com/", "payload": "엑셀 단축키 알려줘", "pri_cnt": 0}'::jsonb,
    '{"id": "sonye", "name": "손예진", "path": "C:\\PCFILTER\\Agent", "com_name": "HR-SONYE"}'::jsonb
);

-- 이도현 / leedh
INSERT INTO log_dlp_sharedfolder_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='leedh'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"block_type": 0, "category_type": 0, "file_name": "공용양식.docx", "file_path": "\\\\FILESERVER\\share\\공용양식.docx", "current_user": "leedh"}'::jsonb,
    '{"id": "leedh", "name": "이도현", "path": "C:\\PCFILTER\\Agent", "com_name": "DEV-LEEDH"}'::jsonb
);

-- 류준열 / ryu
INSERT INTO log_dlp_fileattach_t (license_code, agent_id, log_time, log_json, agent_json) VALUES (
    'DEMO0001',
    (SELECT agent_id FROM agent_t WHERE license_code='DEMO0001' AND user_info->>'user_id'='ryu'),
    ((date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
        - interval '1 days' + interval '11 hours') AT TIME ZONE 'Asia/Seoul'),
    '{"is_block": "false", "category": 6, "file_name": "주간보고.docx", "dst_file_name": "주간보고.docx", "file_size": 1000000, "total_pri_cnt": 0, "is_approve": false}'::jsonb,
    '{"id": "ryu", "name": "류준열", "path": "C:\\PCFILTER\\Agent", "com_name": "SALES-RYU"}'::jsonb
);

