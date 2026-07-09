# recipes/ — 신호 레시피

"한 단계씩 확장"이 코드로 구현되는 곳. 신호 추가 = 여기 파일 추가.

- `base.py` — `Signal` 정의 + `REGISTRY`(신호 목록·가중치의 단일 정본). 설계문서 §3.1.
- `exfil.py` — 유출 후보 산출 SQL(허용로그 대상). 설계문서 §3.3. **[세션에서 구현]**

## 새 신호 추가 절차
1. `base.py` REGISTRY 에 `Signal(...)` 한 줄 추가 (코드·이름·가중치·MITRE).
2. `exfil.py`(또는 새 레시피 파일)에서 그 신호의 판정 SQL 과 evidence 추출 추가.
3. `scoring.build_signals_json` 이 자동으로 반영(코드 기반).

원칙(안전벨트): **판정은 SQL 이 한다. AI 는 결과를 설명만 한다.**
