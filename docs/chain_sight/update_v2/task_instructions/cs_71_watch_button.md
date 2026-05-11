# CS-7-1: Watch 버튼 + 탐색 흐름 통합

> **작업 번호**: CS-7-1
> **로드맵 버전**: v1.4 (신규)
> **목표**: 탐색 트레일에 Watch 버튼 추가
> **예상 소요**: 1일
> **선행 조건**: CS-5-5 완료 + CS-6-2 API 작동
> **산출물**: Watch 버튼 컴포넌트 + 토스트 UX

---

## Watch 버튼 노출 위치

| 위치 | 버튼 형태 | 트리거 |
|------|----------|--------|
| 탐색 트레일 바 | `📌 Watch` 아이콘 버튼 | 현재 탐색 경로 저장 |

⚠️ **v1.3 이후 추가 예정**: 체인 스토리 피드 카드(Next Best Chain, Hidden Hub)에도
Watch 버튼 노출 예정. Feed API(CS-4-11) 구현 후.

## 저장 시 UX

1. 즉시 저장 (CS-4-5 POST API 호출)
2. 토스트 메시지: "경로가 저장되었습니다"
3. 토스트에 secondary action: `Expand` / `Alternatives` / `Open Watchlist`

## 버튼 상태

- 미저장: 빈 핀 아이콘
- 저장됨: 채워진 핀 아이콘 + "Watching" 라벨
- is_watched 필드 기반 (CS-4-1 API 응답)

## 완료 기준

```
□ 탐색 트레일 바에 Watch 버튼 노출
□ 탭 → API 호출 → 토스트 → 아이콘 상태 변경
□ 이미 저장된 path는 "Watching" 표시
□ 토스트 secondary action 동작
```

→ **다음**: cs_72 (Watchlist UI)

**END OF DOCUMENT**
