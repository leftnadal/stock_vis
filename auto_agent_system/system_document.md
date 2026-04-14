# Stock-Vis 야간 자율 에이전트 시스템

매일 밤 AI가 코드를 분석하고, 문제를 수정하고, 서비스 전략까지 검토해서
다음 날 아침 리포트로 전달하는 자동화 시스템.

---

## 1. 시스템 개요

### 핵심 아이디어

개발자(병진)가 자는 동안 4개의 AI 모델이 역할을 나눠서 Stock-Vis 코드베이스를
분석 → 수정 → 검증 → 크로스 체크 → 전략 제안까지 수행한다.
아침에 일어나면 종합 리포트 하나만 읽으면 된다.

### 사용 모델과 역할

```
┌─────────────────────────────────────────────────────────────────┐
│  Haiku 4.5 (빠르고 저렴)     → 스캔, 테스트 실행, 빠른 검증     │
│  Sonnet 4.6 (균형)           → 코드 수정, 심층 분석 초안         │
│  Opus 4.6 (최고 추론)        → 검증/비판, 전략 판단, 최종 리포트 │
│  GPT-5-Codex (크로스 체크)   → Claude blind spot 탐지           │
└─────────────────────────────────────────────────────────────────┘
```

### 전체 흐름

```
밤 23:00 시작
│
├─ [매일] 코드 건강성 체크
│   ├── Phase 1: 코드 스캔 ─────────── Haiku ───── 5분
│   ├── Phase 2: 자동 수정 ─────────── Sonnet ──── 15분
│   ├── Phase 3: 수정 검증 ─────────── Haiku ───── 5분
│   └── Phase 4: Codex 크로스 리뷰 ── GPT-5 ───── 10분
│
├─ [요일별] 심층 분석
│   └── Sonnet↔Opus 검증 루프 ──────────────────── 30분
│       (최대 5라운드)
│
├─ 아침 리포트 통합 ────────────────── Opus ────── 10분
│
│                                      총 ~75분
▼
아침 08:00 알림
├── macOS 알림 팝업
├── HTML 리포트 브라우저 자동 열기
└── Slack 메시지 (선택)
```

---

## 2. 매일 실행되는 작업

### Phase 1: 코드 스캔 (Haiku)

테스트, 타입 체크, 린트를 빠르게 돌려서 현재 상태 파악.

- `pytest tests/ -q --tb=line`
- `cd frontend && npx tsc --noEmit`
- `ruff check . --statistics`
- 최근 24시간 커밋 목록

결과: 🟢 정상 / 🟡 주의 / 🔴 문제 있음

### Phase 2: 자동 수정 (Sonnet)

Phase 1에서 발견된 문제 중 안전하게 수정 가능한 것만 별도 브랜치에서 수정.

수정 가능 범위:

- 테스트 실패 → 테스트 코드를 현재 구현에 맞게 수정
- TypeScript 컴파일 에러 → null 체크, 누락 필드 추가
- 린트 에러 → `ruff check . --fix`

수정 금지:

- DB 마이그레이션 (`makemigrations`, `migrate`)
- Neo4j 스키마 변경
- `.env`, `settings.py`, `config/` 수정
- 새로운 기능 추가, 의미적 로직 변경

모든 수정은 `nightly/auto-fix-날짜` 브랜치에서 개별 커밋.

### Phase 3: 수정 검증 (Haiku)

Phase 2에서 수정한 코드에서 테스트/타입/린트를 다시 돌려서
수정 전/후 비교표 생성.

### Phase 4: Codex 크로스 리뷰 (GPT-5-Codex)

Claude 계열과 완전히 다른 모델(OpenAI GPT-5)이 독립적으로 리뷰.

2가지 작업:

1. **diff 리뷰**: Phase 2에서 자동 수정한 diff를 검토
   → SAFE(머지 안전) / CAUTION(수동 확인) / BLOCK(머지 금지) 판정
2. **스팟 리뷰**: 최근 48시간 변경 파일을 P0/P1/P2로 분류
   → 보안, 버그, 성능 이슈 탐지

Codex가 설치되지 않은 환경에서는 자동 스킵 (에러 없음).

---

## 3. 요일별 심층 분석

각 요일마다 서로 다른 관점에서 Stock-Vis를 분석한다.
모든 심층 분석은 Sonnet↔Opus 검증 루프로 실행.

