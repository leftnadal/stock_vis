<!--
정착 스냅샷(D-DOCS-PERSIST). 이력 참고물 — 결정 정본은 DECISIONS.md "Slice C-core".
실행: 브랜치 monorepo/sess-C-core-l2 (base origin/main bb91c98), 2026-07-14.
-->
# 구현 지시서 — Slice C-core: L2 국면 카테고리 + FE 슬롯 활성 + docs 정착

## 1. 배경·의도 + 확정 결정
- **의도:** Slice B가 남긴 카드의 두 빈 슬롯 중 **결정론 쪽(cat_slot)**을 먼저 채운다. 각 이웃일에
  "그날이 어떤 국면 유형이었나" 태그를 상시 표시. C-N(뉴스 백필)과 **완전 독립·병렬**.
- **확정 결정:**
  - **L2 소스 = RegimeSnapshot의 regime 확정치(+벡터).** 외부 의존 0·683 전 구간 커버·결정론.
    "뉴스 이벤트 유형"에서 **"국면 유형"으로 의미 전환** — 시각 구조(태그 상시)는 목업 그대로, 어휘만 전환.
  - **③B 라벨 ON**의 절반 실현: cat_slot 채움. `why`(L3)는 C-N 백필 완료 후 C-L3에서.
- **원칙:** 판단 로직 단일 출처 = payload builder(백엔드). FE는 태그를 소비만. 카피 = 정적 테이블(LLM-free).

## 3. 경계·안전 제약
- 뉴스·LLM 0. 의존 방향 apps→shared(+macro). prod 쓰기 0·마이그레이션 0(L2 = regime 확정치 순수 함수 파생).
- 행위보존: cat_slot null→값(가산). 그 외 필드·팬·경보 무변경.
- **CRISIS 카피 게이트(절대):** 태그는 그날의 사실 분류 표기까지만. "오늘이 위기와 유사" 류 유사성 주장
  카피는 카드 어디에도 넣지 않는다(역사적 CRISIS 6일은 유사성 주장 근거로 불충분).

## 4. 슬라이스 구성
- Part 1 — L2 카테고리 정적 매핑(결정론 순수 함수). regime 값 전수 전사, 미지 값 명시적 에러.
- Part 2 — payload 배선(이웃 cat_slot + today 태그).
- Part 3 — FE 태그 활성(analog-cat 슬롯), why 슬롯 무접촉.
- Part 4 — docs 정착(지시서·목업 repo 커밋) + D-DOCS-PERSIST 등재.

## 8. DoD
1. 이웃 전건 + (가능 시) today 국면 카테고리 태그 렌더(목업 톤, 어휘=국면 유형).
2. 분류 = payload builder 순수 함수 단일 출처, FE 재구현 0, 저장 0, LLM·뉴스 0.
3. CRISIS 카피 게이트 준수(사실 표기만).
4. why 슬롯 비활성 무접촉.
5. docs 정착 + D-DOCS-PERSIST 등재 + TASKQUEUE 갱신.
6. 검증 게이트 전부 GREEN.

## 부록 — 범위 밖
- why(L3)·LLM cached 생성 = C-L3(C-N 전량 백필 후). as-of 제품 표면·문턱 재판정 = Phase5/S4-REBASE.
