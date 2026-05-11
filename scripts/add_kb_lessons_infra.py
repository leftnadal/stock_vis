#!/usr/bin/env python3
"""
인프라/Celery/Neo4j 운영 교훈을 KB에 일괄 추가하는 스크립트
2026-04 대화에서 발견된 이슈 및 해결 패턴
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_kb.ontology_kb import OntologyKB
from shared_kb.schema import KnowledgeItem, KnowledgeType, ConfidenceLevel

kb = OntologyKB()

lessons = [
    {
        "title": "Neo4j C 확장 Celery fork SIGSEGV 방지 — Lazy Import 패턴",
        "content": """Celery prefork pool에서 Neo4j Python 드라이버의 C 확장이 부모 프로세스에서
로드되면 fork() 후 자식 워커에서 SIGSEGV(세그폴트)가 발생한다.

원인:
- neo4j 패키지의 C 확장(bolt 프로토콜)이 fork-unsafe
- Django autodiscover_tasks() → 모듈 import → __init__.py → neo4j 전이 import
- 부모에서 로드된 C 확장 상태가 자식에 복사되면 메모리 충돌

해결 패턴: __getattr__ lazy import
```python
# 모듈 __init__.py에서 neo4j를 전이적으로 import하는 모든 심볼을 lazy 처리
_LAZY_IMPORTS = {
    'Neo4jServiceLite': 'neo4j_service',
    'GraphRAGScorer': 'graphrag_scorer',  # neo4j_service 전이 import
    'SemanticCacheService': 'semantic_cache',  # neo4j_driver 전이 import
}

def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(f'.{_LAZY_IMPORTS[name]}', __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

주의사항:
- 직접 import뿐 아니라 전이 import도 추적해야 함 (A→B→neo4j)
- hybrid_search.py처럼 try/except 내부의 eager import도 체크
- 검증: `python -c "import 모듈; import neo4j"` — neo4j가 로드되면 안 됨

적용 파일:
1. rag_analysis/services/__init__.py (graphrag_scorer, semantic_cache 등)
2. news/services/__init__.py (NewsNeo4jSyncService)
3. rag_analysis/services/hybrid_search.py (__init__ 내부로 import 이동)

출처: Stock-Vis 2026-04 Celery SIGSEGV 디버깅""",
        "knowledge_type": KnowledgeType.TROUBLESHOOT,
        "domain": "tech",
        "tags": ["celery", "neo4j", "fork", "sigsegv", "lazy-import", "c-extension"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "Celery 다중 워커 FMP Rate Limit 방지 — task rate_limit 패턴",
        "content": """Celery에서 다수의 워커가 동시에 외부 API를 호출하면 rate limit을 초과한다.
apply_async(countdown=N)만으로는 불충분한 경우가 있다.

문제:
- sync_sp500_financials가 101개 태스크를 countdown=i*7로 발송
- 워커가 다른 작업으로 바빠 countdown 경과 후 한꺼번에 가져감
- 10 워커 × 3 FMP calls = 30 동시 호출 → rate limit 초과
- FMP fallback → Alpha Vantage → 대부분 "No data found"

해결: task-level rate_limit + countdown 이중 보호
```python
@shared_task(rate_limit='6/m')  # 워커당 분당 6회 제한
def update_financials_with_provider(symbol):
    ...

# 발송 시에도 countdown 유지 (이중 보호)
for i, symbol in enumerate(batch):
    update_financials_with_provider.apply_async(
        args=[symbol], countdown=i * 7
    )
