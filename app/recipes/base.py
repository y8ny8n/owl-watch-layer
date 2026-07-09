"""신호 레시피 인터페이스 + 레지스트리.

세션 작업(신호 SQL): 새 신호는 여기 Signal 을 하나 만들어 REGISTRY 에 등록만 하면
analyzer 가 자동으로 순회한다. "한 단계씩 확장"이 코드로 구현되는 지점.

설계문서 §3.1 신호 세트 / §3.3 채널교차 SQL 참조.
각 신호의 판정은 SQL 이 하고(안전벨트: 탐지=SQL), 여기선 그 SQL 과 가중치만 선언한다.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    code: str          # 예: "S1_ext_spoof"
    name: str          # 사람용 이름
    weight: int        # 스코어 가중치 (설계문서 §3.1)
    mitre: str = ""    # 근거 태그 (예: "T1027"), 없으면 빈 문자열


# 설계문서 §3.1 표 그대로. 판정 SQL 은 recipes/exfil.py (세션에서 작성) 이 담당하고,
# 여기 REGISTRY 는 "어떤 신호가 있고 몇 점인가"의 단일 정본.
REGISTRY: list[Signal] = [
    Signal("S1_ext_spoof",    "확장자·이름 바꿔치기",   25, "T1027"),
    Signal("S2_zip_hide",     "압축 은닉",             15, "T1027.015"),
    Signal("S3_enc_evade",    "암호화·검사회피",        20, "T1027"),
    Signal("S4_mass_pri",     "개인정보 다량 반출",     15),
    Signal("S5_unofficial",   "비공식 반출경로",        15),
    Signal("S6_night",        "야간·주말",             10),
    Signal("S7_cross_channel","채널 교차",             30),
    Signal("S8_genai_secret", "생성형AI 기밀 붙여넣기",  20),
    Signal("S9_persistence",  "지속 반복 탐지",         25, "T1029"),
]

BY_CODE = {s.code: s for s in REGISTRY}
