# pytest 베이스라인 선존 실패 스냅샷 (SSOT)

> **목적**: 전체 pytest 스위트의 **선존(pre-existing) 실패 집합**을 고정한다. 세션 게이트가
> "문자적 green"이 아니라 **"이 베이스라인 대비 신규 회귀 0"**으로 판정될 수 있도록 하는
> 단일 진실. 신규 작업이 이 목록 밖의 실패를 만들면 = 회귀(차단), 이 목록과 동일하면 = 통과.
>
> **갱신 규칙**: 부채가 상환(수정)되면 해당 항목을 이 목록에서 제거한다. 목록이 줄어드는
> 방향으로만 갱신(늘어나면 회귀 유입 신호). 상환 트랙 = `TASKQUEUE.md` "테스트 부채 상환".

## 측정 스냅샷

- **측정일**: 2026-07-09
- **측정 기준 커밋**: origin/main `924ef96` (MON-P2-BEAT land 직후). MON-P2-BEAT 변경 전
  베이스라인(`1cdea3c`)과 변경 후 실패 집합이 **완전 동일**함을 diff로 확증(신규 회귀 0).
- **집계**: `18 failed / 3532 passed / 53 skipped / 102 errors` (실행 200s, `--maxfail=0`)
  - 변경 전 베이스라인: `18 failed / 3520 passed / ... / 102 errors` (passed 차 +12 = MON-P2-BEAT 신규 테스트).
- **총 선존 실패**: **120건** (18 failed + 102 errors). 전부 `apps/monitor`와 **disjoint**.
- **재현 명령**: `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES PGGSSENCMODE=disable poetry run pytest tests/ -q --maxfail=0`
  - ⚠ `pytest.ini`의 `addopts`에 `--maxfail=5`가 있어 기본 실행은 조기 종료. 전량 파악엔 `--maxfail=0` override 필수.

## 실패군 분류 (4 클러스터)

### C1. news_deep_analyzer — LLM seam 이동 stale mock (102 errors) 🔴 테스트 부채

- **파일**: `tests/news/test_news_deep_analyzer.py` (전 10 클래스 102건 collection error)
- **에러 시그니처**: `AttributeError: module 'services.news.services.news_deep_analyzer' does not have the attribute 'genai'`
- **원인**: BOUNDARY-LLM 이관으로 `news_deep_analyzer`가 `genai`를 직접 import하지 않고 shared LLM 래퍼를 경유 → 테스트의 `patch('...news_deep_analyzer.genai')`가 대상 부재로 setup 단계 실패.
- **성격**: **코드 회귀 아님**(코드는 정상, 이관 완료). 테스트가 옛 seam(직접 genai)을 mock → 새 seam(shared 래퍼)으로 **재작성 필요**(비기계적).
- **상환**: `DEBT-TEST-BOUNDARY-LLM` (아래). 메모리 `project_boundary_llm_track` backlog의 "test_news_deep_analyzer 102e"와 동일 건.
- 클래스별: TestDetermineTier 20 · TestParseResponse 15 · TestBuildPrompt 14 · TestAnalyzeBatch 13 · TestBuildSystemPrompt 9 · TestValidateTickers 9 · TestAnalyzeSingle 7 · TestEdgeCases 7 · TestNewsDeepAnalyzerInit 5 · TestGetValidSymbols 3.

### C2. csv_url_resolver — LLM seam 이동 stale mock (4 failed) 🔴 테스트 부채

- **파일**: `tests/serverless/test_csv_url_resolver.py::TestLLMAnalysis`
  - `test_llm_finds_url` · `test_llm_not_found` · `test_llm_extracts_url_from_text` · `test_no_llm_client_returns_none`
- **원인**: `_find_csv_url_by_llm` LLM 호출 경로가 shared 래퍼로 이동 → 테스트 mock이 옛 seam 가정.
- **성격**: C1과 동일(BOUNDARY-LLM seam 이동, mock 재작성). 메모리 backlog "test_csv_url_resolver 4f"와 동일.
- **상환**: `DEBT-TEST-BOUNDARY-LLM`.

### C3. chainsight/attention — 빈 테마/시드 오탐 의심 (6 failed) 🟡 pristine 판정 필요

- **파일**: `tests/chainsight/test_attention.py` (TestEventBoardAPI 3 · TestEventRankingAPI 3)
  - `test_event_board_has_theme` · `_includes_small_groups` · `_includes_single_member_group`
  - `test_ranking_sorted_by_score_desc` · `_includes_is_low_liquidity` · `test_ranking_response_schema`
