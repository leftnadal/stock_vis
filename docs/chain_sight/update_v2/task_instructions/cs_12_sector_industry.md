# CS-1-2: Sector/Industry 노드 + 관계

> **작업 번호**: CS-1-2
> **로드맵 버전**: v1.4 (변경 없음)
> **목표**: :Sector ~11개, :Industry ~70개, BELONGS_TO 관계 ~1,000개
> **예상 소요**: 2~3시간
> **선행 조건**: CS-1-1 완료
> **산출물**: management command `load_sectors_to_neo4j`

---

## 구현

1. Stock 테이블에서 고유 sector/industry 추출
2. :Sector, :Industry 노드 생성
3. (:Industry)-[:BELONGS_TO_SECTOR]->(:Sector) 관계 생성
4. (:Stock)-[:BELONGS_TO_INDUSTRY]->(:Industry) 관계 생성
5. (:Stock)-[:BELONGS_TO_SECTOR]->(:Sector) 관계 생성

## 완료 기준

```
□ :Sector ~11개, :Industry ~70개
□ BELONGS_TO 관계 ~1,000개
□ MATCH (s:Stock)-[:BELONGS_TO_SECTOR]->(sec:Sector) RETURN sec.name, count(s) → 섹터별 분포 확인
```

→ **다음**: cs_13

**END OF DOCUMENT**