```

계산:
- rate_limit='6/m' → 워커당 분당 6회
- 10 워커 × 6 = 60 태스크/분
- 60 × 3 FMP calls = 180 calls/분 (300 제한 내 안전)

핵심 교훈:
- countdown은 "최초 실행 가능 시점"을 제어하지만, 워커가 바쁘면 무시됨
- rate_limit은 실제 실행 속도를 강제하므로 더 안정적
- 두 가지를 조합하면 burst와 sustained 모두 방어 가능

출처: Stock-Vis 2026-04 FMP rate limit 디버깅""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["celery", "rate-limit", "fmp", "api", "countdown", "concurrency"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "django-celery-beat DatabaseScheduler 잔존 스케줄 문제",
        "content": """django-celery-beat의 DatabaseScheduler를 사용할 때,
celery.py의 beat_schedule에서 항목을 제거해도 DB에 이전 스케줄이 남아 계속 실행된다.

문제:
- beat_schedule dict에서 semantic-cache-stats 삭제 + 주석 처리
- 하지만 DB의 PeriodicTask 테이블에 enabled=True로 남아있음
- 결과: 매시간 get_semantic_cache_stats 실행 지속

확인 방법:
```python
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(task__icontains='semantic_cache')
for t in tasks:
    print(f'{t.name} enabled={t.enabled} crontab={t.crontab}')
```

해결:
```python
# 비활성화
PeriodicTask.objects.filter(name='semantic-cache-stats').update(enabled=False)
# 또는 빈도 변경
task = PeriodicTask.objects.get(name='semantic-cache-stats')
crontab, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='*/6', ...)
task.crontab = crontab
task.save()
```

교훈:
- beat_schedule dict는 "새 항목 추가/업데이트"만 하고 "삭제"는 안 함
- 스케줄 제거 시 반드시 DB도 함께 정리해야 함
- 운영 중 확인: `PeriodicTask.objects.filter(enabled=True)`

출처: Stock-Vis 2026-04 semantic cache stats 과도 실행 디버깅""",
        "knowledge_type": KnowledgeType.TROUBLESHOOT,
        "domain": "tech",
        "tags": ["celery", "celery-beat", "django-celery-beat", "database-scheduler", "periodic-task"],
        "confidence": ConfidenceLevel.VERIFIED
    },
    {
        "title": "Next.js Image 컴포넌트 Invalid URL 방어 패턴",
        "content": """Next.js <Image> 컴포넌트에 잘못된 형식의 URL이 전달되면
'Failed to construct URL: Invalid URL' TypeError가 발생한다.

문제:
- article.image_url이 truthy이지만 유효한 URL이 아닌 경우
- Next.js Image가 내부적으로 new URL(src) 호출 → TypeError
- 조건부 렌더링 `{article.image_url ? <Image ...> : <Placeholder>}`만으로 불충분

해결: URL 유효성 검사 함수 추가
```typescript
function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

// 사용
const hasValidImage = !!article.image_url && isValidUrl(article.image_url);

{hasValidImage ? (
  <Image src={article.image_url} ... />
) : (
  <PlaceholderIcon />
)}
```

적용 대상:
- 외부 API에서 받은 이미지 URL (뉴스, 프로필 등)
- 사용자 입력 URL
- DB에 저장된 URL (마이그레이션 중 깨진 데이터 가능)

출처: Stock-Vis 2026-04 NewsCard 이미지 렌더링 에러""",
        "knowledge_type": KnowledgeType.PATTERN,
        "domain": "tech",
        "tags": ["nextjs", "react", "image", "url-validation", "error-handling"],
        "confidence": ConfidenceLevel.VERIFIED
    },
]

# KB에 추가
added = 0
for lesson in lessons:
    item = KnowledgeItem(
        id=str(uuid.uuid4()),
        title=lesson["title"],
        content=lesson["content"],
        knowledge_type=lesson["knowledge_type"],
        tags=lesson["tags"],
        confidence=lesson["confidence"],
        domain=lesson["domain"],
        source="Stock-Vis 2026-04 운영/디버깅",
        created_by="claude-code",
    )
    try:
        kid = kb.add_knowledge(item)
        print(f"  ✅ {lesson['title'][:60]}... → {kid}")
        added += 1
    except Exception as e:
        print(f"  ❌ {lesson['title'][:60]}... → {e}")

print(f"\n총 {added}/{len(lessons)}개 등록 완료")

# 통계
stats = kb.get_stats()
print(f"\nKB 통계: {stats}")
