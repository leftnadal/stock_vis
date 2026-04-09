# SEC-PR-3: Track A 키워드 필터 + Gemini Flash 추출

> **완료일**: 2026-04-04

## 생성된 파일

| 파일 | 역할 |
|------|------|
| `sec_pipeline/normalizer.py` | 섹션 텍스트 정규화 + Pass 1 키워드 필터 (30개 키워드) |
| `sec_pipeline/prompts.py` | PROMPT_VERSION='v1', SUPPLY_CHAIN_EXTRACTION_PROMPT |
| `sec_pipeline/extractor.py` | GeminiExtractor (gemini-2.5-flash, JSON mode, temp=0.1) |
| `sec_pipeline/validator_track_a.py` | 추출 검증 + confidence_grade 계산 + DB 저장 |

## 데이터 흐름

```
Item 1 + Item 7 텍스트
  ↓ normalize_section_all()
정제된 텍스트
  ↓ filter_paragraphs() — Pass 1 키워드 필터
상위 15개 관련 단락 (중복 제거)
  ↓ GeminiExtractor.extract_supply_chain() — Pass 2
LLM 추출 결과 (JSON)
  ↓ validate_supply_chain_result()
검증 완료 관계 리스트
  ↓ save_supply_chain_evidences()
SupplyChainEvidence (PostgreSQL)
```

## 테스트 결과

| 종목 | 필터링 단락 | Raw 관계 | Validated | 주요 타겟 |
|------|-----------|---------|-----------|----------|
| AAPL | 15 | 0 | 0 | (10-K에서 구체적 회사명 미언급) |
| NVDA | 15 | 8 | 8 | TSMC, Samsung, SK Hynix, Micron, Hon Hai, Wistron, Fabrinet |

- NVDA: 8개 관계 전부 CUSTOMER_OF, confidence 0.90 (high)
- AAPL: 10-K Item 1이 매우 일반적인 서술 → 회사명 추출 불가 (파이프라인 정상, 데이터 특성)

## Gemini API 패턴

- `from google import genai` + `genai.Client(api_key=...)` (프로젝트 표준)
- `client.models.generate_content(model=..., contents=..., config=...)`
- `thinking_budget=0` (빠른 응답, 추론 불필요)

## 다음 PR

→ SEC-PR-4: Celery tasks + 에러 핸들링
