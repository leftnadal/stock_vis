# ⑳-3 S2-C-4 재분류 dry-run 분석 (gate v2, LLM·DB 무접촉)

입력 `review_batch.csv` 270건 → `reclassify_domain_batch` → `review_batch_v2.csv`.
gate v2 = S2-C-1(자가모순 필터) 적용. **THRESHOLD(0.75) 무변경.**

## 1. gate_class 변화 (v1 → v2)

| class | v1 | v2 | 비고 |
|-------|----|----|------|
| auto_candidate | 55 | 55 | 불변 |
| pending | 215 | 162 | ▼53 |
| noise_self_contradiction | — | 53 | 신규(자가모순 분리) |

## 2. A'/B'/C' 구획 재산정

| 구획 | 정의 | v1 | v2 | 건당 | 시간 |
|------|------|----|----|------|------|
| A' | 자가모순 패턴 일괄(타입 확정=노이즈) | 20 | **53** | 8s | 7m |
| B' | 개별 검수(진짜 타입변경·미지정·evidence 약) | 195 | **162** | 30s | 81m |
| C' | auto 스팟체크 | 55 | **55** | 10s | 9m |
| 계 | | 270 | 270 | | **~97m** (108m→) |

**B' = 162 > 120 → 감축 미달** (지시서 S2-C-4, HALT 아님).

## 3. 감축 미달 사유 (정직)

- **confidence 임계(0.75, 동결)가 지배 블로커.** 자가모순 53건 중 나머지 3검증
  통과는 **단 1건**; 52건은 conf<0.75로 재차 pending(38건은 target도 부재).
- B' 162건 블로커 분해: target없음 단독 62 · type변경/미지정+conf 등 복합 다수.
  target∧sig 통과인데 conf<0.75로만 막힌 건 7(conf 0.3~0.6).
- 즉 룰 튜닝(S2-C-1/2)은 review "성격"을 정정(타입변경 오인 119→진짜 66)하나,
  **volume 감축은 임계·evidence가 지배**. 실질 레버 = ⑴THRESHOLD 재튜닝(이번
  분포 확보로 별도 결정) ⑵EVIDENCE-CAP-REEXTRACT(재추출, 보류 등록).

## 4. S2-C-2 실효 (정직)

- CSV엔 stock_name·전체 evidence 없음 → target 재판정 **CSV 재현 불가**
  (target_in_basis는 v1 값 유지). S2-C-2는 코어 단위테스트로 검증, 실효는 차기
  라이브 배치에서 확인.
- target만 막힌(conf 통과) 62건 = 대부분 **100자 evidence 캡 절단·filer 암묵**
  → 나열 파싱으로 복구 불가 = **재추출 대상**(EVIDENCE-CAP-REEXTRACT).
- 심볼 단어경계 실패 auto(짧은 심볼 substring 오탐 후보) = **5건**(표기만, gate 미변경).
  예: CPAY↔V, MA↔V. 라이브 재배치 시 S2-C-2 단어경계 룰로 정정 예상.

## 5. 정규화

- normalize_tag 적용 → distinct **53종**(118→). 상위: 금융·결제·거래소 19 ·
  기타 17 · 클라우드·엔터프라이즈SW 15 · 헬스케어 9 · 자동차 9 · 반도체 9.
