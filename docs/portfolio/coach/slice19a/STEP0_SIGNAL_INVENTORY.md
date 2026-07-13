# Slice 19a STEP 0 — 신호 인벤토리 + A-게이트 HALT (디렉터 판단 입력)

> 세션: 실행 진입 → STEP 0 A-게이트 실패(기대수익 신호 부재) → **HALT**(§7).
> 측정일: 2026-07-13 · worktree `monorepo/sess-slice19a` · base origin/main `3d5341e`.
> baseline `pytest apps/portfolio tests/architecture` = **582 passed / 0 failed**(깨끗한 출발선).

## A-게이트 판정 = ❌ NO (기대수익 정본 신호 부재)

후보/보유 종목의 forward "기대수익률"(갭 = 목표 − **현재기대**의 후자)을 산출할 정본 신호가 프로덕션에서 **하나도 사용 가능하지 않다.**

| 후보 신호 | 위치 | 가용성 |
|---|---|---|
| analyst_target_price(컨센서스 목표가) | `shared/stocks/models.py:97` | ❌ **유령 필드** — writer 전무, 항상 null |
| analyst_rating_* | models.py:100-104 | ❌ 유령 필드 |
| forward_pe | models.py:110 | ❌ 유령 필드 |
| EstimateSnapshot/리비전 | — | ❌ 이 트리에 모델 부재(theme_heat 별도 브랜치) |
| 프리셋 스코어링 엔진 출력 | `services/scoring/` | △ 0~100 **품질점수**(기대수익 아님) + **입력 metrics 공급 계층 부재**(고아 함수, e3_service만 optional 호출) |
| return_12m/6m/3m·momentum | `metrics/definitions/metrics.py:535+` | △ **정의만·리졸버 부재** + 본질 후행 실현수익 |
| WatchlistItem.target_entry_price → distance_from_entry | `users/models.py:226,258` | ✅ 존재·작동. 단 **사용자 손입력 목표가**(예측 아님) |
| Portfolio.target_price → distance_from_target | `users/models.py:64,148` | ✅ 존재. **사용자 손입력 매도목표**(예측 아님) |
| CompanyMetricSnapshot | `shared/metrics/models/metric_snapshot.py` | △ 후행·연간 펀더멘털, 기대수익 없음 |
| DailyPrice | `shared/stocks/models.py:238` | ✅ 존재 → 과거수익률 계산 가능(미계산, 후행 프록시) |

**결론**: "현재 기대수익" 항을 채울 정본이 없다. 손에 잡히는 건 ⑴ 사용자 손입력 목표가 거리, ⑵ 미계산 과거수익률 — 둘 다 예측(expected return)이 아닌 프록시.

## (1) 프리셋 스코어링 엔진 (부품 B 후보)
- `services/scoring/base.py:22` `ScoringEngineBase` + presets/{value,growth,income,factor,special} 12 preset. 출력 = 종목 단위 0~100 **품질점수**.
- ★ **고아 상태**: `metrics/`에 정의(definitions/)만 있고 **종목→정규화 metrics dict 산출 계산 계층 부재**. 유일 호출부 e3_service.py:65도 metrics optional→skip. 랭킹/정렬에 미사용. → 19a가 쓰려면 **metrics 리졸버 신규 구축 선행**.

## (2) RelationConfidence (해자, 부품 B 후보) — 사용 가능 ✅
- `chain_sight/models/relation_discovery.py:64`. 엣지 단위, `symbol_a`·`symbol_b`=티커. `truth_score`(Float)·status(hidden~confirmed). 
- 후보 매핑 = **YES**: WatchlistItem.stock(심볼)과 직접 매핑. dashboard strip_service.py:126-136이 "seed 심볼 ↔ 반대편 심볼" 엣지 조회 실증 → 후보 랭킹 키로 재사용 가능.
- 주의: per-row `investment_relevance`는 deprecated. 쌍 relevance는 `RelationPairSnapshot` 소관.

## (4) FX / 통화
- `stocks.Stock.currency`(USD/KRW choices, default USD, models.py:15) + `exchange` → 종목 통화 판별 가능. **단 default USD라 KRW 미세팅 시 오판 위험.**
- 환율 영속 모델 **부재**(라이브 조회만, market_pulse_client). 다통화 정규화는 라이브 의존.
- CashBalance 현재 OneToOne·currency 필드 없음(USD 고정) → 다통화 전환(FK+unique) 대상.

## ⚠️ 부수 발견
1. analyst_target_price·rating·forward_pe = 유령 필드(serializer 노출되나 항상 null, 프론트 오인 위험).
2. 스코어링 엔진 = 고아(12 preset 전부 미배선, metrics 리졸버 부재).
3. `PredictionRecord`(UserGoal docstring 참조) 모델 미존재 → 19a 신규 생성 대상.
4. FX 저장 부재 + Stock.currency 오탈 위험.

## 디렉터 판단이 필요한 갈래 (판정 없이 제시)

지시서 §2(d)/§4 fallback: A-게이트 실패 → B후퇴는 스켈레톤 변경이라 디렉터 판단.

- **갈래 1 — 기대수익 프록시로 A 골격 유지**: "현재 기대수익"을 사용자 손입력 목표가(distance_from_entry/target) 또는 DailyPrice 과거수익률로 프록시. 갭-충전 뼈대 유지하되 신호를 프록시로 명시.
- **갈래 2 — B후퇴(골격 교체)**: 갭-충전(A) 버리고, 후보를 RelationConfidence(+가용 신호)로 **랭킹만**. 목표-대비 갭 드라이버 없이 "관심 후보 정렬" 중심. 단 스코어링 엔진은 고아라 실질 랭킹 키 = RelationConfidence + 사용자 목표가 거리.
- **갈래 3 — 신호 파이프라인 선구축**: metrics 리졸버 또는 analyst_target writer 또는 forward 추정을 먼저 구축(19a 범위 대폭 확대, 별도 슬라이스).
- **병합 전략(갈래 1/2 공통 하위)**: 기대수익 프록시 = A(사용자 목표가) / B(LLM 추정) / C(blend) 중 택.
