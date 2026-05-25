stock_vis -> iron_trading API 계약 초안
작성일: 2026-05-25
문서 상태: Claude Code 전달용 작업지시서

1. 목표
   iron_trading이 stock_vis를 실제 데이터 제공자로 활용할 수 있는지 검증하기 위해, stock_vis에 읽기 전용 HTTP API를 추가한다.

이 API는 미국 주식 전용 daily decision board 입력을 제공한다. iron_trading은 이 API를 호출해 시장 상태, Chain Sight 요약, 후보 종목, 다일 OHLCV, 데이터 신선도 정보를 받아 결정보드와 사후분석에 사용한다.

2. 협업 방식
   stock_vis는 Claude Code가 작업한다.
   iron_trading은 Codex가 작업한다.
   두 프로젝트는 코드, DB, ORM 모델, 마이그레이션, import 경로를 공유하지 않는다.
   공통 언어는 이 문서의 HTTP API 계약과 샘플 JSON이다.
   stock_vis 구현 완료 후 사용자는 API base URL과 실제 샘플 응답 1개를 Codex에게 전달한다.
3. 핵심 원칙
   stock_vis는 read-only provider다.
   iron_trading은 stock_vis에 쓰기 요청을 하지 않는다.
   stock_vis 내부 DB schema나 backend service 객체를 iron_trading이 직접 참조하지 않는다.
   응답은 재현 가능한 daily snapshot이어야 한다. 같은 trading_date와 같은 data version이면 같은 응답을 반환한다.
   미국 주식 정규장 기준 데이터를 우선한다.
   API가 불완전하거나 오래된 데이터를 반환하면 iron_trading은 새 결정보드 생성을 차단할 수 있어야 한다.
4. 1차 Endpoint
   GET /api/v1/iron-trading/daily-context
   목적: 특정 거래일의 결정보드 입력 데이터를 한 번에 제공한다.

Query parameters:

이름 필수 예시 설명
date required 2026-05-22 미국장 거래일. YYYY-MM-DD.
universe optional us_core 후보군 범위. 기본값은 stock_vis가 정한 미국 주식 기본 후보군.
limit optional 30 후보 종목 최대 개수. 기본값은 30.
성공 응답:

HTTP 200
Content-Type: application/json
모든 숫자는 부동소수점 number가 아니라 string으로 내려도 된다. iron_trading은 Decimal로 파싱한다.
실패 응답:

HTTP 400: 잘못된 날짜/파라미터
HTTP 404: 해당 거래일 snapshot 없음
HTTP 503: stock_vis 데이터 생성 중 또는 필수 데이터 미완성 5. 응답 JSON 계약
{
"schema_version": "1.0",
"provider": "stock_vis",
"snapshot_id": "stockvis-us-2026-05-22-v1",
"trading_date": "2026-05-22",
"captured_at": "2026-05-23T01:05:00+00:00",
"market_timezone": "America/New_York",
"universe": "us_core",
"freshness": {
"status": "fresh",
"as_of": "2026-05-22T20:05:00-04:00",
"max_age_minutes": 1440,
"warnings": []
},
"market_pulse": {
"regime_hint": "risk_on_pullback",
"summary": "S&P 500은 약세지만 AI/반도체 후보군 내부 상대강도는 유지됩니다.",
"risk_notes": [
"지수 변동성이 높아 신규 매수는 상위 상대강도 후보로 제한",
"실적 발표 전후 종목은 포지션 사이징 축소"
],
"opportunity_notes": [
"하락장 안에서도 20일 상대강도 상위 후보는 추세 유지",
"거래량 동반 돌파 후보를 우선 관찰"
]
},
"chain_sight": {
"summary": "AI 인프라와 전력/데이터센터 체인이 강합니다.",
"themes": [
{
"name": "AI infrastructure",
"tone": "positive",
"symbols": ["NVDA", "AMD", "ANET"],
"summary": "GPU와 네트워크 장비 수요 기대가 유지됩니다."
}
]
},
"candidates": [
{
"symbol": "NVDA",
"company_name": "NVIDIA Corporation",
"exchange": "NASDAQ",
"currency": "USD",
"last_price": "950.12",
"score": "0.86",
"rank": 1,
"thesis": "AI 인프라 체인 내 상대강도와 거래량이 동시에 개선되었습니다.",
"signals": {
"momentum_20d": "0.0820",
"momentum_60d": "0.2140",
"sma20_distance_pct": "0.0450",
"sma50_distance_pct": "0.0910",
"volume_ratio_20d": "1.42",
"relative_strength_rank": 3,
"breakout_score": "0.78",
"pullback_quality": "0.41"
},
"risk_flags": [
"earnings_within_14d"
],
"tags": ["AI infrastructure", "semiconductor"],
"ohlcv": [
{
"date": "2026-05-20",
"open": "930.10",
"high": "955.30",
"low": "925.40",
"close": "948.20",
"volume": "51230000"
},
{
"date": "2026-05-21",
"open": "946.00",
"high": "962.40",
"low": "940.10",
"close": "950.12",
"volume": "48700000"
}
]
}
]
} 6. 필드 의미
Top-level
필드 필수 설명
schema_version yes 최초 버전은 1.0. breaking change 시 major version 증가.
provider yes 항상 stock_vis.
snapshot_id yes 같은 응답을 추적하기 위한 고유 id.
trading_date yes 미국장 기준 거래일.
captured_at yes stock_vis가 snapshot을 생성한 UTC 또는 timezone 포함 시각.
market_timezone yes 기본 America/New_York.
universe yes 후보군 이름.
freshness yes 데이터 신선도와 경고.
market_pulse yes 시장 상태 요약.
chain_sight no Chain Sight가 아직 없으면 null 또는 생략 가능.
candidates yes 후보 종목 배열. 비어 있으면 freshness.warnings에 이유를 넣는다.
freshness
필드 필수 설명
status yes fresh, stale, partial, building, error 중 하나.
as_of yes 데이터 기준 시각.
max_age_minutes yes 이 snapshot이 허용하는 최대 지연 시간.
warnings yes 사람이 읽을 수 있는 경고 목록.
market_pulse
필드 필수 설명
regime_hint yes 짧은 regime key. 예: risk_on_pullback, risk_off, trend_following.
summary yes 결정보드 상단에 쓰기 좋은 1-2문장 요약.
risk_notes yes 리스크 목록.
opportunity_notes yes 기회 목록.
chain_sight
필드 필수 설명
summary no 테마/체인 전체 요약.
themes no 관련 테마 배열.
candidates
필드 필수 설명
symbol yes 미국 주식 ticker. 대문자.
company_name no 기업명.
exchange no 거래소.
currency yes MVP에서는 USD.
last_price yes 최신 종가 또는 snapshot 기준 가격.
score yes stock_vis 후보 점수. 0.00-1.00.
rank yes 후보군 내 순위.
thesis yes stock_vis 관점의 핵심 가설.
signals yes 기술/상대강도 지표 묶음.
risk_flags yes 리스크 key 목록. 없으면 빈 배열.
tags yes 테마/섹터 tag 목록.
ohlcv yes 최소 60거래일 권장. MVP 테스트는 20거래일 이상이면 통과 가능. 7. stock_vis 구현 요구사항
Claude Code는 stock_vis에서 다음을 구현한다.

GET /api/v1/iron-trading/daily-context endpoint 추가.
endpoint는 미국 주식 후보만 반환한다.
응답은 위 JSON 계약을 따른다.
ohlcv는 후보별 다일 가격봉을 포함한다.
market_pulse는 기존 stock_vis 또는 관련 backend 데이터에서 생성한다.
Chain Sight 데이터가 이미 있으면 chain_sight에 연결한다. 아직 준비되지 않았으면 null 또는 빈 요약을 반환하되 schema는 유지한다.
필수 데이터가 아직 생성 중이면 503과 명확한 error body를 반환한다.
내부 DB 모델이나 service 구조를 API 밖으로 노출하지 않는다.
테스트를 추가한다.
구현 후 실제 샘플 응답 JSON 1개를 사용자에게 제공한다.
1차 구현에서 인증은 생략해도 된다. 이 API는 로컬 개인 프로젝트 연동 검증용이며, 외부 배포 또는 공용 노출을 전제로 하지 않는다. 다만 endpoint 이름은 명확히 iron-trading namespace 안에 두어 일반 사용자용 API와 섞이지 않게 한다.

