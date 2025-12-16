# RAG Analysis 설치 가이드

## 1. 의존성 설치

```bash
# anthropic 패키지 설치
poetry add anthropic

# 또는 requirements.txt에 추가
echo "anthropic>=0.48.0" >> requirements.txt
pip install -r requirements.txt
```

## 2. 환경 변수 설정

`.env` 파일에 Claude API 키 추가:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_API_KEY_HERE
```

API 키는 [Anthropic Console](https://console.anthropic.com/)에서 발급받을 수 있습니다.

## 3. Django 설정 확인

`config/settings.py`에 다음이 포함되어 있는지 확인:

```python
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
```

## 4. 마이그레이션 실행

```bash
python manage.py makemigrations rag_analysis
python manage.py migrate rag_analysis
```

## 5. 설치 확인

```bash
DJANGO_SETTINGS_MODULE=config.settings python << 'PYEOF'
import django
django.setup()

# Import 테스트
from rag_analysis.services import (
    DateAwareContextFormatter,
    LLMServiceLite,
    ResponseParser,
    AnalysisPipelineLite
)

print("✅ All services imported successfully")

# API 키 확인
from django.conf import settings
if settings.ANTHROPIC_API_KEY:
    print("✅ ANTHROPIC_API_KEY is set")
else:
    print("⚠️ ANTHROPIC_API_KEY is not set")
PYEOF
```

## 6. 테스트 실행 (선택)

```bash
# 단위 테스트
pytest rag_analysis/tests/

# 특정 테스트만 실행
pytest rag_analysis/tests/test_models.py -v
```

## 7. 사용 예제

```python
from rag_analysis.models import DataBasket, AnalysisSession
from rag_analysis.services import AnalysisPipelineLite

# 세션 생성
session = AnalysisSession.objects.create(
    user=user,
    basket=basket,
    title="AAPL 분석"
)

# 파이프라인 실행
pipeline = AnalysisPipelineLite(session)

async for event in pipeline.analyze("AAPL의 실적 전망은?"):
    print(event)
```

## 트러블슈팅

### anthropic 패키지를 찾을 수 없음

```bash
poetry install
# 또는
pip install anthropic
```

### ANTHROPIC_API_KEY 설정 오류

```bash
# .env 파일 확인
cat .env | grep ANTHROPIC

# 환경 변수 직접 설정 (임시)
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Django 앱 등록 확인

`config/settings.py`의 `INSTALLED_APPS`에 `'rag_analysis'`가 포함되어 있는지 확인:

```python
INSTALLED_APPS = [
    ...
    'rag_analysis',  # RAG 기반 AI 분석
    ...
]
```

## 다음 단계

1. API 엔드포인트 구현 (views.py)
2. Celery 태스크 구현 (tasks.py)
3. WebSocket 스트리밍 구현 (consumers.py)
4. Frontend SSE 클라이언트 구현

자세한 내용은 `services/README.md`를 참고하세요.
