# SEC-PR-11~13: Phase 2 Track B + 서비스 레이어

> **완료일**: 2026-04-04

## 생성된 파일

| PR | 파일 | 역할 |
|----|------|------|
| 11 | `sec_pipeline/keywords_track_b.py` | 5개 필드별 BM 키워드 사전 + filter_paragraphs_track_b |
| 12 | `sec_pipeline/prompts.py` (수정) | PROMPT_VERSION_TRACK_B + BUSINESS_MODEL_EXTRACTION_PROMPT |
| 12 | `sec_pipeline/extractor.py` (수정) | GeminiExtractor.extract_business_model() |
| 12 | `sec_pipeline/validator_track_b.py` | validate + save_business_model_snapshot |
| 12 | `sec_pipeline/tasks.py` (수정) | extract_from_document Track B 구현 |
| 13 | `metrics/services/__init__.py` | 신규 |
| 13 | `metrics/services/business_model_service.py` | get_business_model, get_evidence, is_recurring |

## NVDA Track B 테스트 결과

```
direct_customer_contact: hybrid
contract_model: hybrid
recurring_revenue_signal: medium
channel_dependency: high_dependency
customer_concentration: diversified
confidence_grade: high (overall=0.82)
```

## 서비스 레이어 검증

| 테스트 | 결과 |
|--------|------|
| `get_business_model('NVDA', for_api=True)` → overall_confidence 없음 | ✅ |
| `get_business_model('NVDA', for_api=False)` → overall_confidence 있음 | ✅ |
| `get_business_model_evidence('NVDA')` → 5개 evidence | ✅ |
| `is_recurring_business('NVDA')` → None (hybrid) | ✅ |

## Phase 2 완료 상태

| PR | 상태 |
|----|------|
| SEC-PR-11 | ✅ Track B 키워드 사전 |
| SEC-PR-12 | ✅ Track B Gemini 추출 + 검증 + 저장 |
| SEC-PR-13 | ✅ 서비스 레이어 (for_api 게이트) |

→ **Phase 2 완료. Phase 3 (모니터링 + Intelligence) 또는 커밋 가능.**
