# PROGRESS.md — 하네스 상태 영속화 로그

> 이 파일은 모든 에이전트가 세션 시작 시 반드시 읽고, 세션 종료 시 반드시 업데이트한다.

## Harness Engineering 전환 완료

- **일자**: 2026-04-12
- **범위**: PROGRESS.md, DECISIONS.md, TASKQUEUE.md, contracts/, CLAUDE.md 하네스 프로토콜, 에이전트별 Sub CLAUDE.md, 하네스 적합도 추적
- **첫 리뷰**: 2026-04-13 — contracts/ 정합성 검증 6건 수정, @qa Evaluator 첫 검증 완료

---

## 현재 활성 작업

| Feature | Agent | Status | Blocker | Last Updated |
|---------|-------|--------|---------|--------------|
| Chain Sight v2 마켓 뷰 (redesign v1) | @backend + @frontend | QA 검증 완료 (91%), 커밋 대기 | 커밋 필요 | 2026-04-13 |
| 서비스 리모델링 (data_structure_remodeling_V1) | @backend | 브랜치 작업 중 | Chain Sight 마켓 뷰 머지 후 | 2026-04-12 |

---

## 완료된 작업 (최근 2주)

| Feature | Agent | Completed | Notes |
|---------|-------|-----------|-------|
| Alpha Vantage provider 전면 제거 | orchestrator | 2026-04-25 | df85496. -3001 lines, 26 files. PeriodicTask 좀비 2건(collect-sentiment-av-*) 삭제. .env/scripts/settings.local.json 평문 키 제거 |
| 보안: SSH 키 차단 + settings.local.json 평문 API 키 제거 + deny/ask 정책 | orchestrator | 2026-04-25 | d96e434. .gitignore에 OpenSSH/PEM 패턴 + dlswnl545/heaven545 명시. local 권한 정책 deny 11건/ask 12건 추가 |
| 마켓 그래프 초기 노드 간격 + zoomToFit 개선 | orchestrator | 2026-04-24 | b97408c. ResizeObserver, force 동적, onEngineStop fit |
| Chain Sight 시드 캐시 안정화 (#27) + Beat drift 복구 (#28) | orchestrator | 2026-04-24 | f50b3f3. settings_test.py LocMem 격리, SeedSnapshot 영속화, `_get_today_seeds` 3단 폴백, heat_score / sec-seed-relations PeriodicTask 재등록, snapshot cleanup 주간 배치 |
| 하네스 잔여 개선 3건 | orchestrator + @qa | 2026-04-13 | sec-pipeline 스펙 상세화, shared-types.ts 연결, QA 검증 |
| 하네스 contracts/ 정합성 검증 | @qa | 2026-04-13 | 6건 불일치 수정 (chainsight/validation API) |
| 하네스 엔지니어링 전환 | orchestrator | 2026-04-12 | PROGRESS/DECISIONS/TASKQUEUE/contracts/HARNESS_FITNESS |
| CLAUDE.md 최신화 (5개 앱, 버그 #25~26) | orchestrator | 2026-04-12 | a09662f |
| Chain Sight 단계별 설계 문서 3개 | orchestrator | 2026-04-10 | API/시드/UI_UX 설계 |
| Chain Sight 레거시 설계 문서 정리 | orchestrator | 2026-04-09 | 8a3eec1 |
| FMP rate limit 보호 강화 + NewsCard 방어 | @backend + @frontend | 2026-04-08 | ea45b44 |
| Validation peer group 전환 버그 수정 | @frontend | 2026-04-07 | 37c2b67 (버그 #26) |
| SEC Pipeline 전체 (17 PR) | @backend + @rag-llm | 2026-04-04 | 10-K 공급망+사업모델 추출 완료 |

---

## 다음 세션에서 할 일

- [ ] working tree 잔존 `docs/` 21개 deleted 처리 결정 (복원 / 삭제 확정 / 보류)
- [ ] Alpha Vantage 무료 티어 키 방치 확인 (revoke UI 부재 → 사실상 사문화로 처리하지만 만약을 위해 Alpha Vantage 계정 자체 비활성화 검토)
- [ ] Chain Sight 마켓 뷰 PR-1~7 커밋 (CS-R9)
- [ ] Thesis Control FE-PR-3 (대화형 빌더) 착수 (TC-3)
- [ ] 서비스 리모델링 Phase 1 계속 (SR-1)
- [ ] QA follow-up: chainsightService.ts fetch() → authAxios 통일
- [ ] QA follow-up: RelationCardPanel 에러 UI 추가
- [ ] 정기 시크릿 스캔 스크립트 도입 검토 (KB 큐 cdc4d19e 참고)
