# Event Calendar 설계 문서 v1.1 — EVT 트랙

> **문서 지위**: 이 문서는 EVT 트랙의 **설계 앵커**다. 구현 지시서가 이 문서와 충돌하면
> CC는 HALT 후 보고한다(Theme Heat 설계 앵커 프로토콜 준용).
> **작성**: 2026-08-20 v1.0 · **v1.1 갱신**: 2026-08-24 — 목업 3종 확정,
> D-EVT-FE1 반영, FE 계약 확정, 구현 지시서 금지 해제. 조사 근거 = EVT-SURVEY-0/1/2
> (커밋 b026b89b · e23b25ea · b671605d, 브랜치 monorepo/sess-evt-0).
> 본문에 인용된 실측 수치(행 수·엣지 수 등)는 2026-08-20 시점 스냅샷이며
> 기준선으로 캐리오버하지 않는다 — 구현 세션은 STEP 0에서 재측정한다.

---

## 0. 목적과 범위

사용자가 보는 시점에서 **미래에 예정된 시장 이벤트**(개별 종목 어닝·배당락·분할,
거시 이벤트)를 수집·저장하고, 관심종목 관점과 **관계망(Chain Sight) 관점**의
타임라인으로 노출한다. 서비스 플로우 상 위치: Dashboard(시장 흐름) ·
Node Monitoring(관심 추적) · Chain Sight(발견).

범위 = **B′**: 어닝 캘린더(+결과 채움) · 배당락 · 분할 예정 · 거시(기존 정비) ·
IPO(기존 유지). 비정형 이벤트(FDA·락업·컨퍼런스 등)는 범위 밖 — §9 이연 표 참조.

---

## 1. 확정 결정 원장

| ID | 결정 | 채택 | 마진/근거 |
|---|---|---|---|
| D-EVT-1 | 계층 원리 | 이벤트 **사실 원장 = 앱 중립**, 해석·노출 = 각 앱 | C안, 마진 1.05 자동 |
| D-EVT-1b | 물리 배치 | **1b-A**: 신규 통합 원장을 packages/shared에, 기존 3-트리(macro.EconomicEvent · shared.StockSplit · chain_sight.Filing-IPO)는 **불변 + 읽기 연합** | 4.30 vs 3.40, 사용자 확정 |
| D-EVT-2 | 이벤트 범위 | **B′** (어닝+결과 채움 · 배당락 · 분할예정 · 거시 정비) | 4.75, 타이브레이커+사용자 확정 |
| D-EVT-MODEL | 테이블 구조·명명 | **M-B** 단일 테이블 · typed nullable 컬럼, 모델명 **CalendarEvent** ("Event" 단독 금지 — 4개 앱 충돌 실측) | 4.30, 확정 소비자 우선 판단 |
| D-EVT-3 | 출시 순서 | **3-A** 페이즈드: Phase 1 캘린더 뷰 → Phase 2 관계망 타임라인(EVT-CHAIN) | 4.30, 사용자 확정 |
| D-EVT-FE1 | 노드 미니 위젯 배치 | **Phase 2와 동시 출시** — Phase 1은 캘린더 페이지 + 거시 스트립으로 완결 | 4.65, 사용자 확정 |
| — | SPLIT-CALENDAR-PREVIEW 흡수 | TASKQUEUE:1361 트랙을 EVT로 흡수. 예정 분할 = CalendarEvent(SPLIT), I3-SPLIT-GUARD 소비 계약은 본 원장이 제공. 발효 분할 기존 경로(StockSplit ← portfolio task) 불변 | 사용자 확정 |

**이연 결정** (§10): D-EVT-CHAIN-THRESH (관계 타임라인 파라미터 — 실데이터 관찰 게이트),
1b-A 이중성 해소(흡수) 재소환.

---

## 2. 데이터 모델 — CalendarEvent

위치: `packages/shared` (stocks 하위 권장 — StockSplit 선례 트리),
db_table `shared_calendar_event`.

