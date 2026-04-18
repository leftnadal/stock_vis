# CS-4-2: 탐색 제안 API

> **작업 번호**: CS-4-2
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: 맥락화된 카테고리 목록 반환
> **예상 소요**: 1~2일
> **선행 조건**: CS-4-1 완료
> **산출물**: `GET /api/stocks/{symbol}/chainsight/suggestions/`

---

## 엔드포인트

```
GET /api/stocks/{symbol}/chainsight/suggestions/
Response:
{
  "categories": [
    { "id": "supply_chain", "label": "공급망 체인", "count": 8,
      "description": "NVDA의 주요 공급/수요 기업" },
    { "id": "peer_compare", "label": "경쟁사 비교", "count": 12 },
    { "id": "theme_cluster", "label": "테마 클러스터", "count": 5 }
  ]
}
```

## 완료 기준

```
□ 종목별 카테고리 목록 반환
□ 각 카테고리에 count, description 포함
□ 카테고리 선택 → CS-4-1 API에 rel_types 필터로 연결 가능
```

→ **다음**: cs_43

**END OF DOCUMENT**
