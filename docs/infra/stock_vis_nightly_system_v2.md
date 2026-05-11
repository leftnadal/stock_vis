# Stock-Vis 야간 자율 에이전트 시스템 — 최종 운영 문서

> 작성: 2026-04-14 | 버전: v2.1  
> 기준 브랜치: data_structure_remodeling_V1

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [현황 요약](#2-현황-요약)
3. [매일 실행 작업 (Phase 1~4)](#3-매일-실행-작업)
4. [요일별 심층 분석 스케줄](#4-요일별-심층-분석-스케줄)
5. [Sonnet↔Opus 검증 루프](#5-sonnetopus-검증-루프)
6. [전체 작업 인덱스 (21개)](#6-전체-작업-인덱스)
7. [1회성 작업 실행 계획](#7-1회성-작업-실행-계획)
8. [야간 시스템 매핑](#8-야간-시스템-매핑)
9. [파일 구조](#9-파일-구조)
10. [설치 가이드](#10-설치-가이드)
11. [일상 운영](#11-일상-운영)
12. [비용](#12-비용)
13. [안전장치](#13-안전장치)
14. [알림 설정](#14-알림-설정)
15. [트러블슈팅](#15-트러블슈팅)
16. [제약 조건](#16-제약-조건)
17. [부록: 작업 상세 (21개)](#17-부록-작업-상세)

---

## 1. 시스템 개요

### 핵심 아이디어

개발자가 자는 동안 4개의 AI 모델이 역할을 나눠서 Stock-Vis를 다각도로 분석한다.
코드 품질뿐 아니라 서비스 전략, UX, 보안, 데이터 건강성까지 커버한다.
아침에 일어나면 종합 리포트 하나만 읽으면 된다.

### 사용 모델과 역할

| 모델        | 역할                              | 특성                  |
| ----------- | --------------------------------- | --------------------- |
| Haiku 4.5   | 스캔, 테스트 실행, 빠른 검증      | 빠르고 저렴           |
| Sonnet 4.6  | 코드 수정, 심층 분석 초안         | 균형 (코드 작성 능력) |
| Opus 4.6    | 검증/비판, 전략 판단, 최종 리포트 | 최고 추론력           |
| GPT-5-Codex | Claude blind spot 크로스 체크     | 다른 모델 계열        |

### 전체 실행 흐름

```
밤 23:00 시작
│
├─ [매일] 코드 건강성 체크
│   ├── Phase 1: 코드 스캔 ─────────── Haiku ───── ~5분
│   ├── Phase 2: 자동 수정 ─────────── Sonnet ──── ~15분
│   ├── Phase 3: 수정 검증 ─────────── Haiku ───── ~5분
│   └── Phase 4: Codex 크로스 리뷰 ── GPT-5 ───── ~10분
│
├─ [요일별] 심층 분석
│   └── Sonnet↔Opus 검증 루프 (최대 5라운드) ──── ~30분
│
├─ 아침 리포트 통합 ────────────────── Opus ────── ~10분
│
│                                      총 ~75분
▼
아침 08:00 알림
├── macOS 알림 팝업
├── HTML 리포트 브라우저 자동 열기
└── Slack 메시지 (선택)
```

---

## 2. 현황 요약

| 항목               | 수치                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------- |
| 총 테스트          | 1,693개 (549 passed, 1 failed, 4 errors)                                               |
| 테스트 0개 앱      | validation (3,457줄), sec_pipeline (3,466줄), rag_analysis (14,608줄), users (2,820줄) |
| TS 컴파일 에러     | 4개                                                                                    |
| FE 컴포넌트        | 190개 / 테스트 0개 (Vitest/RTL 미설치)                                                 |
| 기존 테스트 실패   | 1 FAILED (news) + 4 ERROR (serverless)                                                 |
| Celery Beat 스케줄 | 50+ 항목                                                                               |
| API 문서 자동생성  | 미설정 (drf-spectacular/Swagger 없음)                                                  |
| Circuit Breaker    | 0건                                                                                    |
| Gemini fallback    | 1건만                                                                                  |
| FK 관계            | 63개, select_related 20건 vs QuerySet 접근 195건                                       |
| 설계 문서          | 59개 plan, 68개 task_done                                                              |

---

## 3. 매일 실행 작업

### Phase 1: 코드 스캔 (Haiku)

테스트, 타입 체크, 린트를 빠르게 돌려서 현재 상태를 파악한다.

실행 항목:

- `pytest tests/ -q --tb=line`
- `cd frontend && npx tsc --noEmit`
- `ruff check . --statistics`
- 최근 24시간 커밋 목록

결과: 🟢 정상 / 🟡 주의 / 🔴 문제 있음

### Phase 2: 자동 수정 (Sonnet)

Phase 1에서 발견된 문제 중 안전하게 수정 가능한 것만 별도 브랜치에서 수정한다.

수정 가능 범위:

- 테스트 실패 → 테스트 코드를 현재 구현에 맞게 수정
- TypeScript 컴파일 에러 → null 체크, 누락 필드 추가
- 린트 에러 → `ruff check . --fix`

수정 금지:

- DB 마이그레이션, Neo4j 스키마 변경
- `.env`, `settings.py`, `config/` 수정
- 새로운 기능 추가, 의미적 로직 변경

모든 수정은 `nightly/auto-fix-날짜` 브랜치에서 개별 커밋.

### Phase 3: 수정 검증 (Haiku)

Phase 2에서 수정한 코드를 재검증하고 수정 전/후 비교표를 생성한다.

### Phase 4: Codex 크로스 리뷰 (GPT-5-Codex)

Claude와 완전히 다른 모델 계열(OpenAI)이 독립적으로 리뷰한다.

2가지 작업:

- **diff 리뷰**: Phase 2 자동 수정의 안전성 판정 (SAFE / CAUTION / BLOCK)
- **스팟 리뷰**: 최근 48시간 변경 파일을 P0/P1/P2로 분류

Codex가 설치되지 않은 환경에서는 자동 스킵.

---

## 4. 요일별 심층 분석 스케줄

모든 심층 분석은 Sonnet↔Opus 검증 루프로 실행된다.

### 주간 스케줄 총괄

| 요일 | 주제          | 분석 항목                                        | 관련 작업         |
| :--: | ------------- | ------------------------------------------------ | ----------------- |
|  월  | UI/UX         | 컴포넌트 일관성, 사용자 플로우, 모바일 UX        | #18               |
|  화  | 데이터 & API  | FMP/Gemini 장애 대응, 데이터 무결성, FK orphan   | #17, #14          |
|  수  | 보안 & 성능   | OWASP 보안 스캔, N+1 쿼리, 인덱스 누락           | #16, #15          |
|  목  | 비즈니스 로직 | 4대 필라 기능 완성도, 설계서 갭, 카탈로그 동기화 | #19-A, #19-B, #10 |
|  금  | 아키텍처      | 기술부채, API 일관성, API 문서 자동생성 현황     | #9, #20           |
|  토  | 전략          | 경쟁 분석, Beat 스케줄 감사, 나머지 설계서 갭    | #6, #19-C         |
|  일  | 주간 종합     | 전체 요약 + 다음 주 추천 TOP 5                   | —                 |

### 월요일 — UI/UX

- 190개 FE 컴포넌트의 디자인 일관성 (색상, 반응형, 접근성)
- 로딩/에러/빈 상태 처리 누락 컴포넌트
- Chain Sight 마켓뷰 UX (노드 클릭→중심이동→좌측히스토리)
- 핵심 사용자 플로우 3개 추적 (Dashboard→발견→1차 검증→Thesis Control)
- 모바일 반응형: 고정 폭 26건 식별, 터치 타겟 44x44pt 검증
- Recharts 모바일 대응, virtualization 적용 여부

### 화요일 — 데이터 & API

- FMP 엔드포인트 전수 조사, rate limit 시뮬레이션 (Starter 10/min)
- 에러 핸들링 현황: 429, timeout, 빈 응답, retry (현재 fallback 0건)
- Circuit breaker 미구현 현황 및 도입 후보
- FK orphan 위험: on_delete=SET_NULL 후 정리 로직 존재 여부
- Neo4j↔PostgreSQL 동기화: signals/tasks 실패 시 재시도 메커니즘
- 시계열 데이터 보존 정책, stale 감지 (72h asof 기반)

### 수요일 — 보안 & 성능

- OWASP Top 10 기반: 인증/인가, 인젝션, 시크릿, CORS/XSS, 에러 노출
- raw SQL 4건 파라미터 바인딩 확인
- Gemini 프롬프트에 사용자 입력 직접 삽입 여부 (프롬프트 인젝션)
- N+1 쿼리: QuerySet 195건 vs select_related 20건 (비율 10:1)
- 인덱스 누락: filter/order_by 필드 중 db_index 없는 것
- SerializerMethodField 추가 쿼리, 페이지네이션 누락

### 목요일 — 비즈니스 로직

- 4대 필라별 구현 완성도 (✅/🔨/📋/❌)
  - Chain Sight: 마켓뷰, 에고그래프, 시드노드, Heat Score, 이벤트 전파
  - EOD Screening: 47개 시그널, static JSON baking
  - News Intelligence: 6단계 파이프라인, MarketAux/Finnhub
  - Thesis Control: Layer A~E 수학 모델, moon-phase 상태
- Chain Sight 설계 26개 vs 코드 갭 (#19-A)
- Thesis Control 설계 vs 코드 갭 (#19-B)
- INDICATOR_CATALOG ↔ KEYWORD_RULES ↔ FE 3곳 동기화 (#10)

### 금요일 — 아키텍처

- 기술부채 TOP 5, 스케일 병목, 마이크로서비스 분리 후보
- 4-layer 데이터 아키텍처 구현도
- DRF API 응답 형식 일관성 매트릭스 (#9)
- API 문서 자동생성 현황: drf-spectacular 미설정, 엔드포인트 수 (#20)
- Trading bot signal stack 준비도

### 토요일 — 전략

- Stock-Vis vs 증권사 MTS vs 토스증권 vs TradingView 비교
- "signals first, news second" 철학 반영도
- 한국 시장 특화 부족한 점 (KOSPI/KOSDAQ, 공시, 외국인 매매)
- MVP 출시까지 필요한 최소 기능 목록
- Celery Beat 50+개 태스크 시간 충돌 히트맵 (#6)
- SEC Pipeline + 나머지 설계서 갭 (#19-C)

### 일요일 — 주간 종합

- 이번 주 코드 변화/커밋 통계
- 반복 등장한 문제 패턴
- 테스트 커버리지 추세
- 자동 수정 내역 총괄
- Opus APPROVED 비율
- 다음 주 추천 작업 TOP 5

---

## 5. Sonnet↔Opus 검증 루프

요일별 심층 분석의 품질을 보증하는 핵심 메커니즘.

### 동작 원리

```
Round 1
  Sonnet 분석 → draft_R1.md
  Opus 검증   → "근거 부족. 파일명/라인 명시해라"

Round 2
  Sonnet 보완 → draft_R2.md (피드백 반영, [R2 추가] 태그)
  Opus 재검증 → "APPROVED ✅"
  → 최종 리포트에 "Opus 4.6 | Round 2/5 | APPROVED" 태그

(최대 5라운드, 대부분 2~3라운드에 APPROVED)
```

### Opus 승인 기준

- 주장에 구체적 근거(파일명, 라인, 코드 조각)가 있는가
- 누락된 중요 관점이 없는가
- 제안이 Stock-Vis 아키텍처와 현실적으로 맞는가
- 우선순위가 합리적인가

### 5라운드 소진 시

최종 draft에 "수동 확인 필요" 태그가 붙고, 마지막 Opus 피드백을 첨부한다.
아침 리포트에서 ⚠️로 강조 표시.

---

## 6. 전체 작업 인덱스 (21개)

| #    | 작업명                                   | 유형        | 관점          | 리스크 |
| ---- | ---------------------------------------- | ----------- | ------------- | :----: |
| 1    | TS 컴파일 에러 수정                      | 코드 수정   | 타입 안전성   |  LOW   |
| 2    | 깨진 테스트 수정                         | 코드 수정   | 테스트        |  LOW   |
| 3    | validation 테스트 작성 (0→40개)          | 테스트 신규 | BE 커버리지   |  LOW   |
| 4    | sec_pipeline 테스트 작성 (0→30개)        | 테스트 신규 | BE 커버리지   |  LOW   |
| 5    | users 테스트 작성 (0→25개)               | 테스트 신규 | BE 커버리지   |  LOW   |
| 6    | Beat 스케줄 감사                         | 감사        | 인프라        |  LOW   |
| 7    | FE 타입 안전성 강화                      | 코드 수정   | 타입 안전성   |  LOW   |
| 8    | Dead code / unused import 정리           | 코드 수정   | 코드 품질     |  MED   |
| 9    | API 응답 일관성 감사                     | 감사        | 아키텍처      |  LOW   |
| 10   | INDICATOR_CATALOG 동기화 검증            | 감사        | 비즈니스 로직 |  LOW   |
| 11   | FE thesis 컴포넌트 테스트 (0→15개)       | 테스트 신규 | FE 커버리지   |  LOW   |
| 12   | FE validation+chainsight 테스트 (0→18개) | 테스트 신규 | FE 커버리지   |  LOW   |
| 13   | rag_analysis 최소 테스트 (0→35개)        | 테스트 신규 | BE 커버리지   |  LOW   |
| 14   | 데이터 무결성 감사                       | 감사        | 데이터        |  LOW   |
| 15   | API 성능 감사                            | 감사        | 성능          |  LOW   |
| 16   | 보안 감사 (OWASP)                        | 감사        | 보안          |  LOW   |
| 17   | FMP/Gemini 장애 대응 감사                | 감사        | 외부 의존성   |  LOW   |
| 18   | 모바일 UX 감사                           | 감사        | UX            |  LOW   |
| 19-A | Chain Sight 설계서 갭                    | 감사        | 설계 vs 구현  |  LOW   |
| 19-B | Thesis Control 설계서 갭                 | 감사        | 설계 vs 구현  |  LOW   |
| 19-C | SEC Pipeline + 나머지 설계서 갭          | 감사        | 설계 vs 구현  |  LOW   |
| 20   | API 문서 자동생성 감사                   | 감사        | 문서화        |  LOW   |

---

## 7. 1회성 작업 실행 계획

야간 시스템 가동 전에 한번만 수행하는 작업들.

### Tier 1: 즉시 수정 (머지 가능, 총 ~45분)

| 작업              | 소요 | 실행 명령                                                    |
| ----------------- | :--: | ------------------------------------------------------------ |
| #1 TS 컴파일 에러 | 5분  | `git checkout -b fix/ts-compile-errors && claude -p "..."`   |
| #2 깨진 테스트    | 15분 | `git checkout -b fix/broken-tests && claude -p "..."`        |
| #7 FE 타입 안전성 | 10분 | `git checkout -b fix/fe-type-safety && claude -p "..."`      |
| #8 Dead code 정리 | 15분 | `git checkout -b chore/dead-code-cleanup && claude -p "..."` |

### Tier 2: 테스트 확보 (0 → 163+개, 총 ~130분)

| 작업                                | 소요 | 선행 조건         | 테스트 증가 |
| ----------------------------------- | :--: | ----------------- | ----------- |
| **수동**: FE 테스트 인프라 설치     | 5분  | —                 | —           |
| #3 validation 테스트                | 30분 | 마이그레이션 완료 | 0→40        |
| #4 sec_pipeline 테스트              | 25분 | 마이그레이션 완료 | 0→30        |
| #5 users 테스트                     | 20분 | —                 | 0→25        |
| #13 rag_analysis 테스트             | 25분 | —                 | 0→35        |
| #11 FE thesis 테스트                | 25분 | FE 인프라 설치    | 0→15        |
| #12 FE validation+chainsight 테스트 | 20분 | FE 인프라 설치    | 0→18        |

FE 테스트 인프라 수동 설치:

```bash
cd frontend
npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom
# + vitest.config.ts 생성
```

### Tier 3: 감사 보고서 (읽기 전용, 브랜치 불필요, 병렬 실행 가능)

| 작업                        | 소요 | 산출물                        |
| --------------------------- | :--: | ----------------------------- |
| #15 API 성능 감사           | 20분 | N+1 위험 엔드포인트 목록      |
| #16 보안 감사               | 20분 | OWASP 취약점 보고서           |
| #17 FMP/Gemini 장애 대응    | 15분 | 의존성 매트릭스 + fallback 갭 |
| #14 데이터 무결성 감사      | 15분 | orphan 위험 + 동기화 갭       |
| #19-A Chain Sight 설계서 갭 | 15분 | 26개 설계서 구현률            |
| #6 Beat 스케줄 감사         | 10분 | API 호출 히트맵               |
| #20 API 문서 감사           | 10분 | 엔드포인트 수 + 도입 플랜     |

### 추천 실행 순서 (오늘 밤)

```bash
# 스크립트 하나로 Tier 1 + Tier 2(BE) 순차 실행
nohup ~/stock-vis-nightly/run_tonight.sh > ~/tonight.log 2>&1 &

# 또는 tmux로
tmux new -s tonight
~/stock-vis-nightly/run_tonight.sh
# Ctrl+B, D
```

---

## 8. 야간 시스템 매핑

1회성 작업 이후, 매일/매주 자동으로 실행되는 매핑.

### 매일 자동 (Phase 1~4)

| Phase | 모델        | 관련 작업       | 하는 일                                    |
| :---: | ----------- | --------------- | ------------------------------------------ |
|   1   | Haiku       | #1, #2, #7 유형 | 코드 스캔 (pytest, tsc, ruff)              |
|   2   | Sonnet      | —               | 발견된 문제 자동 수정 → 별도 브랜치        |
|   3   | Haiku       | —               | 수정 결과 검증                             |
|   4   | GPT-5-Codex | —               | diff 리뷰 (SAFE/CAUTION/BLOCK) + 스팟 리뷰 |

### 요일별 심층 분석

```
월 (UI/UX):
  #18 모바일 반응형 감사
  컴포넌트 일관성 + 사용자 플로우 분석

화 (데이터/API):
  #17 FMP/Gemini 장애 대응 감사
  #14 데이터 무결성 (FK orphan + Neo4j-PG 동기화)

수 (보안/성능):
  #16 OWASP 보안 감사
  #15 API 성능 (N+1 쿼리 + 인덱스)

목 (비즈니스 로직):
  #19-A Chain Sight 설계서 갭
  #19-B Thesis Control 설계서 갭
  #10 카탈로그 동기화 검증

금 (아키텍처):
  #9 API 응답 일관성 감사
  #20 API 문서 자동생성 감사

토 (전략):
  #6 Beat 스케줄 감사
  #19-C SEC Pipeline + 나머지 설계서 갭
  경쟁 서비스 분석

일 (주간 종합):
  전체 요약 + 다음 주 추천 TOP 5
```

---

## 9. 파일 구조

```
~/stock-vis-nightly/
├── nightly_v2.sh              ← cron 매일 23:00 실행 (메인)
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
    │   ├── scan_2026-04-14.md
    │   ├── verify_2026-04-14.md
    │   ├── codex_review_2026-04-14.md
    │   └── morning_2026-04-14.md      ★ 아침에 이걸 읽음
    ├── monday/                ← UI/UX
    ├── tuesday/               ← 데이터/API
    ├── wednesday/             ← 보안/성능
    ├── thursday/              ← 비즈니스 로직
    ├── friday/                ← 아키텍처
    ├── saturday/              ← 전략
    └── weekly/                ← 주간 종합 (일요일)
```

---

## 10. 설치 가이드

### 사전 요구사항

- macOS (MacBook, Tailscale로 원격 접속 가능한 환경)
- Claude Code: `npm i -g @anthropic-ai/claude-code`
- Claude 인증 완료 (Pro/Max 구독 또는 API 키)
- Git 초기화된 Stock-Vis 프로젝트

### 설치 순서

```bash
# 1. 파일 배치
mkdir -p ~/stock-vis-nightly
# 다운받은 파일들을 ~/stock-vis-nightly/ 에 복사

# 2. 프로젝트 경로 확인
nano ~/stock-vis-nightly/nightly_v2.sh
# PROJECT_DIR="$HOME/stock-vis"  ← 실제 경로로 수정

# 3. 실행 권한
chmod +x ~/stock-vis-nightly/*.sh

# 4. 디렉토리 생성
mkdir -p ~/stock-vis-nightly/{reports/{daily,monday,tuesday,wednesday,thursday,friday,saturday,sunday,weekly},logs,work}

# 5. crontab 등록
crontab -e
```

crontab에 추가:

```cron
# Stock-Vis 야간 자동화 시스템 v2
0 23 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/nightly_v2.sh >> ~/stock-vis-nightly/logs/cron.log 2>&1
0  8 * * * PATH=/usr/local/bin:/opt/homebrew/bin:$PATH ~/stock-vis-nightly/morning_notify.sh >> ~/stock-vis-nightly/logs/cron_morning.log 2>&1
```

### Codex 추가 설치 (선택)

```bash
npm i -g @openai/codex
codex auth login                    # ChatGPT 계정 연동
# 또는
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
```

nightly_v2.sh Phase 3 뒤에 삽입:

```bash
source "$SYSTEM_DIR/codex_review_phase.sh"
```

Codex 미설치 시 Phase 4만 자동 스킵. 나머지 영향 없음.

---

## 11. 일상 운영

### 자기 전 — 아무것도 안 해도 됨

cron이 매일 23:00에 자동 실행.
MacBook이 켜져 있고 잠자기 모드가 아니면 됨.

잠자기 방지: `sudo pmset -c sleep 0 displaysleep 10`

### 아침 루틴 (5~10분)

```bash
# 1. 아침 리포트 읽기
cat ~/stock-vis-nightly/reports/daily/morning_$(date +%Y-%m-%d).md

# 2. 오늘 요일 심층 분석 보기
cat ~/stock-vis-nightly/reports/$(date +%A | tr '[:upper:]' '[:lower:]')/*_$(date +%Y-%m-%d).md

# 3. 자동 수정 diff 확인
cd ~/stock-vis
git diff main..nightly/auto-fix-$(date +%Y-%m-%d)

# 4. Codex 판정 확인
cat ~/stock-vis-nightly/reports/daily/codex_review_$(date +%Y-%m-%d).md

# 5. 괜찮으면 머지
git merge nightly/auto-fix-$(date +%Y-%m-%d)
```

---

## 12. 비용

### 구독 플랜 사용 시

| 항목          | 비용    | 비고                                       |
| ------------- | ------- | ------------------------------------------ |
| Claude Max 5x | $100/월 | Phase 1~3 + 요일별 + 아침 리포트 전부 포함 |
| ChatGPT Plus  | $20/월  | Codex 리뷰 포함                            |
| 합계          | $120/월 | 추가 비용 없음 (사용량 한도 내)            |

### API 종량제 사용 시

| 항목                                           | 일 비용 | 월 비용 |
| ---------------------------------------------- | ------- | ------- |
| 매일 작업 (Haiku+Sonnet+Haiku)                 | $0.74   | $22     |
| Codex 크로스 리뷰                              | $0.30   | $9      |
| 요일별 심층 분석 (Sonnet↔Opus, 평균 2.5라운드) | $2.50   | $75     |
| 아침 리포트 (Opus)                             | $0.50   | $15     |
| 합계                                           | ~$4.04  | ~$121   |

변경 없는 날은 Phase 2 스킵, 심층 분석 라운드 감소로 더 저렴.

---

## 13. 안전장치

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

- Codex(GPT-5)가 Claude 수정의 안전성을 독립 판단 (SAFE/CAUTION/BLOCK)
- Opus가 Sonnet 분석을 검증 (최대 5라운드)
- 5라운드 소진 시 "수동 확인 필요" 태그

---

## 14. 알림 설정

### macOS 네이티브 알림 (기본, 설정 불필요)

아침 8시에 알림 팝업 + 터미널에서 리포트 자동 표시.

### Slack (선택)

`morning_notify.sh`에서 `SLACK_WEBHOOK="https://hooks.slack.com/..."` 입력.

### Discord (선택)

`morning_notify.sh`에서 `DISCORD_WEBHOOK="https://discord.com/api/..."` 입력.

### HTML 리포트 (기본)

매일 아침 브라우저에서 리포트 HTML 자동 열림. 다크 테마 적용.

---

## 15. 트러블슈팅

### cron이 실행 안 될 때

macOS 보안 설정에서 cron에 전체 디스크 접근 권한 부여 필요.
시스템 환경설정 → 보안 → 전체 디스크 접근 → `/usr/sbin/cron` 추가.

### Claude Code 인증 만료

```bash
claude auth login
```

### 특정 작업만 재실행

```bash
git branch -D nightly/auto-fix-$(date +%Y-%m-%d)
~/stock-vis-nightly/nightly_v2.sh
```

### MacBook 잠자기로 중단

```bash
sudo pmset -c sleep 0 displaysleep 10
# 또는 tmux 사용
tmux new -s nightly
~/stock-vis-nightly/nightly_v2.sh
```

### 중단/제거

```bash
crontab -e    # stock-vis 관련 줄 삭제
rm -rf ~/stock-vis-nightly
git branch --list 'nightly/*' | xargs git branch -D
```

---

## 16. 제약 조건

| 항목            | 제약                                                           |
| --------------- | -------------------------------------------------------------- |
| DB 마이그레이션 | `makemigrations`, `migrate` 자율 실행 금지                     |
| Neo4j 스키마    | 변경 자율 실행 금지                                            |
| FMP API         | rate limit 고려 (Starter $29: 10 calls/min)                    |
| 시크릿          | `.env`, `settings.py` 수정 금지                                |
| 브랜치          | 모든 코드 수정은 별도 브랜치에서 실행                          |
| 모델            | Agent Teams에서 역할별 모델 분리 미지원 (Bash 스크립트로 우회) |

---

## 17. 부록: 작업 상세 (21개)

### 작업 1: TS 컴파일 에러 수정

대상: `frontend/lib/thesis/mock.ts`, `frontend/components/news/NewsCard.tsx`
실행: 서브에이전트 (`@frontend`)
검증: `cd frontend && npx tsc --noEmit` 에러 0

```
frontend/lib/thesis/mock.ts의 MOCK_DASHBOARD 지표 3개에
description: '', recommendation_reason: '' 추가.
frontend/components/news/NewsCard.tsx의 article.image_url
타입을 string | null에서 non-null assertion 또는 조건부 처리.
npx tsc --noEmit으로 검증.
```

### 작업 2: 깨진 테스트 수정

대상: `tests/news/test_collect_category_news.py`, `tests/serverless/test_keyword_service.py`
실행: 서브에이전트 (`@qa-architect`)
검증: `pytest tests/ -q --tb=short` 전체 통과

```
pytest에서 5건 실패/에러 수정.
(1) test_collect_category_news_by_id — FAILED 원인 분석 후 수정.
(2) test_keyword_service.py 4건 ERROR — import/fixture 누락 확인.
소스 코드 변경 최소화. 테스트 코드를 현재 구현에 맞게 수정.
```

### 작업 3: validation 테스트 (0→40개)

대상: `validation/services/` (peer_engine, preset_generator, benchmark)
실행: `claude -p` headless
검증: `pytest tests/unit/validation/ -v` 40+개 통과

```
validation/ 앱의 단위 테스트를 tests/unit/validation/ 에 작성.
패턴: pytest 클래스, @pytest.mark.django_db, FMP는 mock.
기존 tests/unit/thesis/ 스타일 참조. 최소 40개.
```

### 작업 4: sec_pipeline 테스트 (0→30개)

대상: `sec_pipeline/services/` (edgar_client, extractor), `models.py`
실행: `claude -p` headless
검증: `pytest tests/unit/sec_pipeline/ -v` 30+개 통과

```
sec_pipeline/ 앱의 단위 테스트 작성. HTTP 호출 mock. 최소 30개.
```

### 작업 5: users 테스트 (0→25개)

대상: JWT 인증, Portfolio CRUD, Watchlist
실행: `claude -p` headless
검증: `pytest tests/unit/users/ -v` 25+개 통과

```
users/ 앱의 단위 테스트 작성. APIClient로 API 테스트. 최소 25개.
```

### 작업 6: Beat 스케줄 감사

대상: `config/celery.py` (읽기 전용)
실행: 서브에이전트 (`@infra`)
산출물: `docs/infra/beat_schedule_audit.md`

```
beat_schedule 50+개 항목의 시간 충돌 + FMP/Gemini rate limit 위반 분석.
시간대별 API 호출 히트맵 포함.
```

### 작업 7: FE 타입 안전성 강화

대상: `frontend/components/`, `frontend/lib/`
실행: `claude -p` 1회
검증: `npx tsc --noEmit` exit code 0

```
npx tsc --noEmit 에러 목록 추출 후 수정.
null 체크, optional chaining, 타입 narrowing. 새 기능 추가 금지.
```

### 작업 8: Dead Code 정리

대상: `validation/`, `chainsight/`, `sec_pipeline/`, `thesis/`, `macro/`
리스크: MED (re-export 누락 가능)
실행: `claude -p` headless
검증: `pytest tests/ -q` 전체 통과

```
unused import 탐지 후 제거. __all__/re-export 확인 필수.
```

### 작업 9: API 응답 일관성 감사

대상: `*/views.py` (읽기 전용)
실행: 서브에이전트 (`@backend`)
산출물: `docs/architecture/api_consistency_audit.md`

```
success/error 래핑, HTTP 상태 코드, 에러 형식, pagination 일관성 분석.
```

### 작업 10: INDICATOR_CATALOG 동기화 검증

대상: `prompt_builder.py`, `indicator_matcher.py`, frontend (읽기 전용)
실행: 서브에이전트 (`@qa-architect`)
산출물: `docs/thesis_control/indicator_catalog_audit.md`

```
카탈로그↔matcher↔FE 3곳 동기화 검증.
불일치, 빈 description, data_params 형식 차이 식별.
```

### 작업 11: FE thesis 컴포넌트 테스트 (0→15개)

대상: `frontend/components/thesis/dashboard/` 5개 컴포넌트
선행: Vitest + RTL 수동 설치 필수
실행: `claude -p` headless
검증: `cd frontend && npx vitest run`

```
IndicatorRow, RealValueIndicatorCard, QuarterlySparkline,
HeatmapGrid, DashboardHeader에 대해 Vitest + RTL 테스트.
각 컴포넌트당 최소 3개 (렌더링, 인터랙션, 엣지케이스).
```

### 작업 12: FE validation+chainsight 테스트 (0→18개)

대상: `frontend/components/validation/`, `frontend/components/chainsight/` 6개 컴포넌트
선행: 작업 11 선행조건 완료
실행: `claude -p` headless
검증: `cd frontend && npx vitest run`

```
PeerContextBar, MetricCard, ValidationSummary,
GraphVisualization, ChainProfileCard, RelationList 테스트.
```

### 작업 13: rag_analysis 최소 테스트 (0→35개)

대상: Neo4j 의존성 없는 4개 서비스 (cache, context, entity_extractor, context_compressor)
실행: `claude -p` headless
검증: `pytest tests/unit/rag_analysis/ -v` 35+개 통과

```
Neo4j import 0인 파일만 대상.
from neo4j import 금지. LLM 호출 mock. 최소 35개.
```

### 작업 14: 데이터 무결성 감사

대상: `*/models*.py`, `*/signals.py`, `*/tasks.py` (읽기 전용)
산출물: `docs/architecture/data_integrity_audit.md`

```
FK orphan 위험, stale 데이터 정책, Neo4j↔PG 동기화 갭,
중복 레코드 위험 (UniqueConstraint / update_or_create) 분석.
```

### 작업 15: API 성능 감사

대상: `*/views.py`, `*/serializers.py`, `*/models*.py` (읽기 전용)
현황: QuerySet 195건 vs select_related 20건 (10:1)
산출물: `docs/architecture/performance_audit.md`

```
N+1 쿼리 탐지, 인덱스 누락, 느린 Serializer,
페이지네이션 누락. HIGH/MED/LOW + 수정 난이도 분류.
```

### 작업 16: 보안 감사

대상: 전체 코드 (읽기 전용)
현황: raw SQL 4건, CORS_ALLOW_ALL=True (DEBUG), JWT 60분/7일
산출물: `docs/architecture/security_audit.md`

```
OWASP Top 10: 인증/인가, 인젝션, 시크릿, CORS/XSS, 에러 노출.
Gemini 프롬프트 인젝션 벡터 포함.
심각도 CRITICAL/HIGH/MED/LOW/INFO.
```

### 작업 17: FMP/Gemini 장애 대응 감사

대상: `*/services/*`, `*/tasks.py` (읽기 전용)
현황: FMP fallback 0건, Gemini fallback 1건, Circuit Breaker 0건
산출물: `docs/architecture/api_dependency_audit.md`

```
FMP/Gemini/FRED/Neo4j 장애 시 영향 범위, fallback 유무,
Circuit Breaker 도입 후보, stale-while-revalidate 강화 후보.
```

### 작업 18: 모바일 UX 감사

대상: `frontend/components/`, `frontend/app/` (읽기 전용)
현황: 반응형 173건, 고정 폭 26건
산출물: `docs/architecture/mobile_ux_audit.md`

```
반응형 누락 (375px overflow), 터치 타겟 (44x44pt 미만),
모바일 네비게이션, 차트 터치 대응.
심각도 BLOCKER/MAJOR/MINOR.
```

### 작업 19-A: Chain Sight 설계서 갭

대상: `docs/chain_sight/plan/` 26개 vs `chainsight/` 코드
산출물: `docs/chain_sight/design_gap_audit.md`

```
설계 26개를 코드와 대조. 완전구현/부분구현/미구현/폐기 분류.
redesign_v1이 기존 plan을 대체하는지 확인.
```

### 작업 19-B: Thesis Control 설계서 갭

대상: `docs/thesis_control/` vs `thesis/`, `frontend/components/thesis/`
산출물: `docs/thesis_control/design_gap_audit.md`

### 작업 19-C: SEC Pipeline + 나머지 설계서 갭

대상: `docs/sec_pipeline/`, `docs/first_validation_system/`, `docs/news/`
산출물: `docs/architecture/design_gap_remaining.md`

### 작업 20: API 문서 자동생성 감사

대상: `config/settings.py`, `config/urls.py`, `*/views.py`, `*/serializers.py`
현황: drf-spectacular/Swagger 미설정
산출물: `docs/architecture/api_docs_audit.md`

```
drf-spectacular 설치 여부, schema view 등록 여부,
전체 엔드포인트 수, 도입 시 필요한 작업 목록.
```

---

## 부록: 아침 리포트 예시

```markdown
# ☀️ Stock-Vis 아침 리포트 — 2026-04-15 (Tuesday)

## 한눈에 보기

| 항목       | 상태 | 상세                  |
| ---------- | ---- | --------------------- |
| 테스트     | 🟢   | 549 passed, 0 failed  |
| TypeScript | 🟢   | 에러 0                |
| 린트       | 🟡   | 경고 5개              |
| 야간 수정  | ✅   | 1개 커밋 (ruff --fix) |
| Codex 판정 | SAFE | 머지 추천             |

## 🔧 야간 자동 수정

- nightly-fix: ruff 경고 2건 자동 수정

## 🔍 Codex 크로스 리뷰

- diff 안전성: SAFE
- 스팟 리뷰: P1 1건 (news/views.py 페이지네이션 누락)

## 🔬 오늘의 심층 분석: 데이터 & API (화요일)

- FMP 장애 대응: fallback 0건 → Circuit Breaker 도입 추천
- 데이터 무결성: on_delete=SET_NULL 후 정리 로직 3곳 누락
- Opus 검증: APPROVED (Round 2/5)

## ⚠️ 즉시 조치 필요

- [P1] Circuit Breaker 미구현 — FMP 다운 시 전체 서비스 영향

## 💡 이번 주 제안

1. FMP API 호출에 Circuit Breaker 패턴 도입
2. Chain Sight 마켓뷰 시드 노드 구현 착수
3. news/views.py 페이지네이션 추가

## 📋 오늘 할 일

- [ ] git diff main..nightly/auto-fix-2026-04-15 확인 후 머지
- [ ] reports/tuesday/ 심층 분석 전문 읽기
```
