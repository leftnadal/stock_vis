"""
apps/market_pulse/llm — market_pulse 내부 LLM 공용 plumbing (단일출처).

Brief(briefing/)·Translation(후속)이 genai 호출·출력 검출기를 복제 없이 재사용한다.
※ 범용 cross-surface LLM 래퍼(rag 포함)는 BOUNDARY-LLM 트랙(타 세션) 소관 — 본 모듈은
  market_pulse zone 내부 공용에 한정한다.
"""