### 주간 스케줄

```
┌────────┬─────────────────────┬──────────────────────────────────────┐
│  요일  │       주제          │            분석 내용                  │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  월    │  UI/UX              │  컴포넌트 일관성 감사                 │
│        │                     │  사용자 플로우 분석                   │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  화    │  데이터 & API       │  FMP API 의존성 감사                  │
│        │                     │  데이터 파이프라인 건강성             │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  수    │  보안 & 성능        │  보안 취약점 스캔                     │
│        │                     │  성능 병목 분석                       │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  목    │  비즈니스 로직      │  4대 필라 기능 완성도 평가            │
│        │                     │  지표 카탈로그 동기화 검증            │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  금    │  아키텍처           │  기술부채 & 진화 제안                  │
│        │                     │  API 응답 일관성 감사                 │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  토    │  전략               │  경쟁 서비스 대비 차별화 분석         │
│        │                     │  Celery Beat 스케줄 감사              │
├────────┼─────────────────────┼──────────────────────────────────────┤
│  일    │  주간 종합          │  전체 요약 + 다음 주 추천 TOP 5       │
└────────┴─────────────────────┴──────────────────────────────────────┘
```

### 각 요일 상세

**월요일 — UI/UX**

- 190개 FE 컴포넌트의 디자인 일관성 (색상, 반응형, 접근성)
- 로딩/에러/빈 상태(empty state) 처리 누락
- Chain Sight 마켓뷰 UX 구현 상태
- 핵심 사용자 플로우 3개 추적 (Dashboard→발견→검증)
- 모바일 터치 인터랙션, API waterfall, 상태 보존

**화요일 — 데이터 & API**

- FMP 엔드포인트 전수 조사, rate limit 시뮬레이션
- 에러 핸들링 현황 (429, timeout, 빈 응답, retry)
- FMP 장애 시 서비스 영향 범위
- 데이터 파이프라인 (EOD, News) 각 단계 실패 영향
- neo4j_dirty 플래그, stale 감지(72h asof), Circuit Breaker

**수요일 — 보안 & 성능**

- 하드코딩된 시크릿, SQL injection, CORS, JWT
- 사용자 입력 검증, DEBUG 설정, 패키지 취약점
- N+1 쿼리, 인덱스 누락, 무거운 직렬화
- FE 번들 크기, 불필요한 API 응답 필드
- 캐싱 필요 지점 식별

**목요일 — 비즈니스 로직**

- 4대 필라별 구현 완성도: ✅ 완료 / 🔨 진행중 / 📋 설계만 / ❌ 미착수
  - Chain Sight: 마켓뷰, 에고그래프, 시드노드, Heat Score, 이벤트 전파
  - EOD Screening: 47개 시그널, static JSON baking
  - News Intelligence: 6단계 파이프라인, MarketAux/Finnhub
  - Thesis Control: Layer A~E 수학 모델, moon-phase 상태
- INDICATOR_CATALOG ↔ KEYWORD_RULES ↔ FE 3곳 동기화

**금요일 — 아키텍처**

- 스케일 시 병목 지점, 마이크로서비스 분리 후보
- 4-layer 데이터 아키텍처 구현도
- 기술 부채 TOP 5 (구체적 파일과 이유)
- Trading bot signal stack 준비도
- DRF API 응답 형식 일관성 매트릭스

**토요일 — 전략**

- Stock-Vis vs 증권사 MTS vs 토스증권 vs TradingView 비교
- "signals first, news second" 철학 반영도
- 한국 시장 특화 부족한 점 (KOSPI/KOSDAQ, 공시, 외국인 매매)
- MVP 출시까지 필요한 최소 기능 목록
- Celery Beat 50+개 태스크 시간 충돌 히트맵

**일요일 — 주간 종합**

- 이번 주 코드 변화/커밋 통계
- 반복 등장한 문제 패턴
- 테스트 커버리지 추세
- 자동 수정 내역 목록
- Opus APPROVED 비율
- 다음 주 추천 작업 TOP 5

---

## 4. Sonnet↔Opus 검증 루프

요일별 심층 분석에 적용되는 품질 보증 메커니즘.

### 동작 원리

