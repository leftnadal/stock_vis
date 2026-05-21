"""Slice 13 Part 1 — Portfolio Coach DRF API 패키지.

기존 순수 Django view(`portfolio/views.py`, `portfolio/urls.py`)는 무수정 유지.
본 패키지는 별도 경로(`/api/coach/e1/` etc.)에 DRF 기반 endpoint를 추가한다.

설계:
  - serializers.py: Pydantic 어댑터 (CommentaryInputE1/E1Output 위임)
  - views.py: APIView (POST /api/coach/e1/)
  - urls.py: DRF endpoint 라우팅
  - config/urls.py에 include 1줄 추가 — 기존 portfolio.urls와 별도 prefix
"""
