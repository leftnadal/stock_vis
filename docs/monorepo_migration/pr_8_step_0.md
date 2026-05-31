PR8 STEP 0 — 루트 잔존 7앱 분류 조사 (READ-ONLY 조사·정지, mv·삭제 절대 금지)

[전제] PR8 = 트랙 마지막, 지금까지와 다름. 7앱(rag_analysis·serverless·macro·
news·thesis·sec_pipeline·validation)의 처분이 미결(이동/해체/삭제 갈림).
plan "이관 5건" vs 실제 7개 갭 존재. 이 STEP은 조사만, 결정은 사용자가.
mv·edit·삭제·commit 일절 금지.

[프롬프트 자체 확인]
① main HEAD = f80b7dd 확인 (아니면 STOP·보고)
② tag monorepo-pre-pr8 존재 확인 (롤백 지점)
③ READ-ONLY. 어떤 파일도 수정·생성·삭제 안 함. 특히 "삭제 후보"라도
절대 삭제하지 말 것 — 후보 식별만, 실삭제는 사용자 결정 후 별도

──────────────────────────────────────────────
STEP 0-A — 7앱 활성도 매트릭스 (각 앱당 동일 조사)
대상: rag_analysis, serverless, macro, news, thesis, sec_pipeline, validation
각 앱에 대해:
(1) INSTALLED_APPS 등록 여부 (grep config/settings.py)
(2) URL 등록 여부 (grep config/urls.py)
(3) 외부(다른 앱)에서 import하는 호출처 수 (메인코드, tests 제외)
(4) 모델 보유 여부 (models.py / models/ 존재 + migration 존재)
(5) Celery task 등록 여부
→ 표로 박기. 활성도 판정:
· 등록O + 외부호출O + 모델O = ACTIVE (이동 대상)
· 등록O + 외부호출0 + 모델O = ACTIVE-격리 (이동, PR3 iron_trading형)
· 등록X + 외부호출0 = DORMANT/삭제후보 (해체·삭제 검토)
· 모델0 + 코드 최소 = 잉여 의심 (삭제후보)

STEP 0-B — plan 갭 규명 (5 vs 7)

- execution_plan_v1.md에서 PR8 "이관 5건"의 5건이 구체적으로 무엇인지 추출
  (plan에 명시 있으면 그 목록, 없으면 "미명시" 박기)
- 7앱 중 어느 2개가 "이관 5건"에서 빠졌는지 대조
- 빠진 2개의 plan상 의도 grep (해체/삭제 언급 있는지)
- blueprint §②에서 macro "해체", 잉여 모델 "삭제" 관련 라인 전부 박기

STEP 0-C — 해체/삭제 후보 안전성 조사 (★ 되돌리기 어려운 액션 사전 검증)

- 0-A에서 DORMANT/삭제후보로 판정된 앱에 대해:
  · 해당 앱을 import하는 곳 전수 (메인 + tests + scripts + migration)
  · 다른 앱의 migration이 이 앱 모델을 FK/참조하는지 (to="<app>.X")
  → 참조 있으면 삭제 시 migration 깨짐 = 삭제 위험 ⚠ 박기
  · 이 앱의 모델에 실데이터 의존 가능성 (운영 DB 영향) 정성 메모
- 해체후보(macro)에 대해:
  · macro 코드가 실제로 어디서 쓰이는지 (Market Pulse 관련 grep)
  · "해체"가 무엇으로 흡수를 의미하는지 단서 (이미 packages/shared나
  apps/market_pulse로 일부 이동했는지)

STEP 0-D — 이동 대상의 target 트랙 조사

- 0-A에서 ACTIVE 판정된 앱들이 어느 트랙으로 갈지 단서:
  · plan/blueprint에 각 앱의 target 명시 있는지 (apps/ vs packages/shared)
  · news = News Intelligence(완료 기능), validation = 1차검증,
  sec_pipeline = SEC 파이프라인 등 성격상 분류 힌트 박기
- rename 동반 여부 (snake_case 등, PR4/PR6형)

STEP 0-E — 루트 메타 정리 항목 식별 (PR8 "메타 정리" 분)

- 루트에 남은 비-앱 정리 대상 (PR7까지 옮기며 생긴 잔재):
  · marketpulse/ 빈 디렉토리 (중간보고 발견분, untracked)
  · graph_analysis 자기참조 import 2건 (중간보고 발견분)
  · dashboard docs 잔재 (plan 도식)
  · 기타 루트 잔여
- 목록만 박기 (정리는 PR8 실행 시)

STEP 0-F — 종합 보고·정지 (여기서 멈춤)

- 0-A 활성도 매트릭스 + 0-B 갭 규명 + 0-C 안전성 + 0-D target + 0-E 메타
  전부 표로 박고 STOP
- 각 앱을 [이동→트랙 / 해체→흡수처 / 삭제→위험도] 로 분류 제안 박되,
  "제안일 뿐 결정은 사용자" 명시
- 삭제후보가 있으면 그 위험도(migration 참조·데이터)를 별도 강조

──────────────────────────────────────────────
HALT 트리거 (정지·보고):

1. 어떤 앱이든 분류가 모호 (등록·호출 엇갈림) → 박고 보고
2. 삭제후보에 migration FK 참조 발견 (삭제 시 깨짐) → 강조 보고
3. plan "5건" 정체가 코드와 전혀 안 맞음 → 박고 보고
   금지: 파일 수정·생성·삭제, mv, commit, tag, LLM 호출.
   ★ "삭제 후보"라도 절대 삭제 금지 — 식별만. 이상 발견해도 고치지 말 것.
   ──────────────────────────────────────────────
