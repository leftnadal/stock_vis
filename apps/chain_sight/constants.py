"""Chain Sight 유니버스 상수.

UNIVERSE_EXCLUDED_INDUSTRIES — 카드 유니버스(마인드맵 트리·카드·업종 집계)에서
숨길 industry 목록. 현재 = 레버리지 ETF 3종(OKLL·IREG·GEVG)의 소속 industry.
이들은 2배 롱 파생 ETF로 투자 유니버스 밖이며 관계(RC) 0.

⚠️ 임시 1단 필터 — 하이브리드 ③(2026-08-26 사용자 결정). 2단 승격 =
CS-UNIVERSE-EXCLUDE-FLAG(마이그 번들: SELFLOOP-DBCONSTRAINT 편승)에서
`Stock` 제외 플래그+사유코드로 승격 후 **이 상수 참조를 전부 걷어낸다**.
제외 판정을 이 단일 지점에 모아 2단 승격 시 걷어낼 곳이 한 군데가 되도록 한다.
"""

# 카드 유니버스에서 숨길 industry (exact match).
UNIVERSE_EXCLUDED_INDUSTRIES = ["Asset Management - Leveraged"]