```
event_type       CharField choices: EARNINGS / DIVIDEND / SPLIT      # 개방 enum
symbol           CharField, db_index
event_date       DateField, db_index          # DIVIDEND는 ex-date
session          BMO / AMC / UNKNOWN          # EARNINGS용
status           scheduled / occurred / stale
                 # stale = 재조회 창에서 소실(이동·철회 추정). 직접 매칭 없음(v1)
# --- EARNINGS ---
eps_estimated / eps_actual / revenue_estimated / revenue_actual   numeric null
# --- DIVIDEND ---
dividend_amount / payment_date / record_date / frequency          null
# --- SPLIT ---
split_numerator / split_denominator                               null
# --- 관측 메타 (P1-ii) ---
first_seen_at / last_seen_at     timestamptz
date_observed_count              smallint default 1
                 # 동일 (type,symbol,date)로 재관측될 때마다 +1 → 날짜 안정 신호
source           default 'fmp'
fmp_last_updated timestamptz null
created_at / updated_at
unique_together: (event_type, symbol, event_date)                 # 멱등 upsert 키
```

설계 노트:
- **날짜 이동 v1 처리 = 소실 감지.** FMP는 확정 플래그를 안 준다
  (earnings-calendar-confirmed 404 실측). 재조회 창의 미래 scheduled 행이 최신
  응답에 없으면 stale 전이. 새 날짜는 자연히 신규 행. 직접 매칭·date_history는
  v2 이음새(§9).
- **날짜 신뢰 라벨(P1-ii)은 파생 표시**: date_observed_count 기반
  안정(N회 연속 관측)/유동(stale 이력·신규) 라벨. 계산은 읽기 계층.
- 서프라이즈 % = (actual − estimated)/|estimated| — **저장하지 않고 계산**(P1-i).
- 유형 추가 시 컬럼 마이그레이션 허용은 M-B 채택의 명시적 비용.

---

## 3. 수집 설계

**Beat**: `collect-calendar-events`, 매일 **17:45 ET**
(collect-theme-filings 17:30 뒤 · theme-heat-daily 18:00 앞).
**DB PeriodicTask 정식 등록 + 등록 확인 필수** (dict-only 금지 규칙).
성분(유형)별 try/except 실패 격리, foreground 검증 가능 구조.

| 창 | 대상 | 콜 수 | 근거 |
|---|---|---|---|
| 선행 90일 | earnings — **45일 × 2 청킹** | 2 | 하드캡 4,000행 실측(90일 창은 tail만 반환·앞 74일 무언 소실 / 45일=2,302행 안전) |
| 선행 90일 | dividends-calendar 단일 콜 | 1 | 90일 2,517행 캡 미도달 실측 |
| 선행 90일 | splits-calendar 단일 콜 | 1 | 저볼륨(8일 14건 실측) |
| 트레일링 10일 | earnings 재조회 | 1 | actual 채움(→occurred 전이) + 소실 감지 겸용 |

일일 ~5콜 (Starter cap 10,000/day 대비 무시 가능).

**캡 방어 — 하드 요건 (게이트)**: 반환 count==4000 **또는** 반환 date-span <
요청 span → 창 이분 재시도, 2회 실패 시 해당 청크 실패 마킹 + 알림.
조용한 tail 절단은 무오류 데이터 소실이므로 **감지기 없이 가동 금지**.

**거시**: `update_economic_calendar`(01:00 ET, 멱등 upsert) **불변**. 정비 없음 —
연합 읽기에서 소비만.

**FMP 래퍼**: earnings/dividends/splits-calendar 3종 메서드 신규
(shared FMP client — 외부 API는 shared 래퍼 경유 규약).

---

## 4. 연합(읽기 병합) 계약

병합은 **앱 계층** 소유(shared가 macro를 import하면 경계 정신 위반 — 금지).
통합 타임라인 DTO의 원천 4개:

| # | 원천 | 제공 | 필터 기본값 |
|---|---|---|---|
| 1 | shared.CalendarEvent | 어닝·배당락·분할예정 | 유니버스∩관심종목 |
| 2 | macro.EconomicEvent | 거시 (forecast/actual 포함) | importance HIGH/CRITICAL |
| 3 | shared.StockSplit | 발효 분할 (참고 표시) | 관심종목 |
| 4 | credit_signals trading_calendar | NYSE 휴장일 (P1-iv) | 전체 |

DTO 공통 필드: kind, symbol?, title, event_dt(ET) + event_dt_kst, d_day, session?,
badges[](유형·중요도·날짜신뢰), detail(유형별), surprise?(P1-i, 발표 후).

**시간대 규약**: 저장은 ET 기준 날짜 + 세션. 표시 계층에서 KST 병기.
감사·로그 추론은 UTC 앵커(기존 common-bugs 규율).

