# TH-SESSION-1 — TNV 백필 · stale heat 재산출 결과 (TH 기상 완료 선언 초안)

**실행:** 2026-08-03 · SECB 종결 트리거(TH-TRIGGER-FIRED) 소비 · 백필=병진 수동 실행 / 검증·문서=CC
**계약:** CC DB 쓰기 0(백필은 병진 실행분) · LLM 0 · 외부 API 0(순수 DB 집계) · override 무접촉

---

## 실행 개요

디렉터 판정 = **(A) TNV만 + heat 재산출**(override 재산출 배제, 마진 2.25). 트리거 원안 "corpus unfreeze(07-12→, 50일+)"은 실측으로 정정(D-TH-TRIGGER-CORRECT): corpus 무동결, 실동결=TNV 집계, 창=07-26→08-03(9일).

## 백필 창 (§0 실측)

| | 값 |
|---|---|
| T₀ (TNV 최신, 백필 前) | 2026-07-25 |
| D_end (corpus 최신) | 2026-08-03 |
| 백필 창 | 07-26 → 08-03 (9일) |
| corpus 창 내 결측일 | 없음 (단 4일은 keywords=[] 빈 추출) |

## 병진 실행 결과 (foreground)

- **① TNV 집계 백필**: `aggregate_theme_news_volume(date_gte=07-26, date_lte=08-03)` → `{'days': 9, 'written': 17, 'zeroed': 0}`
- **② stale heat 재산출**: `compute_theme_heat(as_of)` 루프 07-26→08-03 → 9일 전부 `stored 6 of 11`

## §D 검증표

| 항목 | 사전 | 사후 | 판정 |
|---|---|---|---|
| TNV 총행 | 359 | **376** (+17) | ✓ written 17 일치 |
| TNV 최신 date | 07-25 | **08-01** | ✓ (08-02/03 빈 키워드→0행) |
| TNV 창 채움 | 0행 | 07-28(3)·29(3)·30(5)·31(3)·08-01(3) | ✓ 멘션 있는 5일만(희소) |
| TNV 결측 4셀 | — | 07-26·27·08-02·03 | ✓ keywords=[] 빈 추출(주말/월, corpus 특성) |
| heat 창(07-26~08-03) | 30행(07-29~) | **54행 = 9일×6테마** | ✓ 전 창 커버(07-26/27/28 신규+08-03 신규) |
| heat 최신일 저장 themes | 6 | 6 | ✓ §0.5 설계(결측 ≥3=not_computed) |
| **override** | 215/ovr_v1/07-22 01:57 | **215/ovr_v1/07-22 01:57** | ✓ **무접촉** |
| **corpus** | 08-03/155 | **08-03/155** | ✓ **무변경** |
| full suite | 4561/0/53 @ 0e994427 | **4561/0/53** | ✓ 동일(문서 커밋뿐) |

## 추가 검증 — heat가 백필 TNV를 소비 확인 (07-30 스팟)

07-30(TNV 백필 5테마=1,2,3,5,7) heat 저장 6테마의 `components["C3"]` 실측 — 전부 present(missing=None), raw(news volume)=38~152. 백필 TNV 보유 테마(1,2,3,5)가 저장행에 포함·C3 계산됨 → **heat 재산출이 백필 TNV를 실제 소비**. (ThemeHeatScore `components` JSONField 저장 스키마 → 확인 가능.)

| theme | TNV(07-30) | C3 s | C3 raw |
|---|---|---|---|
| 1 | 있음 | 0.085 | 152 |
| 2 | 있음 | 0.631 | 51 |
| 3 | 있음 | 0.516 | 48 |
| 4 | 없음 | 0.565 | 56 |
| 5 | 있음 | 0.736 | 38 |
| 6 | 없음 | 0.746 | 50 |

## 멱등성·격리 근거

- TNV=`aggregate_theme_news_volume` `update_or_create`(c3_narrative_service.py:189·202) / heat=`compute_theme_heat` `update_or_create(theme,date)`(heat_beat.py:13). 재실행 안전.
- override 무접촉: `use_override=True`는 `load_override_map` **읽기만**. ThemeTermOverride 쓰기 경로 없음(사전=사후 스냅샷 입증).

## 관찰 (범위 밖·차기 후보)

- **주말/월요일 DailyNewsKeyword 빈 키워드([])**: 07-26(Sun)·07-27(Mon)·08-02(Sun)·08-03(Mon) DNK 행 존재하나 keywords=[] → 해당일 TNV/C3 0. 백필 무관·기존 corpus 키워드 추출 특성. 키워드 추출 beat의 주말 공백 여부는 별도 관찰 후보.
- **6/11 themes 상시**: 5개 not_computed 테마는 C3(TNV) 외 성분도 결측 ≥3 → TNV 백필로도 미전환. 수렴 관찰 = TH-HEAT-C8-CONVERGENCE(별도).

## TH 기상 완료 선언 (초안)

TH 트랙은 SEC β 종결 트리거로 기상, **TNV 집계 백필(07-26→08-03)·stale heat 재산출**을 완료했다. corpus는 동결된 적 없었고(정정), 실동결이던 TNV 집계는 병진 수동 백필로 07-25→08-01 전진(빈 키워드 4일 제외). heat는 전 창 재산출로 결손 TNV 성분을 반영했다. override(215 ovr_v1)·corpus 무접촉 입증. 잔여 = TNV 집계 beat 승격(결정 후보)·TH-OVR-RECUT(보류)·주말 키워드 공백 관찰.
