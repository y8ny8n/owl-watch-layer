# DESIGN_07 · 인라인 편집 ↔ 실제 PCFILTER 정책 스키마 대조

> 근거: `pcfilter_work/.claude/api-spec/snapshots/정보유출방지.csv`, `공통_정책.csv`,
> `db-map/spec.json` (실제 테이블명). OWL 인라인 편집기(승인 전 조정)의 "동작·채널·시간·대상"
> 옵션을 실제 스키마와 맞춘 결과. **핵심: 지금 실제로 반영되는 조치는 매체(USB) 차단 하나뿐이며,
> 나머지 옵션은 스키마상 별개 정책이라 "곧 지원"으로 정직하게 비활성 유지가 맞다.**

## 1. 확인된 사실 (실 스키마)

### 매체 관리 정책 `set_media_manage`
- `use`, `media_pid`, `name`
- `device { fdd_usb, rhdd, cd_dvd, wpd, wireless, wired_lan, bluetooth, ... }`
  - 값 정의: **0 = 허용 · 1 = 장치차단 · 2 = 읽기전용 · 3 = 읽기전용-삭제가능 · 4 = 관제대상 제외**
  - `fdd_usb` = 이동식 디스크(FDD/USB/R-HDD), `rhdd` = 외장형 하드, `cd_dvd` = CD/DVD/BD
- `device_alarm { ... }`, `mac_device { ... }` (0~2), `pid`(개인정보 정책번호), `alarm`,
  `save { use, pid }`, `offline { use, policy { media_pid, device{...} } }`

즉 **"USB/이동식 차단"의 실제 표현은 `device.fdd_usb = 1`(장치차단)** 이다.

### 매체 개별정책 `media_separate` (OWL 이 쓰는 경로)
- 특정 사용자에게 매체 정책을 개별 지정하는 메커니즘. `policy_t(policy_type='media_separate')`
  + `policy_sub_t(sub_name='target_user')` 로 대상 지정. `pvn = pvn + 1` 필수(에이전트 갱신 감지).
- OWL `policy.py`(스카우트 확인 `setMediaSeparatePolicyAdd`)가 이 경로를 raw SQL 로 재현.

## 2. 대조 결과 · 인라인 편집기 옵션

| 편집기 옵션 | 실제 스키마 | 현재 처리 | 판단 |
|---|---|---|---|
| 동작: **USB 매체 차단** | `media_separate` + 매체정책(`device.fdd_usb=1`) | **실동작**(policy.py) | 유지 |
| 동작: 파일첨부 차단 | `set_attach` 계열(별개 정책) | 비활성 "곧 지원" | 정직 — 별개 write 필요 |
| 동작: 생성형 AI 차단 | ChatGPT/웹 정책(별개) | 비활성 "곧 지원" | 정직 — 별개 write 필요 |
| 적용 시점: 야간/주말/상시 | `time_set` + `s_time`/`e_time`(기간) | **실동작** | 유지 |
| 대상 | `policy_sub_t.target_user` (agent_id) | **실동작**(리포트 대상 고정) | 유지 |

## 3. 프로덕션 TODO (데모 이후)

1. **`policy.py` `_BLOCK_MEDIA_PID = 0` 은 플레이스홀더.** 실제 차단이 걸리려면 대상 라이선스에
   "이동식 차단(`device.fdd_usb=1`)" 프리셋 매체정책이 존재하고 그 `media_pid` 를 참조해야 함.
   (또는 `media_separate` 가 인라인 `device` 블록을 허용하는지 실 DB 로 검증 후 인라인 삽입.)
2. 파일첨부/생성형AI 차단을 실동작화하려면 각 정책(`set_attach`/웹·ChatGPT)의 write 경로를
   `write-map/write-map.json` 대조 후 추가. 그 전까지 편집기에서 비활성 유지.
3. `mac_device` 는 값 범위가 0~2(3·4 없음) — 크로스플랫폼 시 분기 필요.
