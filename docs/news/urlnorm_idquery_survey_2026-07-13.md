# NEWS-URLNORM-IDQUERY 설계 입력 — 전수 조사 (2026-07-13)

> 지시서 ⑨. **read-only** — 정규화 코드 변경 0 · 병합/삭제/백필 0 · 배포 0.
> 브랜치 `monorepo/sess-urlnorm-design`, base origin/main `85fe1b7`.
> AV 호출 0 · Marketaux 호출 0 · 쓰기 0 (전부 DB SELECT + 정규화 재현).

---

## 요약 (한 줄)

현행 정규화(`normalize_news_url`)는 **쿼리 전량 제거** = **S3 코드와 동일이며, 이미 런타임에 배포·활성**(워커 PID 80710, 07-13 11:31 재기동). 기존 저장분은 raw 보존이라 **아직 오병합 미발생(예방 단계)** 이나, **S3-활성 워커의 다음 수집 발화(collect_av_broad_news 07-14 01:00 UTC)부터 finviz.com/quote?t=TICKER 같은 공유경로 URL이 붕괴** → 서로 다른 티커가 한 기사로 병합돼 **co-mention 조작** 위험. 예방 시한이 임박했다.

---

## STEP 0 (실측)

- origin/main tip = `85fe1b7`.
- **워커 트리 HEAD = `3a3e921`(07-13 11:29 커밋), S3(`8fb59c3`)이 조상 = S3 코드 배포됨.** (지시서 ⑧ 시점 `b569f43`에서 전진 — 그 사이 worker_sync.)
- **실행 워커 프로세스**: PID **80710** = `Mon Jul 13 11:31:39 KST` 기동(= S3 머지 직후 → **S3 코드 로드·활성**). + 구 PID 57518(`Jul 2` 기동, 좀비 가능성 #33). beat PID 80714(11:31 기동).

---

## Part A — live vs S3 정규화 diff + 손상 판정

### A-1. 두 함수 diff (코드 실측)
라이브(`sv-worker-runtime`)와 origin/main(S3)의 `url_utils.normalize_news_url`는 **바이트 동일**:
```python
normalized = (url or "").strip().lower()
if "?" in normalized:
    normalized = normalized.split("?")[0]     # ← 쿼리 전량 제거
if normalized.endswith("/"):
    normalized = normalized[:-1]
```
→ **라이브 = 쿼리 전량 제거 = S3.** (별도 diff 없음 — 이미 같은 코드.)

### A-2. "이미 쿼리 전량 제거인가?" → **YES(코드상)**, 단 적용 이력이 provider별로 다름
- **finnhub / marketaux**: `normalize_url`(구 base 메서드도 쿼리 전량 제거)을 **항상** 호출 → 역사적으로 항상 strip. (marketaux 저·finnhub 극저 볼륨)
- **AV / FMP**: S3 이전엔 raw url 저장(미정규화) → **기존 저장분에 쿼리 보존(intact)**. S3가 AV/FMP로 확대.

### A-3. 손상 판정 → **예방 (기존 무손상), 단 시한 임박**
- **기존 저장분 collapse 미발생**: 공유경로 위험 URL(youtube 1,961·finviz 1,651)이 **distinct raw로 전부 잔존**(아래 Part C-3). AV/FMP가 raw 저장했기 때문. → **비가역 오병합 정황 없음 = HALT 미해당.**
- **미발생 근거**: S3-활성 워커(80710)는 11:31 기동, 이후 **수집 발화 0건**(collect_av 07-13 01:01은 재기동 전 구코드, FMP/market/category 수집은 07-10 이후 dormant). → 신규 collapse 아직 없음.
- 🔴 **그러나 예방이 아니라 임박한 방어**: S3가 **이미 배포·활성**이므로 "배포 전 선결" 게이트는 **이미 지나침**. **다음 발화(collect_av_broad_news 07-14 01:00 UTC)부터** AV broad가 finviz.com/quote?t=TICKER 페이지를 재수집하면 `finviz.com/quote`로 붕괴 → **서로 다른 티커 페이지가 1건으로 병합 = co-mention 조작(허위 공동언급 생성)**. → ⑩ 구현을 **07-14 01:00 UTC 이전**에 마쳐야 순수 예방 유지.

---

## Part B — 쿼리-파라미터 전수 인벤토리

- 총 URL **113,399**, 쿼리 보유 **13,173 (11.6%)**, 고유 query key **125**.

### B-1. 분류별 집계 (기준: TRACKING blocklist / ID_HINTS / 나머지 AMBIG)
| 분류 | 총 출현 | 고유 key |
|------|--------:|---------:|
| TRACKING (utm_*·fbclid·gclid·ref·source 등) | 7,400 | 8 |
| ID (v·t·id·idxno·no·p·q·symbol 등) | 5,023 | 11 |
| AMBIG (나머지) | 8,856 | 106 |

### B-2. 상위 key × 빈도 × provider × 도메인 (발췌)
| key | 빈도 | 분류 | 주 provider | 주 도메인 |
|-----|-----:|------|------------|-----------|
| `cid` | 7,230 | TRACKING? | FMP | zacks.com (campaign id — 사실상 tracking) |
| `v` | 1,962 | ID | FMP | youtube.com (영상 id) |
| `t` | 1,654 | ID | AV(=other) | finviz.com (티커) |
| `ty`·`ta`·`r`·`b`·`ov`·`s`·`p` | 각 300~1,574 | AMBIG/ID | AV(finviz) | finviz.com (차트/뷰 파라미터) |
| `ampmode` | 735 | AMBIG | other | m.uk.investing.com |
| `apiversion`·`domshim`·`noservercache`·`wcseo` 등 | 각 321 | AMBIG | other(msn) | msn.com (렌더링 파라미터) |
| `ocid`·`mod`·`ncid`·`amp` | 65~128 | AMBIG | other | msn/marketwatch/insidermonkey |

### B-3. provider id-param 집중도 (Blocklist vs Hybrid 지표)
- **ID 파라미터는 극소수 (도메인,key) 쌍에 집중**: youtube `v`(FMP, 1,962) + finviz `t`/`p`(AV, ~3,000) = ID 출현의 대부분. → **Blocklist(tracking만 제거·id 보존)로도 이 핵심 id는 안전 보존**.
- 단 **AMBIG 8,856(106 key)** 이 큼: msn 렌더링 파라미터·finviz 뷰 파라미터 등 **실질 무의미(제거해도 안전)** 인데 blocklist엔 없어 **잔존 → 과소제거(dedup 덜 됨, 그러나 데이터 손실 없음)**. → **Hybrid(blocklist + 도메인별 id-param 화이트리스트/렌더링파라미터 제거)** 가 finviz 뷰 파라미터·msn 렌더링 파라미터를 안전 정리할 여지.

### B-4. Blocklist가 놓칠 신규 tracking/무의미 key 후보 (관측 기준)
`cid`(zacks 캠페인), `ocid`·`ncid`(msn), `mod`(marketwatch), `amp`·`ampmode`(amp 렌더), `apiversion`·`domshim`·`noservercache`·`noservertelemetry`·`batchservertelemetry`·`renderwebcomponents`·`wcseo`(msn 렌더링), `lang`(언어변형 — 동일기사 병합 관점선 제거가 나을 수 있음, ambiguous).

---

## Part C — 회귀 골든셋 파티션 (행위보존 설계)

### C-1. 3분할 (총 113,399)
| 구분 | 개수 | 비율 | 처리 |
|------|-----:|-----:|------|
| (a) 무쿼리 | 100,226 | 88.4% | **IDENTICAL 유지 필수** |
| (b) tracking-only (쿼리 key 전부 tracking) | 42 | 0.0% | **IDENTICAL 유지 필수** |
| (c) id/ambig-query 포함 | 13,131 | 11.6% | 변경 허용 |
| **IDENTICAL 필수 (a+b)** | **100,268** | **88.4%** | 어떤 새 정규화든 불변 |

### C-2. 골든 입력→기대출력 표본 (⑩ 구현용, 코드 아님·데이터)
> 기대출력 = 제안 규칙("tracking-param만 제거, id-쿼리 보존")

| # | 구분 | 입력 URL(발췌) | S3 출력(현행) | 제안 기대출력 | 동일? |
|---|------|----------------|---------------|---------------|-------|
| 1 | (a) | `simplywall.st/stocks/us/.../armour` | 동일 | 동일 | ✅ IDENTICAL |
| 2 | (b) | `seekingalpha.com/article/4921213-weride-...?utm_...` | `.../4921213-weride-...` | `.../4921213-weride-...` | ✅ IDENTICAL |
| 3 | (c) | `newsfilecorp.com/release/150628?lang=fr` | `.../release/150628` | `.../release/150628?lang=fr` | ⚠ 상이(lang=ambiguous) |
| 4 | (c) | `youtube.com/watch?v=ABC` vs `?v=XYZ` | 둘다 `youtube.com/watch` **(collapse)** | `.../watch?v=ABC` / `?v=XYZ` **(보존)** | ✅ 변경(수정 목표) |
| 5 | (c) | `finviz.com/quote?t=AAPL` vs `?t=MSFT` | 둘다 `finviz.com/quote` **(collapse)** | `.../quote?t=AAPL` / `?t=MSFT` **(보존)** | ✅ 변경(수정 목표) |
| 6 | (c) | `msn.com/en-us/money/companies/sempra-appoints-cfo-...?ocid=..` | `.../sempra-appoints-cfo-...` | `.../sempra-appoints-cfo-...` (경로가 id) | ✅ 사실상 동일 |

### C-3. 실제 collapse 위험 부분집합 (변경의 핵심)
(c) 13,131 중 대부분은 **경로에 기사 id가 있어**(예 #6 msn, tradingview) S3·제안 모두 distinct → **collapse 무관**. 실제 위험 = **경로 공유 + 쿼리가 유일 구분자**인 그룹:

| 지표 | 값 |
|------|----|
| 공유경로 collapse 위험 그룹 | **22** |
| 붕괴될 distinct URL | 3,717 |
| **잉여(손실/오병합) 행** | **3,695** |
| **AV(sentiment=alpha_vantage) 연관 위험 그룹** | **21 (잉여 1,734)** |

도메인 집중: **youtube.com 1,961(FMP)** · **finviz.com 1,651(AV)** · ft 27 · lse 12 · webwire 10 · thelec 10 · (롱테일). → 즉 **collapse 위험은 사실상 youtube(FMP)·finviz(AV) 2도메인**. Hybrid의 도메인 화이트리스트가 이 둘만 잡아도 손실의 ~98% 방어.

> ⚠ finviz.com/quote?t=TICKER = AV broad가 티커별로 저장한 **1,675 distinct 페이지**. S3 정규화 시 전부 `finviz.com/quote`로 붕괴 → **한 "기사"에 다수 티커 엔티티가 뭉쳐 허위 co-mention 생성** = 데이터 손실을 넘어 **co-mention 조작**. (co-mention은 NewsEntity 2+ 심볼 기사를 관계로 추출하므로 직접 오염.)

---

## 설계 재료 요약 (⑩ 입력, 판단 보류)

1. **판정**: **예방**(기존 무손상) — 단 **S3 이미 배포·활성**이라 **다음 발화(07-14 01:00 UTC) 전 ⑩ 완료**해야 순수 예방 유지. 미완 시 finviz(AV)·youtube(FMP) collapse 시작.
2. **전략 지표**: id-param은 소수 (도메인,key)에 집중(youtube `v`·finviz `t`) → **Blocklist(tracking만 제거)로 핵심 id 보존 가능**. AMBIG 대량(msn 렌더링·finviz 뷰 파라미터)은 blocklist가 미제거 → **Hybrid(도메인별 규칙)** 로 안전 정리 여지.
3. **골든 회귀**: (a)+(b) **100,268행(88.4%) IDENTICAL 필수**, (c) 13,131 변경 허용(실 위험 22그룹/3,695행). 표본 6종(위 C-2).
4. **blocklist 확장 후보**: `cid`·`ocid`·`ncid`·`mod`·msn 렌더링 7종·`amp`/`ampmode` (B-4).
5. **선결 부채**: 좀비 워커 PID 57518(Jul 2) 잔존(#33) — collect 라우팅 이중 가능성, 별도 점검 후보.

---

## 회계

- **AV 호출 0 · Marketaux 호출 0 · 쓰기(병합/삭제/백필/배포) 0.** 전부 DB SELECT + 정규화 함수 재현(Python 계산). 정규화 코드·설정·모델·beat 무변경.