market_pulse와 chain_sight가 아직 stock_vis 내부에서 완성되지 않았다면 다음 기준을 따른다.

market_pulse는 최소한 regime_hint, summary, risk_notes, opportunity_notes를 빈 값 없이 반환한다.
chain_sight는 준비되지 않았으면 {"summary": "", "themes": []} 형태로 반환한다.
후보 종목, score, thesis, OHLCV가 더 중요하므로 Chain Sight 때문에 전체 endpoint를 막지 않는다.
반대로 후보 종목 또는 OHLCV가 없으면 결정보드 입력이 성립하지 않으므로 503 또는 404를 반환한다. 8. 권장 error body
{
"schema_version": "1.0",
"provider": "stock_vis",
"error": {
"code": "snapshot_not_ready",
"message": "2026-05-22 daily context snapshot is still building.",
"retry_after_seconds": 300
}
} 9. Claude Code에게 전달할 작업지시서
아래 블록을 stock_vis를 작업 중인 Claude Code에 그대로 전달한다.

stock_vis에 iron_trading용 read-only HTTP API를 추가해줘.

목표:

- iron_trading이 stock_vis의 미국 주식 시장/후보군 데이터를 직접 HTTP API로 받아 daily decision board에 사용하려고 함.
- stock_vis는 외부 데이터 제공자 역할만 하고, iron_trading과 DB/ORM/코드/import를 공유하지 않음.

구현할 endpoint:

- GET /api/v1/iron-trading/daily-context

query:

- date: required, YYYY-MM-DD, 미국장 거래일
- universe: optional, 기본 us_core 또는 stock_vis 기본 미국 주식 후보군
- limit: optional, 기본 30

응답:

- schema_version, provider, snapshot_id, trading_date, captured_at, market_timezone, universe
- freshness
- market_pulse
- chain_sight
- candidates[]

후보별 필수 정보:

- symbol, currency, last_price, score, rank, thesis
- signals: momentum_20d, momentum_60d, sma20_distance_pct, sma50_distance_pct, volume_ratio_20d, relative_strength_rank, breakout_score, pullback_quality
- risk_flags, tags
- ohlcv: 최소 20거래일, 가능하면 60거래일 이상

중요 제약:

- 미국 주식만 반환
- read-only API
- 1차 구현에서 인증은 생략 가능. 단, 외부 노출 전제 아님
- 내부 DB schema나 backend 객체를 응답에 그대로 노출하지 말 것
- 데이터 생성 중이면 503 + error body
- snapshot 없음은 404
- 잘못된 query는 400
- 테스트 추가
- Chain Sight가 없더라도 endpoint는 후보/가격/market_pulse 중심으로 동작해야 함

완료 후 나에게 알려줄 것:

1. endpoint URL
2. 실행 방법
3. 테스트 명령과 결과
4. 200 응답 샘플 JSON 1개
5. 404 또는 503 error 샘플 JSON 1개
6. iron_trading 수용 기준
   stock_vis 쪽 구현이 끝나면 iron_trading에서는 다음을 구현한다.

StockVisHttpApiClient 추가.
설정값 추가:
IRON_TRADING_STOCKVIS_BASE_URL
IRON_TRADING_STOCKVIS_TIMEOUT_SECONDS
IRON_TRADING_STOCKVIS_UNIVERSE
API 응답을 local DTO로 정규화.
raw snapshot을 로컬 DB에 저장.
StockSignal, PriceBar, market_pulse, chain_sight를 DailyStrategyContext에 연결.
freshness.status != fresh이면 새 결정보드 생성을 차단하거나 경고 처리.
HTTP client fixture test와 contract sample test를 추가. 11. 이번 단계에서 하지 않는 것
KIS/NH 실주문 연결.
stock_vis DB 직접 접근.
stock_vis 코드를 iron_trading에서 import.
iron_trading이 stock_vis에 추천 결과를 write-back.
C2 성과 검증 자동화. 12. 다음 단계
사용자가 이 문서를 Claude Code에 전달한다.
Claude Code가 stock_vis endpoint를 구현한다.
사용자가 base URL과 샘플 응답을 Codex에게 전달한다.
Codex가 iron_trading에 HTTP client와 수용 테스트를 구현한다.