```
Round 1
  Sonnet 분석 → draft_R1.md
  Opus 검증   → "근거 부족. 파일명/라인 명시해. FMP 호출 3개 더 있음"

Round 2
  Sonnet 보완 → draft_R2.md (피드백 반영, [R2 추가] 태그)
  Opus 재검증 → "APPROVED ✅"
  → 최종 리포트에 "Opus 4.6 | Round 2/5 | APPROVED" 태그 부착
```

### Opus 승인 기준

- 주장에 구체적 근거(파일명, 라인, 코드 조각)가 있는가
- 누락된 중요 관점이 없는가
- 제안이 Stock-Vis 아키텍처와 현실적으로 맞는가
- 우선순위가 합리적인가

### 5라운드 소진 시

최종 draft에 "수동 확인 필요" 태그가 붙고, 마지막 Opus 피드백을 첨부.
이 경우 아침 리포트에서 ⚠️로 강조 표시.

### 왜 이 구조인가

| 방식             | 장점                    | 단점                         |
| ---------------- | ----------------------- | ---------------------------- |
| Sonnet 단독      | 빠르고 저렴             | 자기 결과를 객관적으로 못 봄 |
| Opus 단독        | 정확                    | 비싸고 느림                  |
| Sonnet→Opus 루프 | Sonnet 속도 + Opus 품질 | 라운드당 비용 증가           |

실사용 기준 대부분 2~3라운드에 APPROVED.

---

## 5. 파일 구조

```
~/stock-vis-nightly/
├── nightly_v2.sh              ← cron 매일 23:00 실행 (메인 스크립트)
├── codex_review_phase.sh      ← Phase 4: Codex 리뷰 (source로 삽입)
├── morning_notify.sh          ← cron 매일 08:00 실행 (알림)
├── install.sh                 ← 최초 설치 스크립트
│
├── work/                      ← Sonnet↔Opus 중간 파일 (임시, 1일 보관)
├── logs/                      ← 실행 로그 (14일 보관)
│   ├── nightly_2026-04-14.log
│   ├── 20260414_phase1.log
│   ├── 20260414_codex.log
│   └── ...
│
└── reports/                   ← 분석 리포트 (14일 보관)
    ├── daily/                 ← 매일 생성
    │   ├── scan_2026-04-14.md         Phase 1 결과
    │   ├── verify_2026-04-14.md       Phase 3 결과
    │   ├── codex_review_2026-04-14.md Phase 4 결과
    │   └── morning_2026-04-14.md      ★ 아침에 이걸 봄
    ├── monday/                ← UI/UX 분석
    ├── tuesday/               ← 데이터/API 분석
    ├── wednesday/             ← 보안/성능 분석
    ├── thursday/              ← 비즈니스 로직 분석
    ├── friday/                ← 아키텍처 분석
    ├── saturday/              ← 전략 분석
    └── weekly/                ← 주간 종합 (일요일)
```

---

## 6. 설치

### 사전 요구사항

- macOS (MacBook, Tailscale로 원격 접속 가능)
- Claude Code 설치: `npm i -g @anthropic-ai/claude-code`
- Claude 인증 완료 (Pro 또는 Max 구독, 또는 API 키)
- Git 초기화된 Stock-Vis 프로젝트

### 설치 순서

```bash
# 1. 파일 복사
mkdir -p ~/stock-vis-nightly
# 다운받은 파일들을 ~/stock-vis-nightly/ 에 배치

# 2. 프로젝트 경로 확인
#    nightly_v2.sh 상단의 PROJECT_DIR 수정
nano ~/stock-vis-nightly/nightly_v2.sh
#    PROJECT_DIR="$HOME/stock-vis"  ← 실제 경로

# 3. 실행 권한
chmod +x ~/stock-vis-nightly/*.sh

# 4. 디렉토리 생성
mkdir -p ~/stock-vis-nightly/{reports/{daily,monday,tuesday,wednesday,thursday,friday,saturday,sunday,weekly},logs,work}

# 5. crontab 등록
crontab -e
```

crontab에 추가할 내용:

```cron
# Stock-Vis 야간 자동화 시스템
0 23 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/nightly_v2.sh >> ~/stock-vis-nightly/logs/cron.log 2>&1
0  8 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/morning_notify.sh >> ~/stock-vis-nightly/logs/cron_morning.log 2>&1
```

### Codex 추가 설치 (선택)

