# NEWS-AUTH Slice 1 배포 전 측정 (read-only)

- **일시**: 2026-06-15 측정
- **대상**: `581dc76` (monorepo/sess-news-auth, NEWS-AUTH Slice 1)
- **성격**: read-only 측정. merge/rebase/push/reset/checkout/branch-d 0. fetch + merge-tree/merge-base/log/rev-list만.
- **판정 요약**: **CASE A — 순수 fast-forward, 충돌 0, consolidation 불필요.** (메모리상 "diverged 숙제"는 현재 해소됨)

---

## 1. STEP 0 — 원격 갱신 결과
- `git fetch --all --prune`: **무변화**(신규 커밋 없음).
- **origin/main = `ffbe599`** | 2026-06-12 09:18:32 +0900 | leftnadal | "docs(meta): Phase 1 공식 종료".
- local main = `ffbe599` (현 worktree `/Users/byeongjinjeong/Desktop/stock_vis`).
- news-auth worktree: **clean** (uncommitted 0).

## 2. diverged 정량
| 비교 | 결과 | 해석 |
|------|------|------|
| `origin/main...main` (left/right) | **0 / 0** | local main == origin/main, **동기(diverged 아님)** |
| `origin/main...581dc76` | **0 / 1** | 581dc76가 origin/main보다 정확히 1커밋 앞섬 |
| merge-base(origin/main, 581dc76) | `ffbe599` | **= origin/main HEAD** → ff 가능 조건 충족 |
| local-only 커밋 (`origin/main..581dc76`) | `581dc76` (NEWS-AUTH Slice 1, 본 작업) | 보존 대상 = 이 1건뿐 |
| origin-only 커밋 (`581dc76..origin/main`) | **0건** | origin은 581dc76의 부분집합 |

→ **순수 ff** (581dc76의 부모가 곧 origin/main HEAD). diverged·미반영 로컬 작업 없음.

## 3. 581dc76 적재 판정 — CASE A (충돌 0)
- 변경 5파일: `services/news/api/views.py`(6 데코), `config/settings.py`(주석), `frontend/services/newsService.ts`(3함수), `frontend/components/news/NewsList.tsx`(catch), `DECISIONS.md`.
- **merge-tree 충돌 마커: 0건** (`git merge-tree $(merge-base origin/main 581dc76) origin/main 581dc76`).
- 5파일 모두 **merge-base(ffbe599) 이후 origin에서 추가 변경 0건** → 겹침 없음.
- 타 worktree/브랜치(cs-exp/ux-census/ux-s1/mgmt/nt11)가 이 5파일 건드린 것 **0건**.
- → **origin/main 위에 깨끗이 적재(충돌 0).**

## 4. 머지 방식 후보 (⚠️ 실행 금지 — 사용자 수동 게이트)

**권장: ff merge (CASE A, 가장 단순).**
```bash
# main worktree에서
cd /Users/byeongjinjeong/Desktop/stock_vis
git status                                  # clean + main 확인
git merge --ff-only monorepo/sess-news-auth # 581dc76가 main tip이 됨 (머지 커밋 없음)
git push origin main                        # origin 반영
```
- 충돌 해결·rebase·3-way 불필요. consolidation 동반 0.
- **파괴적 작업 없음.** push는 ff(원격도 ffbe599)이라 non-ff 거부 위험 없음.

**머지 후 정리 (선택 — 별도 표기):**
```bash
# 머지·검증 완료 후, 원하면:
git worktree remove /Users/byeongjinjeong/Desktop/stock_vis_news_auth   # worktree 제거
git branch -d monorepo/sess-news-auth                                   # ff 머지됐으므로 -d(안전) 가능
```
- ⚠️ 브랜치 삭제는 **머지+push 확인 후** 수동. `-d`(merged 안전 삭제)면 충분 — `-D`(강제) 불요.

## 5. consolidation 동반 범위
- **분리 가능 (동반 0).** local main ↔ origin/main 동기(0/0), 미반영 로컬 커밋 = 581dc76(본 작업)뿐.
- archive 태그(`archive/news-auth-premerge-*`) **불요** — 유실 위험 미머지 작업 없음.
- 이번 배포는 **순수 news-auth 머지로 종결.** 과거 consolidation 숙제는 이미 해소되어 본 트랙과 무관.

## 6. 머지 후 최종 확인 리마인드 (daphne 재기동 후 실측)
> APIClient 검증(공개 200 / 파생 401)은 코드 레벨 확정. **라이브 최종 확정**은 머지+daphne 재기동 후:
```bash
B=http://localhost:18765/api/v1
# 공개 6종 → 200 기대
for p in "news/all/?source=all&category=all&days=7&limit=3" news/daily-keywords/ news/trending/ news/sources/ news/insights/ "news/news-events/?symbol=AAPL"; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' "$B/$p")  /$p"
done
# 파생 2종 → 401 유지 기대
for p in news/recommendations/ news/stock/AAPL/; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' "$B/$p")  /$p"
done
```
- daphne는 main dir(현재 ffbe599) 서빙 → **머지 후 재기동해야 581dc76 코드 반영**. 재기동은 별도 승인(본 측정 세션 범위 밖).
- 기대: 공개 6 = 200, recommendations/stock = 401.
