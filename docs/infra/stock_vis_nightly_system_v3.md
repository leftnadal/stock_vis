# Stock-Vis 야간 자율 에이전트 시스템 — 최종 운영 문서

> 버전: v3 | 작성: 2026-04-15  
> 기준 브랜치: data_structure_remodeling_V1  
> 초기 감사 기준일: 2026-04-14

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [현황 요약](#2-현황-요약)
3. [매일 실행 작업 (Phase 1~4)](#3-매일-실행-작업)
4. [요일별 심층 분석 스케줄](#4-요일별-심층-분석-스케줄)
5. [Sonnet↔Opus 검증 루프](#5-sonnetopus-검증-루프)
6. [기준선 비교 추적](#6-기준선-비교-추적)
7. [전체 작업 인덱스 (21개)](#7-전체-작업-인덱스)
8. [1회성 작업 실행 계획](#8-1회성-작업-실행-계획)
9. [야간 시스템 매핑](#9-야간-시스템-매핑)
10. [파일 구조](#10-파일-구조)
11. [설치 가이드](#11-설치-가이드)
12. [일상 운영](#12-일상-운영)
13. [비용](#13-비용)
14. [안전장치](#14-안전장치)
15. [알림 설정](#15-알림-설정)
16. [트러블슈팅](#16-트러블슈팅)
17. [제약 조건](#17-제약-조건)
18. [부록: 작업 상세 (21개)](#18-부록-작업-상세)

---

## 1. 시스템 개요

### 핵심 아이디어

개발자가 자는 동안 4개의 AI 모델이 역할을 나눠서 Stock-Vis를 다각도로 분석한다. 코드 품질뿐 아니라 서비스 전략, UX, 보안, 데이터 건강성까지 커버한다. 매주 같은 분석을 반복하면서 이슈 증감을 자동으로 추적한다. 아침에 일어나면 종합 리포트 하나만 읽으면 된다.

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
├─ 기준선 비교 요약 생성 ───────────────────────── ~1분
├─ 아침 리포트 통합 ────────────────── Opus ────── ~10분
├─ 리포트 Git 커밋 ──────────────────────────────── 즉시
│
│                                      총 ~75분
▼
아침 08:00 알림
├── macOS 알림 팝업
├── HTML 리포트 브라우저 자동 열기
└── Slack / Discord 메시지 (선택)
```

### 리포트 저장 경로

```
docs/nightly_auto_system/YYYYMM/DD/
                          ↑       ↑
                        연월     일
```

예: `docs/nightly_auto_system/202604/15/morning_report.md`

---

## 2. 현황 요약

| 항목               | 수치                                                                                   |
| ------------------ | -------------------------------------------------------------------------------------- |
| 총 테스트          | 1,693개 (549 passed, 1 failed, 4 errors)                                               |
| 테스트 0개 앱      | validation (3,457줄), sec_pipeline (3,466줄), rag_analysis (14,608줄), users (2,820줄) |
| TS 컴파일 에러     | 4개                                                                                    |
| FE 컴포넌트        | 190개 / 테스트 0개 (Vitest/RTL 미설치)                                                 |
| 기존 테스트 실패   | 1 FAILED (news) + 4 ERROR (serverless)                                                 |
| Celery Beat 스케줄 | 63개                                                                                   |
| API 엔드포인트     | 234개                                                                                  |
| API 문서 자동생성  | 미설정 (수동 계약서 3개만)                                                             |
| Circuit Breaker    | 뉴스 3개만 (FMP/Gemini 없음)                                                           |
| Gemini fallback    | 1건 / timeout 0/28건                                                                   |
| FK 관계            | 63개, select_related 20건 vs QuerySet 195건 (10:1)                                     |
| 설계 문서          | 59개 plan, 68개 task_done                                                              |

---

## 3. 매일 실행 작업

### Phase 1: 코드 스캔 (Haiku)

pytest, tsc, ruff를 돌려서 현재 상태를 파악한다. 어제 스캔 결과가 있으면 "어제 대비 변화" 섹션을 자동 추가한다.

결과: 🟢 정상 / 🟡 주의 / 🔴 문제 있음

### Phase 2: 자동 수정 (Sonnet)

Phase 1에서 발견된 문제 중 안전한 것만 `nightly/auto-fix-날짜` 브랜치에서 수정한다.

수정 가능: 테스트 실패(테스트 코드 수정), TS 컴파일 에러, `ruff --fix`
수정 금지: DB 마이그레이션, Neo4j 스키마, `.env`, `settings.py`, 새 기능, 의미적 로직

### Phase 3: 수정 검증 (Haiku)

Phase 2 수정 코드를 재검증하고 수정 전/후 비교표를 생성한다.

### Phase 4: Codex 크로스 리뷰 (GPT-5-Codex)

Claude와 다른 모델 계열(OpenAI)이 독립적으로 리뷰한다.

- **diff 리뷰**: Phase 2 자동 수정의 안전성 판정 (SAFE / CAUTION / BLOCK)
- **스팟 리뷰**: 최근 48시간 변경 파일을 P0/P1/P2로 분류

Codex 미설치 시 자동 스킵.

---

## 4. 요일별 심층 분석 스케줄

모든 심층 분석은 Sonnet↔Opus 검증 루프로 실행되며, 지난주 같은 요일 결과를 기준선으로 비교한다.

| 요일 | 주제          | 분석 항목                                   | 기준선 추적 대상            |
| :--: | ------------- | ------------------------------------------- | --------------------------- |
|  월  | UI/UX         | 컴포넌트 일관성, 모바일 UX                  | 고정 폭 26건, 접근성        |
|  화  | 데이터 & API  | FMP/Gemini 장애 대응, 데이터 무결성         | CB 도입 여부, fallback 비율 |
|  수  | 보안 & 성능   | OWASP 보안, N+1 쿼리, 인덱스                | CRITICAL 5→?, AllowAny 38→? |
|  목  | 비즈니스 로직 | 4대 필라 완성도, 설계서 갭, 카탈로그 동기화 | keyword_rules 17%→?         |
|  금  | 아키텍처      | API 일관성, API 문서, 기술부채              | 엔드포인트 234→?            |
|  토  | 전략          | 경쟁 분석, Beat 스케줄, 나머지 설계서 갭    | 17:00 폭주 1,015+→?         |
|  일  | 주간 종합     | 전체 요약 + 다음 주 추천 TOP 5              | —                           |

### 각 요일 상세

**월요일 — UI/UX**

- 190개 FE 컴포넌트 디자인 일관성 (색상, 반응형, 접근성)
- 로딩/에러/빈 상태 처리 누락, Chain Sight 마켓뷰 UX
- 핵심 사용자 플로우 3개 추적
- 모바일: 고정 폭 26건, 터치 타겟 44x44pt, Recharts 모바일 대응

**화요일 — 데이터 & API**

- FMP 18파일: 에러 핸들링, 402 처리, rate limit (Starter 300/min)
- Gemini 28파일: 429 처리(현재 12파일 미처리), timeout(현재 0/28)
- Circuit Breaker 도입 여부 추적 (FMP P0, Gemini P0)
- FK orphan: on_delete=SET_NULL 13곳, 정리 로직 존재 여부
- Neo4j↔PG 동기화 실패 재시도, drift 감지

**수요일 — 보안 & 성능**

- OWASP Top 10 + LLM Top 10: CRITICAL 5건 해소 여부 추적
- serverless AllowAny 38개 뷰 감소 추적
- LLM 프롬프트 인젝션 4곳, Cypher 인젝션
- N+1 쿼리 HIGH 4건 (LeaderComparison 90+ 히트 등)
- 인덱스 누락 7건, 글로벌 페이지네이션 미설정

**목요일 — 비즈니스 로직**

- 4대 필라별 구현 완성도 (✅/🔨/📋/❌)
- Chain Sight 설계 26개 vs 코드 갭
- Thesis Control 설계 vs 코드 갭
- 카탈로그 동기화: 이름 불일치 4건, keyword_rules 17% 커버리지

**금요일 — 아키텍처**

- 기술부채 TOP 5, 스케일 병목
- DRF API 응답 형식 일관성 매트릭스
- API 문서: drf-spectacular 미설정, 234개 엔드포인트
- 아키텍처 진화 제안 (솔로 개발자 현실성)

**토요일 — 전략**

- Stock-Vis vs 증권사/토스/TradingView 비교
- MVP 출시 최소 기능 목록
- Beat 스케줄 63개: 17:00-18:00 FMP 1,015+ 폭주 해소 여부
- SEC Pipeline + 나머지 설계서 갭

**일요일 — 주간 종합**

- 이번 주 코드 변화/커밋 통계
- 반복 문제 패턴, 테스트 커버리지 추세
- CRITICAL/HIGH 이슈 증감 추세
- Opus APPROVED 비율
- 다음 주 추천 작업 TOP 5

---

## 5. Sonnet↔Opus 검증 루프

```
Round 1
  Sonnet 분석 (+ 기준선 있으면 비교 포함) → draft_R1.md
  Opus 검증 → "APPROVED ✅" 또는 "NEEDS_REVISION + 보완 지시"

Round 2 (NEEDS_REVISION일 때)
  Sonnet 보완 (Opus 피드백 반영) → draft_R2.md
  Opus 재검증 → ...

최대 5라운드. 대부분 2~3라운드에 APPROVED.
5라운드 소진 → "수동 확인 필요" 태그.
```

Opus 승인 기준: 구체적 근거(파일/라인) 있는지, 누락 관점 없는지, 기준선 대비 변화 추적 정확한지, 솔로 개발자 현실적인지.

---

## 6. 기준선 비교 추적

### 동작 원리

매주 같은 요일 심층 분석을 돌릴 때, 지난주 같은 요일 리포트를 Sonnet에게 자동으로 제공한다. Sonnet은 기준선 대비 변화를 다음과 같이 표시한다:

- ✅ 해결된 이슈
- 🆕 새로 발견된 이슈
- ⬆️ 악화된 이슈
- ➡️ 변화 없는 이슈

### 초기 기준선 (2026-04-14 감사)

| 카테고리 | 항목                   | 초기값       | 추적 요일 |
| -------- | ---------------------- | ------------ | --------- |
| 보안     | CRITICAL               | 5건          | 수요일    |
| 보안     | HIGH                   | 12건         | 수요일    |
| 보안     | serverless AllowAny    | 38개 뷰      | 수요일    |
| 성능     | N+1 쿼리 HIGH          | 4건          | 수요일    |
| 성능     | 인덱스 누락            | 7건          | 수요일    |
| 성능     | 글로벌 페이지네이션    | 미설정       | 수요일    |
| API      | Circuit Breaker        | 뉴스 3개만   | 화요일    |
| API      | Gemini timeout 설정    | 0/28 파일    | 화요일    |
| API      | FMP 402 미처리         | 12/18 파일   | 화요일    |
| 인프라   | FMP 17:00 폭주         | 1,015+ calls | 토요일    |
| 비즈니스 | keyword_rules 커버리지 | 17% (11/64)  | 목요일    |
| 비즈니스 | 카탈로그 이름 불일치   | 4건          | 목요일    |

### 매일 생성되는 baseline_comparison.md

어제 대비 일일 스캔 변화 + 지난주 같은 요일 대비 심층 분석 변화 + 초기 기준선 대비 전체 추적 테이블을 포함한다.

---

## 7. 전체 작업 인덱스 (21개)

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

## 8. 1회성 작업 실행 계획

### Tier 1: 즉시 수정 (~45분)

| 작업              | 소요 | 명령                                                         |
| ----------------- | :--: | ------------------------------------------------------------ |
| #1 TS 컴파일 에러 | 5분  | `git checkout -b fix/ts-compile-errors && claude -p "..."`   |
| #2 깨진 테스트    | 15분 | `git checkout -b fix/broken-tests && claude -p "..."`        |
| #7 FE 타입 안전성 | 10분 | `git checkout -b fix/fe-type-safety && claude -p "..."`      |
| #8 Dead code      | 15분 | `git checkout -b chore/dead-code-cleanup && claude -p "..."` |

### Tier 2: 테스트 확보 (0→163+개, ~130분)

| 작업                         | 소요 | 선행 조건                                                                               |
| ---------------------------- | :--: | --------------------------------------------------------------------------------------- |
| 수동: FE 테스트 인프라 설치  | 5분  | `cd frontend && npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom` |
| #3 validation 테스트         | 30분 | 마이그레이션 완료                                                                       |
| #4 sec_pipeline 테스트       | 25분 | 마이그레이션 완료                                                                       |
| #5 users 테스트              | 20분 | —                                                                                       |
| #13 rag_analysis 테스트      | 25분 | —                                                                                       |
| #11 FE thesis 테스트         | 25분 | FE 인프라 설치                                                                          |
| #12 FE validation+chainsight | 20분 | FE 인프라 설치                                                                          |

### Tier 3: 감사 보고서 (병렬 가능, 브랜치 불필요)

#15 API 성능, #16 보안, #17 FMP/Gemini, #14 데이터 무결성, #19-A Chain Sight 갭, #6 Beat 스케줄, #20 API 문서 — 총 7건, ~2시간.

---

## 9. 야간 시스템 매핑

### 매일 자동 (Phase 1~4)

Phase 1 Haiku(스캔) → Phase 2 Sonnet(수정) → Phase 3 Haiku(검증) → Phase 4 Codex(크로스 리뷰)

→ #1, #2, #7 유형을 매일 자동 처리

### 요일별 심층 분석

| 요일 | 분석                                           | 관련 작업         |
| :--: | ---------------------------------------------- | ----------------- |
|  월  | 컴포넌트 일관성 + 모바일 UX                    | #18               |
|  화  | FMP/Gemini 장애 대응 + 데이터 무결성           | #17, #14          |
|  수  | 보안 (OWASP) + 성능 (N+1)                      | #16, #15          |
|  목  | 기능 완성도 + 카탈로그 동기화 + Chain Sight 갭 | #19-A, #19-B, #10 |
|  금  | API 일관성 + API 문서 + 아키텍처 진화          | #9, #20           |
|  토  | 경쟁 분석 + Beat 스케줄 + 나머지 설계서 갭     | #6, #19-C         |
|  일  | 주간 종합 + 다음 주 TOP 5                      | —                 |

---

## 10. 파일 구조

```
stock-vis/docs/nightly_auto_system/     ← 리포트 (프로젝트 안, Git 추적)
├── 202604/
│   ├── 14/
│   │   ├── morning_report.md           ★ 아침에 이걸 읽음
│   │   ├── morning_report.html         ★ 브라우저 자동 열림
│   │   ├── scan.md
│   │   ├── auto_fix_verify.md
│   │   ├── codex_review.md
│   │   ├── baseline_comparison.md
│   │   └── (요일별 심층 분석 파일들)
│   ├── 15/
│   │   └── ...
│   └── ...
├── 202605/
│   └── ...
└── ...

~/stock-vis-nightly/                    ← 시스템 파일 (프로젝트 밖)
├── nightly_v3.sh                       매일 23:00 실행
├── morning_notify.sh                   매일 08:00 알림
├── install.sh                          최초 설치
├── work/                               Sonnet↔Opus 중간 파일 (임시)
└── logs/                               실행 로그 (30일 보관)
```

---

## 11. 설치 가이드

### 사전 요구사항

- macOS (MacBook, Tailscale 원격 접속 가능)
- Claude Code: `npm i -g @anthropic-ai/claude-code`
- Claude 인증 (Pro/Max 구독 또는 API 키)

### 설치 순서

```bash
# 1. 파일 배치
mkdir -p ~/stock-vis-nightly
# nightly_v3.sh, morning_notify.sh, install.sh 복사

# 2. 프로젝트 경로 확인
# nightly_v3.sh 상단: PROJECT_DIR="$HOME/stock-vis"

# 3. 설치 실행
chmod +x ~/stock-vis-nightly/*.sh
~/stock-vis-nightly/install.sh
```

install.sh가 하는 일: 실행 권한, 디렉토리 생성, crontab 등록 (23:00 + 08:00), Git 포함 여부 선택.

### Codex 추가 (선택)

```bash
npm i -g @openai/codex
codex auth login
```

미설치 시 Phase 4만 스킵. 나머지 영향 없음.

---

## 12. 일상 운영

### 자기 전 — 아무것도 안 해도 됨

cron이 매일 23:00 자동 실행. MacBook 잠자기 방지: `sudo pmset -c sleep 0 displaysleep 10`

### 아침 루틴 (5~10분)

```bash
# 1. 아침 리포트
cat docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/morning_report.md

# 2. 오늘 생성된 모든 리포트
ls docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/

# 3. 자동 수정 diff
git diff main..nightly/auto-fix-$(date +%Y-%m-%d)

# 4. Codex 판정 확인
cat docs/nightly_auto_system/$(date +%Y%m)/$(date +%d)/codex_review.md

# 5. 머지
git merge nightly/auto-fix-$(date +%Y-%m-%d)
```

### 날짜별 리포트 탐색

```bash
# 특정 날짜
ls docs/nightly_auto_system/202604/14/

# 이번 달 전체
tree docs/nightly_auto_system/$(date +%Y%m)/ -L 1

# 지난주 vs 이번 주 보안 감사 비교
diff docs/nightly_auto_system/202604/09/security_audit.md \
     docs/nightly_auto_system/202604/16/security_audit.md
```

---

## 13. 비용

### 구독 플랜

| 항목                   | 비용                     |
| ---------------------- | ------------------------ |
| Claude Max 5x          | $100/월                  |
| ChatGPT Plus (Codex용) | $20/월                   |
| 합계                   | $120/월 (추가 비용 없음) |

### API 종량제

| 항목             | 일     | 월    |
| ---------------- | ------ | ----- |
| 매일 Phase 1~4   | $1.04  | $31   |
| 요일별 심층 분석 | $2.50  | $75   |
| 아침 리포트      | $0.50  | $15   |
| 합계             | ~$4.04 | ~$121 |

---

## 14. 안전장치

- 모든 수정은 `nightly/auto-fix-날짜` 브랜치 (main 직접 수정 없음)
- DB 마이그레이션, Neo4j 스키마, `.env`, `settings.py` 수정 금지
- lockfile 중복 실행 방지, 자동 stash/복원
- Codex SAFE/CAUTION/BLOCK 판정
- Opus 5라운드 소진 시 "수동 확인 필요" 태그
- 7일 이전 nightly 브랜치 자동 삭제
- 30일 이전 로그 자동 정리

---

## 15. 알림 설정

macOS 네이티브 알림 (기본): 설정 불필요.
Slack: `morning_notify.sh`에서 `SLACK_WEBHOOK` 입력.
Discord: `morning_notify.sh`에서 `DISCORD_WEBHOOK` 입력.
HTML 리포트: 매일 아침 브라우저 자동 열림.

---

## 16. 트러블슈팅

| 증상             | 해결                                                              |
| ---------------- | ----------------------------------------------------------------- |
| cron 실행 안 됨  | 시스템 환경설정 → 보안 → 전체 디스크 접근 → `/usr/sbin/cron` 추가 |
| Claude 인증 만료 | `claude auth login`                                               |
| 특정 작업 재실행 | `git branch -D nightly/auto-fix-날짜` 후 재실행                   |
| MacBook 잠자기   | `sudo pmset -c sleep 0 displaysleep 10`                           |
| 중단/제거        | `crontab -e` 줄 삭제, `rm -rf ~/stock-vis-nightly`                |

---

## 17. 제약 조건

| 항목            | 제약                                     |
| --------------- | ---------------------------------------- |
| DB 마이그레이션 | 자율 실행 금지                           |
| Neo4j 스키마    | 변경 자율 실행 금지                      |
| FMP API         | rate limit 고려 (Starter: 300 calls/min) |
| 시크릿          | `.env`, `settings.py` 수정 금지          |
| 브랜치          | 모든 코드 수정은 별도 브랜치에서         |

---

## 18. 부록: 작업 상세 (21개)

### #1 TS 컴파일 에러 수정

대상: `frontend/lib/thesis/mock.ts`, `frontend/components/news/NewsCard.tsx`
검증: `npx tsc --noEmit` 에러 0

### #2 깨진 테스트 수정

대상: `tests/news/`, `tests/serverless/`
검증: `pytest tests/ -q --tb=short` 전체 통과

### #3 validation 테스트 (0→40개)

대상: 실제 파일 구조 먼저 확인 (`find validation/ -name "*.py"`)
검증: `pytest tests/unit/validation/ -v`

### #4 sec_pipeline 테스트 (0→30개)

대상: 실제 파일 구조 먼저 확인 (`find sec_pipeline/ -name "*.py"`)
검증: `pytest tests/unit/sec_pipeline/ -v`

### #5 users 테스트 (0→25개)

대상: JWT 인증, Portfolio CRUD, Watchlist
검증: `pytest tests/unit/users/ -v`

### #6 Beat 스케줄 감사

대상: `config/celery.py` 63개 태스크 (읽기 전용)
초기 기준: 17:00-18:00 FMP 1,015+ 호출 폭주

### #7 FE 타입 안전성

대상: `frontend/components/`, `frontend/lib/`
검증: `npx tsc --noEmit` exit 0

### #8 Dead code 정리

대상: BE 5개 앱 (리스크 MED: re-export 확인 필수)
검증: `pytest tests/ -q` 전체 통과

### #9 API 응답 일관성 감사

대상: 모든 `views.py` (읽기 전용)

### #10 INDICATOR_CATALOG 동기화

초기 기준: 이름 불일치 4건, keyword_rules 커버리지 17%

### #11 FE thesis 컴포넌트 테스트 (0→15개)

선행: Vitest + RTL 수동 설치 필수

### #12 FE validation+chainsight 테스트 (0→18개)

선행: #11 선행조건 완료

### #13 rag_analysis 최소 테스트 (0→35개)

대상: Neo4j 의존성 0인 4개 서비스만 (cache, context, entity_extractor, context_compressor)

### #14 데이터 무결성 감사

초기 기준: CRITICAL 3건, Stock CASCADE 27+ 테이블

### #15 API 성능 감사

초기 기준: N+1 HIGH 4건, 인덱스 누락 7건, QuerySet 195 vs select_related 20

### #16 보안 감사

초기 기준: CRITICAL 5건, HIGH 12건, AllowAny 38개 뷰

### #17 FMP/Gemini 장애 대응 감사

초기 기준: FMP fallback 67%, Gemini timeout 0/28, CB 뉴스만

### #18 모바일 UX 감사

초기 기준: 반응형 173건, 고정 폭 26건

### #19-A Chain Sight 설계서 갭

대상: docs/chain_sight/plan/ 26개 vs chainsight/ 코드

### #19-B Thesis Control 설계서 갭

대상: docs/thesis_control/ vs thesis/ + frontend/components/thesis/

### #19-C SEC Pipeline + 나머지

대상: docs/sec_pipeline/, docs/first_validation_system/, docs/news/

### #20 API 문서 자동생성 감사

초기 기준: drf-spectacular 미설치, 엔드포인트 234개, 수동 계약서 3개

---

## 부록: 아침 리포트 예시

```markdown
# ☀️ Stock-Vis 아침 리포트 — 2026-04-16 (Wednesday)

> 리포트 위치: docs/nightly_auto_system/202604/16/

## 한눈에 보기

| 항목       | 상태 | 상세                 |
| ---------- | ---- | -------------------- |
| 테스트     | 🟢   | 549 passed, 0 failed |
| TypeScript | 🟢   | 에러 0               |
| 린트       | 🟡   | 경고 5개             |
| 야간 수정  | ✅   | 1개 커밋             |
| Codex 판정 | SAFE | 머지 추천            |

## 📊 기준선 대비 변화 (초기 2026-04-14 대비)

| 항목                | 초기 | 현재 | 변화        |
| ------------------- | ---- | ---- | ----------- |
| 보안 CRITICAL       | 5    | 3    | ✅ -2       |
| serverless AllowAny | 38   | 20   | ✅ -18      |
| N+1 HIGH            | 4    | 3    | ✅ -1       |
| Gemini timeout      | 0/28 | 0/28 | ➡️ 변화없음 |

## 🔬 오늘의 심층 분석: 보안 & 성능 (수요일)

- 보안: CRITICAL 2건 해결 (SECRET_KEY 환경변수 분리, CORS 프로덕션 설정)
- 성능: LeaderComparisonView N+1 수정 확인
- Opus 검증: APPROVED (Round 2/5)

## 📂 오늘 생성된 리포트

- scan.md, auto_fix_verify.md, codex_review.md
- security_audit.md, performance_audit.md
- baseline_comparison.md, morning_report.md
```