---

## 5. 노출 계약 — Phase 1 (뷰 A)

- **Node Monitoring — 관심종목 이벤트 캘린더** (설계 사이클 목업 A 확정):
  날짜 그룹 리스트, D-day, 유형 뱃지, 컨센서스/상세, 거시 인터리브, 유형 필터.
- **Dashboard — 거시 스트립**: 동일 연합 읽기의 축소판(원천 2+4 중심).
- 표기 요건: 서프라이즈 %(P1-i, 발표 후 어닝·거시 공통 문법),
  날짜 신뢰 라벨(P1-ii: 안정/유동/미확정), KST·세션 병기, 휴장일 표시(P1-iv).
- **FE 안착 확정 (2026-08-24 목업 확인 사이클)**: Phase 1 = Node Monitoring 캘린더
  페이지("지난 7일 발표됨" 섹션 + 서프라이즈 % + 날짜 신뢰 라벨 + KST 병기 +
  휴장일 행) + Dashboard 거시 스트립(가로 카드 · HIGH 이상 · 45일 창 · 휴장 포함).
  노드 상세 미니 이벤트 위젯은 D-EVT-FE1에 따라 Phase 2와 동시(관계망 티저와 함께 완성).
  확정 목업 3종이 시각 계약 — FE 구현은 이를 준수.

**알림 이음새(P1-iii)** — Phase 1은 발송 미구현. 단 원장 쿼리 형태가
shared alerting(AlertSubscription/AlertDispatchLog)의 구독 조건과 호환되도록
계약을 고정한다: 조건 축 = (symbol[], event_type[], trigger ∈ {D-N 도래,
occurred 전이, stale 전이}). Phase 1.5에서 발송 연결 시 원장 변경 0이 목표.

---

## 6. Phase 2 — EVT-CHAIN (뷰 B, 관계망 이벤트 타임라인)

시드 종목 관점: 시드 자신의 이벤트 + RelationConfidence 1-hop 이웃의 이벤트.
**Postgres 단독 조인**(symbol_a/b 인덱스 실측 — Neo4j 무관, 복구 트랙과 결합도 0).

v1 파라미터 (잠정 — 확정은 D-EVT-CHAIN-THRESH, 실데이터 관찰 게이트):
- 엣지 필터: truth_score ≥ 85 AND relation_status = confirmed
- top-k = 10 (노이즈 통제)
- 전파 유형 = EARNINGS만 (배당락·분할 전파 off)
- **부호 중립**: 관계 뱃지(공급사/경쟁사/피어 = relation_type)와 truth_score만 표시,
  호재/악재 방향 판단은 시스템이 하지 않는다.
- 표기: "시드 다음 이벤트 D-N" 배너 + 그 사이 관계망 이벤트 목록(목업 B 확정).

원장 측 요건은 Phase 1 스키마가 이미 충족(symbol 인덱스 · 단일 테이블 타임라인
쿼리) — Phase 2 진입 시 원장 재작업 0.

---

## 7. Phase 2 백로그 (우선순위 순)

| ID | 내용 | 재료 | 비고 |
|---|---|---|---|
| P2-i | 컨센서스 리비전 × 다가오는 어닝 ("D-7 · 컨센 60일 상향 중") | EstimateSnapshot diff 조인 | C8 크로스섹셔널 가동 시기(~09-11 수렴)와 연동 |
| P2-ii | 어닝 반응 히스토리 (최근 4~8분기 beat/miss·익일 변동) | BasePriceData + actual. G-EVT-2로 FMP 서프라이즈 이력 EP 대체 가능성 확인 | D군 플라이휠 선행 재료 |
| P2-iii | 어닝 콜 AI 요약 | FMP transcript (G-EVT-2 게이트) + LLM 래퍼(Haiku 라우팅) | 시장 기본기화 — 갭 |
| P2-iv | 주간 이벤트 브리핑 | 결정론 템플릿(LLM 불요), Dashboard | Heat evidence-line 문법 |
| P2-v | 이벤트 행 뉴스 밀도 배지 ("최근 7일 뉴스 N건") | StockNews·ChainNewsEvent·TNV 조인 — 외부 콜 0 | 2026-08-20 스캔 추가분 |

