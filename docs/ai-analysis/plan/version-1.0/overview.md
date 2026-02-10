# Stock-Vis AI Analysis System v1.0

## GraphRAG + Token Optimization Architecture

**버전**: 1.0.0
**최종 수정**: 2025-12-13  
**마지막 변경 사항**: GraphRAG 통합, 토큰 최적화 파이프라인, 다층 캐싱

---

## 📋 목차

1. [Executive Summary](#1-executive-summary)
2. [핵심 변경사항 (v4.2.1 → v4.3)](#2-핵심-변경사항)
3. [전체 아키텍처](#3-전체-아키텍처)
4. [Phase 구성](#4-phase-구성)
5. [성능 목표](#5-성능-목표)
6. [기술 스택](#6-기술-스택)

---

## 1. Executive Summary

### 1.1 프로젝트 목표

Stock-Vis AI 분석 시스템은 사용자가 DataBasket에 담은 종목, 뉴스, 재무 데이터를 LLM이 분석하고, Knowledge Graph 기반으로 연관 종목을 탐험할 수 있는 시스템입니다.

### 1.2 v4.3의 핵심 철학

> **"얼마나 많이 넣느냐가 아니라, 얼마나 질 좋은 정보를 토큰 효율적으로 넣느냐"**

기존 RAG 방식의 한계를 극복하고, **GraphRAG + 토큰 최적화**를 통해:

- **토큰 사용량 88% 절감** (5,000 → 600 토큰)
- **응답 품질 향상** (노이즈 제거, 핵심 정보만 전달)
- **비용 87% 절감** ($0.015 → $0.002/분석)

### 1.3 핵심 차별화 포인트

```
┌─────────────────────────────────────────────────────────────────┐
│                 Stock-Vis의 차별화된 RAG 파이프라인              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Knowledge Graph로 "관계"를 안다                              │
│     → 단순 키워드 매칭이 아닌, TSMC-삼성 경쟁 관계를 이해        │
│                                                                  │
│  2. 관계 기반으로 검색 범위를 좁힌다                             │
│     → 전체 뉴스가 아닌, 관계된 종목의 뉴스만                     │
│                                                                  │
│  3. Reranking으로 핵심만 추린다                                  │
│     → 20개 → 3개                                                │
│                                                                  │
│  4. 압축해서 넣는다                                              │
│     → 500토큰 문서 → 30토큰 요약                                │
│                                                                  │
│  5. 캐싱으로 반복 질문은 스킵                                    │
│     → 유사 질문 85% 이상이면 캐시 히트                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 핵심 변경사항

### 2.1 v4.2.1 → v4.3 변경 요약

| 영역 | v4.2.1 | v4.3 | 개선 효과 |
|------|--------|------|-----------|
| **검색** | Vector Search만 | Hybrid (Vector + BM25 + Graph) | 정확도 ↑ |
| **필터링** | 없음 | 메타데이터 + Entity 기반 | 범위 축소 |
| **재순위화** | 없음 | Cross-Encoder Reranker | Top-K 선별 |
| **컨텍스트** | 전체 문서 주입 | 압축 + 계층화 | 토큰 88% ↓ |
| **캐싱** | Redis 기본 | 다층 (Redis + Neo4j Vector) | 응답 속도 ↑ |
| **그래프** | 단순 관계 조회 | GraphRAG 통합 점수 | 품질 ↑ |

### 2.2 새로 추가된 컴포넌트

```
신규 컴포넌트:
├── EntityExtractor (Haiku 기반)
├── HybridSearcher (Vector + BM25 + Graph)
├── CrossEncoderReranker
├── ContextCompressor (Haiku 기반)
├── SemanticCache (Neo4j Vector Index)
├── TokenBudgetManager
└── GraphRAGScorer
```

---

## 3. 전체 아키텍처

### 3.1 High-Level Flow

```
사용자 질문: "TSMC 실적이 삼성전자에 미치는 영향은?"
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 1: Entity Extraction                                      │
│  ─────────────────────────                                       │
│  Model: Claude Haiku (저렴)                                      │
│  Input: 사용자 질문                                              │
│  Output: [TSMC, 삼성전자, 실적, 영향]                            │
│  Token: ~50                                                      │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 2: Hybrid Search + Graph Traversal                        │
│  ─────────────────────────────────────────                       │
│                                                                  │
│  2a. Knowledge Graph 탐색 (Neo4j):                               │
│      TSMC ──[COMPETITOR]──→ 삼성전자                             │
│      TSMC ──[SUPPLIER]──→ NVIDIA, Apple                          │
│      → 관계 컨텍스트 생성                                         │
│                                                                  │
│  2b. Vector Search (sentence-transformers):                      │
│      → 질문 임베딩 기반 유사 문서 검색                           │
│                                                                  │
│  2c. BM25 Keyword Search:                                        │
│      → 정확한 고유명사 매칭 (종목코드, CEO 이름)                 │
│                                                                  │
│  2d. 메타데이터 필터:                                            │
│      → 날짜(최근 3개월) + 섹터(반도체) 필터링                    │
│                                                                  │
│  Token: 0 (검색 단계)                                            │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: Reranking + Compression                                │
│  ─────────────────────────────────                               │
│                                                                  │
│  3a. Cross-Encoder Reranker:                                     │
│      Input: 20개 후보 문서 × 질문                                │
│      Output: 관련성 점수 기반 Top-3 선택                         │
│                                                                  │
│  3b. Context Compression (Haiku):                                │
│      Input: "TSMC의 2024년 4분기 실적 발표에 따르면..." (500토큰)│
│      Output: "TSMC 24Q4: 매출 $20B(+15% YoY)" (30토큰)           │
│                                                                  │
│  Token: ~200 (압축 처리용)                                       │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 4: LLM Analysis                                           │
│  ─────────────────────                                           │
│  Model: Claude Sonnet                                            │
│                                                                  │
│  Input Context (~600 토큰):                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [Graph Context] ~200 토큰                                │   │
│  │ TSMC ↔ 삼성전자: 파운드리 경쟁 (점유율 54% vs 12%)       │   │
│  │ 공통 고객: NVIDIA, Apple, AMD                            │   │
│  │                                                          │   │
│  │ [Compressed Documents] ~300 토큰                         │   │
│  │ 1. TSMC 24Q4: 매출 $20B, AI 반도체 비중 30%로 확대       │   │
│  │ 2. 삼성 파운드리: 3nm 수율 개선, GAA 기술 적용           │   │
│  │ 3. 업계 전망: 2025 파운드리 시장 +8% 성장 예상           │   │
│  │                                                          │   │
│  │ [Question]                                               │   │
│  │ TSMC 실적이 삼성전자에 미치는 영향은?                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Output: 분석 결과 + 탐험 제안                                   │
│  Token: ~600 input + ~800 output                                │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  Stage 5: Response + Caching                                     │
│  ───────────────────────────                                     │
│                                                                  │
│  5a. SSE Streaming 응답                                          │
│  5b. 분석 결과 캐싱 (Redis + Neo4j)                              │
│  5c. 탐험 제안 파싱 및 표시                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 다층 캐싱 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     다층 캐싱 레이어                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: 브라우저 캐시 (클라이언트)                             │
│  ├── 정적 그래프 데이터                                          │
│  ├── 종목 기본 정보                                              │
│  └── TTL: 5분                                                    │
│                                                                  │
│  Layer 2: Redis 캐시 (애플리케이션)                              │
│  ├── LLM 응답 캐시 (질문 해시 기반)                              │
│  ├── Neo4j 쿼리 결과 캐시                                        │
│  ├── 압축된 종목 요약                                            │
│  └── TTL: 6시간                                                  │
│                                                                  │
│  Layer 3: Neo4j 벡터 인덱스 (시맨틱 캐시)                        │
│  ├── 과거 분석 세션 임베딩                                       │
│  ├── 유사도 0.85 이상 → 캐시 히트                                │
│  └── TTL: 7일                                                    │
│                                                                  │
│  Layer 4: PostgreSQL (영구 저장)                                 │
│  ├── 분석 히스토리                                               │
│  ├── 사용자별 인사이트                                           │
│  └── TTL: 무제한                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 구성

### 4.1 Phase 개요

| Phase | 기간 | 목표 | 핵심 산출물 |
|-------|------|------|-------------|
| **Phase 1** | 4주 | 동작하는 기본 시스템 | DataBasket, SSE, 기본 분석 |
| **Phase 2** | 4주 | 토큰 최적화 핵심 | GraphRAG, Reranker, Compression |
| **Phase 3** | 4주 | 완성 및 최적화 | 캐싱 고도화, 성능 튜닝, 모니터링 |

### 4.2 Phase별 상세 문서

- **Phase 1**: `AI_ANALYSIS_v4.3_PHASE1.md`
- **Phase 2**: `AI_ANALYSIS_v4.3_PHASE2.md`
- **Phase 3**: `AI_ANALYSIS_v4.3_PHASE3.md`

### 4.3 Phase 의존성

```
Phase 1 (기반)
    │
    ├── DataBasket CRUD
    ├── Neo4j 기본 연결
    ├── SSE 스트리밍
    └── 단일 프롬프트 분석
          │
          ▼
Phase 2 (토큰 최적화)
    │
    ├── Entity Extraction (Phase 1의 질문 처리 확장)
    ├── Hybrid Search (Phase 1의 Neo4j 활용)
    ├── Reranker (신규)
    └── Context Compression (신규)
          │
          ▼
Phase 3 (완성)
    │
    ├── Semantic Cache (Phase 2의 임베딩 활용)
    ├── GraphRAG 통합 점수 (Phase 2의 검색 고도화)
    ├── 성능 모니터링 (전체 파이프라인 측정)
    └── 비용 최적화 (모델 분리 전략)
```

---

## 5. 성능 목표

### 5.1 응답 시간 목표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| TTFT (Time To First Token) | ≤ 3초 | SSE 첫 청크 도착 |
| 전체 응답 완료 | ≤ 10초 | SSE complete 이벤트 |
| 캐시 히트 시 응답 | ≤ 500ms | Redis/Neo4j 캐시 |
| 그래프 쿼리 | ≤ 1초 | Neo4j 쿼리 실행 |

### 5.2 토큰 효율성 목표

| 방식 | 입력 토큰 | 비용 (Sonnet) | 품질 |
|------|----------|---------------|------|
| 기존 (전체 문서) | ~5,000 | $0.015 | 중 |
| Phase 1 (기본) | ~2,500 | $0.008 | 중상 |
| Phase 2 (최적화) | ~800 | $0.003 | 상 |
| Phase 3 (완성) | ~600 | $0.002 | 상 |

### 5.3 캐시 히트율 목표

| Phase | 목표 히트율 | 전략 |
|-------|------------|------|
| Phase 1 | 20% | Redis 기본 캐싱 |
| Phase 2 | 40% | + 종목 요약 사전 생성 |
| Phase 3 | 60% | + 시맨틱 캐시 |

---

## 6. 기술 스택

### 6.1 Backend

| 컴포넌트 | 기술 | 용도 |
|----------|------|------|
| Framework | Django 5.x + DRF | REST API |
| Async | asgiref, asyncio | SSE, 병렬 처리 |
| Task Queue | Celery + Redis | 백그라운드 작업 |
| Database | PostgreSQL 15 | 메인 데이터 |
| Graph DB | Neo4j Aura | Knowledge Graph |
| Cache | Redis 7 | 세션, 캐시 |

### 6.2 AI/ML

| 컴포넌트 | 기술 | 용도 |
|----------|------|------|
| Main LLM | Claude Sonnet | 분석 생성 |
| Light LLM | Claude Haiku | 추출, 압축 |
| Embedding | sentence-transformers | 벡터 검색 |
| Reranker | cross-encoder/ms-marco | 재순위화 |
| BM25 | rank_bm25 | 키워드 검색 |

### 6.3 Frontend

| 컴포넌트 | 기술 | 용도 |
|----------|------|------|
| Framework | Next.js 14 | React SSR |
| State | Zustand | 상태 관리 |
| Graph Viz | D3.js / vis-network | 그래프 시각화 |
| SSE Client | EventSource API | 스트리밍 |

---

## 📎 관련 문서

- `AI_ANALYSIS_v4.3_PHASE1.md` - Phase 1 상세 구현 가이드
- `AI_ANALYSIS_v4.3_PHASE2.md` - Phase 2 상세 구현 가이드
- `AI_ANALYSIS_v4.3_PHASE3.md` - Phase 3 상세 구현 가이드
- `SCREEN_DATA_STRUCTURE.md` - 데이터 구조 명세
- `CLAUDE_CODE_PROMPTS_v4.3.md` - Claude Code 실행용 프롬프트

---

*v4.3.0 - 2025-12-13*
*GraphRAG + Token Optimization Architecture*