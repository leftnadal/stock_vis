# 상신 — AGENT-S2.1: `sv sync` 1회 (오늘 밤 발화 전)

- **작성**: 2026-09-04 (CC · worktree `sv-agent-s21` / `monorepo/sess-agent-s21`)
- **마이그레이션**: **0건**. plist 무변경. launchd 조작 불요.

---

## ★ 긴급도

**09-05 05:20 발화 전에 `sv sync`가 되어야 한다.** 안 하면 오늘 밤도 미인증으로 돌아 **루브릭 평균 1.4/5 왜곡 메일**이 다시 발송된다(09-04 실증).

---

## 반영 절차

```bash
sv sync
```

`~/bin/sv` 래퍼가 worker 트리를 최신화한 뒤 3트리를 정렬하고 worker·beat·daphne를 재기동한다. **web 트리도 대상**이어야 한다 — `render_screens.mjs`가 거기 playwright로 실행되기 때문(통상 `sv sync`면 함께 정렬된다).

## 반영 후 확인 (다음 날 아침)

```bash
grep -E "자격증명|렌더 수집|루브릭" $(ls -t ~/stock-vis-nightly/logs/dogfood_*.log | head -1)
```

**합격 기준**: `자격증명 있음(.env 포함 조회)` → `렌더 수집 5/5 (인증)` → 루브릭 본 평균이 1점대가 아님. 메일 제목의 평균과 `[빈 상태]` 라벨 확인.

**실패 시 판별**: 로그의 미인증 사유가 구분돼 나온다 — `자격증명 부재(DOGFOOD_USER=없음, …)`(=`.env` 접근 실패) vs `로그인 거부 status=NNN`(=계정/비번 문제) vs `access 토큰 없음`(=응답 스키마 변경).

## 되돌리기

main에서 `git revert <머지 커밋>` → `sv sync`. 되돌리면 미인증 채점으로 회귀하지만 1단계 정량 점검과 메일은 영향 없다.

---

## 이번 변경 요약

| # | 내용 | 검증 |
|---|---|---|
| ① | `collect_rendered.py`가 `.env`를 직접 읽어 `DOGFOOD_*` **화이트리스트 키만** node에 주입 | **`env -i` 빈 환경에서 `렌더 수집 5/5 (인증)` 재현** |
| ② | 빈 상태 화면은 "안내가 충분한가" 기준으로 분기 채점 + `[빈 상태]` 라벨 + 평균 별도 트랙 | 같은 렌더로 **1.4/5 → 본 4.0/5**(빈 상태 2건 4.5/5 분리) |
| ③ | 앵커 원인 확정(등재만, 코드 무접촉) | monitor·portfolio 4건 = 빈 상태 조건부 / chainsight 3건 = route 불일치 |

유닛 **39 passed** · 회귀 **190 passed**(선존 2건 `test_targets.py`) · ruff 0 · health **❌0** · 메일 실발송 1통.