```bash
# Codex CLI 설치
npm i -g @openai/codex

# 인증 (택 1)
codex auth login                          # ChatGPT 계정 연동
# 또는
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc

# nightly_v2.sh Phase 3 뒤에 삽입
# source "$SYSTEM_DIR/codex_review_phase.sh"
```

Codex 미설치 시 Phase 4는 자동 스킵. 나머지에 영향 없음.

---

## 7. 일상 사용

### 자기 전 — 아무것도 안 해도 됨

cron이 매일 23:00에 자동 실행.
MacBook이 켜져 있고 잠자기 모드가 아니면 됨.

잠자기 방지:

```bash
# macOS 잠자기 비활성화 (AC 전원 시)
sudo pmset -c sleep 0 displaysleep 10
```

### 아침 루틴 (5~10분)

```bash
# 1. 아침 리포트 읽기
cat ~/stock-vis-nightly/reports/daily/morning_$(date +%Y-%m-%d).md

# 2. 오늘 요일 심층 분석 보기
ls ~/stock-vis-nightly/reports/$(date +%A | tr '[:upper:]' '[:lower:]')/
cat ~/stock-vis-nightly/reports/monday/component_consistency_$(date +%Y-%m-%d).md

# 3. 자동 수정 diff 확인
cd ~/stock-vis
git diff main..nightly/auto-fix-$(date +%Y-%m-%d)

# 4. 괜찮으면 머지
git merge nightly/auto-fix-$(date +%Y-%m-%d)

# 5. Codex 리뷰가 BLOCK이면 수정 안 함
cat ~/stock-vis-nightly/reports/daily/codex_review_$(date +%Y-%m-%d).md
```

### 유용한 명령어

```bash
# 실행 중 로그 실시간 보기 (Tailscale 원격 접속 시)
tail -f ~/stock-vis-nightly/logs/nightly_$(date +%Y-%m-%d).log

# 지난주 리포트 모아보기
ls -la ~/stock-vis-nightly/reports/weekly/

# cron 등록 확인
crontab -l

# 수동 실행 (테스트)
~/stock-vis-nightly/nightly_v2.sh

# 실행 중 멈추기
ps aux | grep nightly_v2
kill <PID>
```

---

## 8. 비용

### 구독 플랜 사용 시

| 항목          | 비용        | 비고                                       |
| ------------- | ----------- | ------------------------------------------ |
| Claude Max 5x | $100/월     | Phase 1~3 + 요일별 + 아침 리포트 전부 포함 |
| ChatGPT Plus  | $20/월      | Codex 리뷰 포함                            |
| **합계**      | **$120/월** | **추가 비용 없음**                         |

### API 종량제 사용 시

| 항목                                           | 일 비용    | 월 비용   |
| ---------------------------------------------- | ---------- | --------- |
| 매일 작업 (Haiku+Sonnet+Haiku)                 | $0.74      | $22       |
| Codex 크로스 리뷰                              | $0.30      | $9        |
| 요일별 심층 분석 (Sonnet↔Opus, 평균 2.5라운드) | $2.50      | $75       |
| 아침 리포트 (Opus)                             | $0.50      | $15       |
| **합계**                                       | **~$4.04** | **~$121** |

변경 없는 날은 Phase 2 스킵, 심층 분석 라운드 감소로 더 저렴.

### 비용 절약 팁

- Max 구독이 API보다 거의 항상 이득 (동일 비용에 10배 이상 사용)
- 요일별 분석에서 라운드 수 제한 (MAX_LOOP_ROUNDS=3으로 줄이기)
- 주말 심층 분석 스킵 (`토/일`을 읽기 전용 감사만으로 변경)

---

## 9. 안전장치

### 코드 보호

- 모든 수정은 `nightly/auto-fix-날짜` 브랜치에서 실행 (main 직접 수정 없음)
- DB 마이그레이션 절대 실행 안 함
- Neo4j 스키마 변경 없음
- `.env`, `settings.py` 수정 없음
- 7일 이전 nightly 브랜치 자동 삭제

### 실행 보호

- lockfile로 중복 실행 방지
- 커밋 안 된 변경사항 자동 stash → 완료 후 복원
- Codex 미설치 시 해당 Phase만 스킵
- 14일 이전 로그/리포트 자동 정리

### 크로스 체크

- Codex(GPT-5)가 Claude 수정의 안전성을 독립 판단
  - SAFE: 머지 추천
  - CAUTION: 수동 확인 후 머지
  - BLOCK: 머지 금지