**G-EVT-2 프로브 (Phase 2 진입 게이트, read-only ~6콜)**: ① transcript list/dates
접근(유료 게이트 단서 有 — FAIL 시 P2-iii 대체 원천 결정 사이클), ② M&A
latest/search 접근(§9 재소환 판단 재료), ③ 어닝 서프라이즈 이력 EP 접근
(P2-ii 비용 절감 판단). 예산 확인 → 각 1콜 → 상태·필드·캡 징후 보고.

---

## 8. D군 — 해자 플라이휠 (전략 방향, v2+)

**이벤트 반응 → 관계 증거 환류**: 이벤트(어닝 서프라이즈) 다음 날 1-hop 이웃의
실제 가격 반응을 측정해 RelationConfidence의 증거로 되먹인다. 이음새 =
chain_sight.CompanyEventReaction(기존 모델 실측 존재). 선행 재료 = P2-ii.
이벤트 원장이 해자(학습된 관계 신뢰도)를 소비하는 데서 그치지 않고 **기르는**
구조 — 별도 결정 사이클로 개시(트리거: Phase 2 안착 + P2-ii 가동).

부수: 테마 어닝 시즌 진행률("테마 X: 어닝 12/18 완료, beat 9") — Theme Heat
소비처 후보 구체화(기존 등록 유지).

---

## 9. 이연 + 재소환 트리거 (범위 잠식 방지)

| 항목 | 트리거 |
|---|---|
| 기존 3-트리 흡수(1b-C) | 소비처 2곳 이상이 연합 병합 코드 중복을 겪을 때. 흡수 시 makemigrations --dry-run 필수(방향C 함정) |
| 옵션 기대 변동폭 | T2 Tradier 게이트 통과 |
| M&A 이벤트 유형 | G-EVT-2 ② PASS + EVT-CHAIN 안착 (ACQUIRED 관계 시너지) |
| 가이던스 추출 | P2-iii 트랜스크립트 확보 (8-K RSS 병행 원천) — SEC β 계열 파싱 |
| 프레스릴리스 날짜 확정 신호 | P1-ii 라벨 가동 후 + LLM 비용 검토 (v2 date_history 포함) |
| FDA·락업·컨퍼런스 등 비정형 | C안 재소환 조건(기존 문서화) 유지 |
| 애널리스트 레이팅 이벤트 유형 | 사용자 요구 발생 (AnalystSignalSnapshot·grades EP 연결) |
| ICS 캘린더 내보내기 | 사용자 요구 발생 |
| 심볼 변경 API | 이 트랙 밖 — 유니버스 리프레시 트랙 등재 (티커 리네임 위생) |

---

## 10. 하네스 반영 번들 — 구현 세션 1호 지시서 탑재분

1. **DECISIONS**: §1 표 6행 전문 + 이연 2건(D-EVT-CHAIN-THRESH, 1b 흡수 재소환)
   + "이벤트 원장 백필은 no-retroactive 원칙 비대상(사실 데이터)" 명시.
2. **TASKQUEUE**: SPLIT-CALENDAR-PREVIEW(:1361) → EVT 이관(I3-SPLIT-GUARD 계약 유지
   명기) / IT-3(b) → CalendarEvent 소비자 연결 / §7 백로그·G-EVT-2 등재 /
   FMP 영속 예산 원장 부재 백로그.
3. **common-bugs**: 부존재 판정 규율 — 절단된 목록(head -N)·이름 패턴 grep만으로
   '없음' 판정 금지, 판정 전 전수성(wc -l) 검증.
4. **본 문서** docs/design/event_calendar_design.md 커밋 (0번 게이트).
5. 별건 처리 대기(디렉터 스케줄): sess-evt-0 조사 커밋 3건 push / origin 재통합(역머지) /
   C-N-REPAIR(19398955).

## 11. 오픈 이슈

1. shared 내 세부 위치(stocks vs 신설 모듈) — 구현 세션 STEP 0에서 트리 실측 후 확정.
2. 유니버스 스코프: 수집은 캘린더 전량 vs 유니버스 필터 — 구현 결정
   (저장량 대비 필터 이득 실측: 어닝 8일 1,057건 전량 기준).
3. Phase 1 FE 안착 세부 — **해소** (v1.1, D-EVT-FE1 + 목업 확정).

*(구현 금지 해제 — 2026-08-24. 구현 1호 지시서 = EVT-IMPL-1.)*
