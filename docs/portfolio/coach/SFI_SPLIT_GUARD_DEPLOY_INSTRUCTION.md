# SFI_SPLIT_GUARD_DEPLOY_INSTRUCTION — HALT ② 집행 (워커 배포·재기동 + beat 등록)

> 실행 세션 (prod-write 2건: 워커 재기동 · beat 등록). 승인문 본문 내장.
> 선행: origin/main 528c1571 랜딩 · migrate 0014 적용(stocks_stock_split 0행) · PeriodicTask 미등록.

## 절대 규칙
1. 브랜치·worktree 삭제 금지(D-BRANCH-DELETE-MANUAL). sess-split-guard·sv-split-guard = 병진 정리 후보(보고만).
2. 명시 prod-write 2건 외 금지. migrate 재실행 금지(showmigrations 확인만). makemigrations 산출물 발생 시 HALT.
3. GATE 실패 = 즉시 정지·원시값 보고(우회·재시도 금지).
4. 기대값도 캐시 — STEP 0 실측이 다르면 HALT.
5. STEP 0 거버넌스 grep(beat|worker|restart|prod) 상충 시 HALT.

## 내장 승인문
- 승인 A(워커 배포·재기동): 워커 런타임 트리를 origin/main 동기화 + celery worker/beat 재기동. GATE 통과 후만.
- 승인 B(beat 등록): `python manage.py sync_stock_splits_beat`. GATE C(워커 ingest_stock_splits 등록) 통과 후만. 등록 후 PeriodicTask 원시값 검증 보고.

## STEP 0 게이트
0-1 528c1571 ⊆ origin/main · 0-2 showmigrations 0014 [X] · 0-3 StockSplit 0행 ·
0-4 PeriodicTask portfolio-stock-splits-daily 부재 · 0-5 워커 트리·HEAD·기동방식 ·
0-6 inspect registered ingest_stock_splits 부재(구 코드) · 0-7 ET 17:00–20:00 구간 밖 · 0-8 거버넌스 grep 상충 0.

## Part A 워커 트리 동기화 → GATE A(HEAD ⊇ 528c1571)
## Part B 워커/beat 재기동(승인 A) → GATE B(프로세스 정상)
## Part C task 등록 검증 → GATE C(ingest_stock_splits registered)
## Part D beat 등록(승인 B) → GATE D(PeriodicTask enabled=True·crontab 19:45 dow1-5 ET)
## Part E 최종 보고 후 정지 (익일 recon은 별도 세션)
