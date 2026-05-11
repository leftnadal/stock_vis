# 작업 지시서 전수 검증 2차 — 40개 파일 분석

> **검증일**: 2026-04-17
> **대상**: 40개 파일 (이전 20개 + 신규 20개)

---

## 1. 구조 진단: 중복 파일 쌍 6개

Phase 4 통합 시절(cs_45~49) vs Phase 6 분리 후(cs_61~67)가 **모두 남아 있다**.

| Phase 4 (구) | Phase 6 (신) | 내용 | 어떤 게 최신? |
|-------------|-------------|------|------------|
| cs_45 (CS-4-5) | cs_62 (CS-6-2) | Watchlist CRUD | cs_62 (더 상세) |
| cs_46 (CS-4-6) | cs_63 (CS-6-3) | Summary Path | cs_63 (더 상세) |
| cs_47 (CS-4-7) | ❌ cs_64 없음 | Simple Actions | cs_47만 존재 |
| cs_48 (CS-4-8) | cs_65 (CS-6-5) | Recheck | cs_65 (더 상세) |
| cs_49 (CS-4-9) | cs_66 (CS-6-6) | Expand | cs_66 (훨씬 상세) |
| cs_4_10 (CS-4-10) | cs_67 (CS-6-7) | Alternatives | cs_67 |
| — | cs_61 (CS-6-1) | SavedPath 모델 | Phase 6 전용 |

**→ Phase 6 (cs_61~67)이 canonical. cs_45~49 + cs_4_10은 제거 대상.**

---

## 2. 🔴 CRITICAL: 모델 필드명 불일치 (cs_00 vs cs_61)

cs_00(Phase 0에서 생성)과 cs_61(Phase 6에서 검증)의 **SavedPath 모델 정의가 서로 다르다**.

| 필드 | cs_00 (Phase 0) | cs_61 (Phase 6) | 비고 |
|------|----------------|----------------|------|
| 경로 배열 | `full_path` | `path_nodes` | ⚠️ 이름 다름 |
| 경로 길이 | `path_length` (있음) | 없음 | cs_61에서 제거 |
| 재검사 수 | 없음 | `recheck_count` (있음) | cs_61에서 추가 |
| 탐색 의도 | `primary_intent` (있음) | 없음 | cs_61에서 제거 |
| 액션 필드 | `action` | `action_type` | ⚠️ 이름 다름 |
| user nullable | 아님 | nullable | cs_61이 MVP에 맞음 |
| source_slot 길이 | max_length=30 | max_length=40 | cs_61이 여유 |
| path_signature 길이 | max_length=60 | max_length=80 | cs_61이 여유 |

**결정 필요: 어떤 스키마가 canonical인가?**

---

## 3. 🔴 누락 파일

| 파일 | 역할 | 상태 |
|------|------|------|
| cs_64 (CS-6-4) | Simple Actions (archive/resolve) | ❌ Phase 6 버전 없음 (cs_47만 있음) |
| cs_71 (CS-7-1) | Watch 버튼 | ❌ 없음 (cs_57이 실질적 대응) |
| cs_72 (CS-7-2) | Watchlist UI | ❌ 없음 (cs_58이 실질적 대응) |
| cs_73 (CS-7-3) | Full Path View | ❌ 없음 (cs_59가 실질적 대응) |

---

## 4. 🟡 흐름 끊김

**Phase 5 (cs_51~cs_56)**
```
cs_51 → cs_52 → cs_53 → cs_54 → cs_55 → ❌ CS-7-1로 점프 (cs_56 건너뜀!)
cs_56 → cs_57 (cs_57은 Phase 7이어야 함)
```

수정안: cs_55 → cs_56 → "Phase 5 완료, Phase 6 착수"

**Phase 6 (cs_61~cs_67)**
```
cs_61 → cs_62 → cs_63 → ❌ cs_64 없음 → cs_65 → cs_66 → cs_67
cs_65 "→ 다음: CS-6-3 또는 CS-6-4" (CS-6-4 없음!)
```

**Phase 7 (cs_57~cs_59 → 재번호 필요)**
```
cs_57 → cs_58 → cs_59 (M5)
→ cs_71 → cs_72 → cs_73 (M5)로 재번호
```

---

## 5. 정리 계획 (추천)

### Step 1: 모델 필드명 통일 — 결정 필요

### Step 2: 구 파일 제거 (6개)
cs_45, cs_46, cs_47, cs_48, cs_49, cs_4_10 → 삭제 (Phase 6이 canonical)

### Step 3: 누락 파일 생성 (1개)
cs_64 (CS-6-4 Simple Actions) — cs_47에서 번호만 변경하면 됨

### Step 4: Phase 7 재번호 (3개)
cs_57 → cs_71, cs_58 → cs_72, cs_59 → cs_73

### Step 5: 흐름 링크 전체 수정
cs_55 → cs_56, cs_56 → "Phase 5 완료"
cs_67 → cs_71, cs_73에 M5

### 최종 파일 구조 (34개)
Phase 0: cs_00~03 (4개)
Phase 1: cs_11~13 (3개)
Phase 2: cs_21~25 (5개)
Phase 3: cs_31~33 (3개)
Phase 4: cs_41~44 (4개) — 그래프 API + Seed Node
Phase 5: cs_51~56 (6개) — 코어 프론트엔드
Phase 6: cs_61~67 (7개) — Watchlist 백엔드
Phase 7: cs_71~73 (3개) — Watchlist 프론트엔드
폐기: cs_45~49, cs_4_10 (6개)

---

**END OF DOCUMENT**