- **에러 시그니처**: `AssertionError: assert 'SEMICON' in []` (event board가 빈 테마 반환)
- **성격**: 메모리 `lesson` — "stale `_dormant/graph_analysis` 잔재 + 공유 test DB가 attention N건 오탐 → **pristine 체크아웃서만 판정**". `.claude/worktrees/`에 news-av-broad·credit-signals **stale 워크트리 + `_dormant` 실재**(측정 시 확인). **선존·비-monitor**이나 코드 결함 여부는 **pristine 재현으로만 확정**.
- **상환**: `DEBT-TEST-CHAINSIGHT` — pristine 체크아웃 재현 → 오탐이면 격리 픽스처/시드, 진성이면 코드.

### C4. chainsight/leadership + upward_learning — 404/노옵 원인 미확정 (8 failed) 🟡 pristine 판정 필요

- **파일**: `tests/chainsight/test_leadership_api.py` (7) + `tests/chainsight/test_upward_learning.py` (1)
  - leadership: TestRankingLeadershipFields 3 (`test_m1_fields_preserved`·`_m2_fields_present`·`_trend_quality_populated`) + TestWindowParam 4 (`test_default_window_is_20`·`_explicit_window_120`·`_invalid_window_falls_back_to_20`·`_nonint_window_falls_back`)
  - upward: `TestTaskFlagOff::test_task_is_noop_when_flag_off`
- **에러 시그니처**: `assert 404 == 200`, `KeyError: 'stocks'` (leadership 랭킹 API가 404).
- **성격**: **미확정** — 라우트/시드/공유 DB 상태 중 무엇인지 pristine 재현 전 단정 불가. C3와 함께 판정.
- **상환**: `DEBT-TEST-CHAINSIGHT`.

## 전체 목록 (120건, 상환 시 개별 삭제)

### FAILED (18)
```
tests/chainsight/test_attention.py::TestEventBoardAPI::test_event_board_has_theme
tests/chainsight/test_attention.py::TestEventBoardAPI::test_event_board_includes_single_member_group
tests/chainsight/test_attention.py::TestEventBoardAPI::test_event_board_includes_small_groups
tests/chainsight/test_attention.py::TestEventRankingAPI::test_ranking_includes_is_low_liquidity
tests/chainsight/test_attention.py::TestEventRankingAPI::test_ranking_response_schema
tests/chainsight/test_attention.py::TestEventRankingAPI::test_ranking_sorted_by_score_desc
tests/chainsight/test_leadership_api.py::TestRankingLeadershipFields::test_m1_fields_preserved
tests/chainsight/test_leadership_api.py::TestRankingLeadershipFields::test_m2_fields_present
tests/chainsight/test_leadership_api.py::TestRankingLeadershipFields::test_trend_quality_populated
tests/chainsight/test_leadership_api.py::TestWindowParam::test_default_window_is_20
tests/chainsight/test_leadership_api.py::TestWindowParam::test_explicit_window_120
tests/chainsight/test_leadership_api.py::TestWindowParam::test_invalid_window_falls_back_to_20
tests/chainsight/test_leadership_api.py::TestWindowParam::test_nonint_window_falls_back
tests/chainsight/test_upward_learning.py::TestTaskFlagOff::test_task_is_noop_when_flag_off
tests/serverless/test_csv_url_resolver.py::TestLLMAnalysis::test_llm_extracts_url_from_text
tests/serverless/test_csv_url_resolver.py::TestLLMAnalysis::test_llm_finds_url
tests/serverless/test_csv_url_resolver.py::TestLLMAnalysis::test_llm_not_found
tests/serverless/test_csv_url_resolver.py::TestLLMAnalysis::test_no_llm_client_returns_none
```

### ERROR (102) — 전량 `tests/news/test_news_deep_analyzer.py` (동일 근본원인 = genai attr 부재)
클래스별 집계: TestDetermineTier 20 · TestParseResponse 15 · TestBuildPrompt 14 · TestAnalyzeBatch 13 · TestBuildSystemPrompt 9 · TestValidateTickers 9 · TestAnalyzeSingle 7 · TestEdgeCases 7 · TestNewsDeepAnalyzerInit 5 · TestGetValidSymbols 3.

> 참고: `scripts/health_check.py:KNOWN_TEST_FAILS`(환경 known-fail 4건, Finnhub 키 부재)는 이 스냅샷과 **별개의 좁은 레지스트리**(회귀 카운트 명시 제외용). 본 문서가 전체 선존 실패의 SSOT.