- Opus가 Sonnet 분석을 검증 (최대 5라운드)
- 5라운드 소진 시 "수동 확인 필요" 태그

---

## 10. 알림 설정

### macOS 네이티브 알림 (기본, 설정 불필요)

아침 8시에 알림 팝업 + 터미널에서 리포트 자동 표시.

### Slack (선택)

```bash
# 1. api.slack.com/messaging/webhooks 에서 Incoming Webhook 생성
# 2. morning_notify.sh에서 SLACK_WEBHOOK 입력
SLACK_WEBHOOK="https://hooks.slack.com/services/T.../B.../xxx"
```

### Discord (선택)

```bash
# 1. 서버 설정 → 연동 → 웹후크 → 새 웹후크
# 2. morning_notify.sh에서 DISCORD_WEBHOOK 입력
DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
```

### HTML 리포트 (기본)

매일 아침 브라우저에서 자동으로 리포트 HTML 열림.
다크 테마, 테이블, 체크박스 포함.

---

## 11. 중단/제거

```bash
# 스케줄만 중단
crontab -e
# → stock-vis 관련 줄 삭제 또는 주석(#) 처리

# 완전 제거
crontab -e    # 줄 삭제
rm -rf ~/stock-vis-nightly

# 남은 nightly 브랜치 정리
cd ~/stock-vis
git branch --list 'nightly/*' | xargs git branch -D
```

---

## 12. 트러블슈팅

### cron이 실행 안 될 때

```bash
# macOS 보안 설정에서 cron에 디스크 접근 권한 필요
# 시스템 환경설정 → 보안 → 전체 디스크 접근 → /usr/sbin/cron 추가

# PATH 문제 확인
# crontab에 PATH를 명시적으로 지정했는지 확인
```

### Claude Code 인증 만료

```bash
# 재인증
claude auth login
# 또는 API 키 확인
echo $ANTHROPIC_API_KEY
```

### 특정 Phase만 다시 실행

```bash
# 해당 날짜 브랜치 삭제 후 재실행
git branch -D nightly/auto-fix-$(date +%Y-%m-%d)
~/stock-vis-nightly/nightly_v2.sh
# (이미 존재하는 브랜치는 자동 스킵되므로
#  삭제한 Phase만 재실행됨)
```

### MacBook 잠자기로 중단됨

```bash
# AC 전원 시 잠자기 비활성화
sudo pmset -c sleep 0 displaysleep 10

# 또는 tmux 사용
tmux new -s nightly
~/stock-vis-nightly/nightly_v2.sh
# Ctrl+B, D로 빠져나오기
```

---

## 부록: 아침 리포트 예시

```markdown
# ☀️ Stock-Vis 아침 리포트 — 2026-04-14 (Monday)

## 한눈에 보기

| 항목       | 상태 | 상세                 |
| ---------- | ---- | -------------------- |
| 테스트     | 🟢   | 549 passed, 0 failed |
| TypeScript | 🟡   | 2개 에러 (수정됨)    |
| 린트       | 🟢   | 경고 3개             |
| 야간 수정  | ✅   | 2개 커밋             |
| Codex 판정 | SAFE | 머지 추천            |

## 🔧 야간 자동 수정

- nightly-fix: mock.ts description 필드 추가
- nightly-fix: NewsCard null 체크 추가

## 🔍 Codex 크로스 리뷰

- diff 안전성: SAFE
- 추가 발견: 없음

## 🔬 오늘의 심층 분석: UI/UX

- 컴포넌트 일관성: 190개 중 12개에서 색상 하드코딩 발견
- 사용자 플로우: Chain Sight→1차 검증 전환 시 API 3회 호출 (최적화 가능)
- Opus 검증: APPROVED (Round 2/5)

## ⚠️ 즉시 조치 필요

- 없음

## 💡 이번 주 제안

1. Chain Sight 마켓뷰 시드 노드 로직 구현 착수
2. validation 앱 테스트 40개 작성
3. FMP rate limit 분산을 위한 Beat 스케줄 조정

## 📋 오늘 할 일

- [ ] git diff main..nightly/auto-fix-2026-04-14 확인 후 머지
- [ ] reports/monday/component_consistency 읽고 색상 하드코딩 12곳 확인
```
