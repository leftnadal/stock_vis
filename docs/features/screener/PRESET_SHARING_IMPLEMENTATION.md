# Phase 2.1: 프리셋 공유 시스템 구현 완료

## 개요

스크리너 프리셋 공유 시스템을 구현하였습니다. 사용자는 자신의 프리셋을 공개하고, 다른 사용자는 공유 코드로 조회 및 복사할 수 있습니다.

## 구현된 기능

### 1. share_preset (POST /api/v1/serverless/presets/{preset_id}/share)
- 프리셋 공유 코드 생성 (8자리 영숫자)
- is_public = True로 설정
- 중복 체크 및 재사용 가능

**요청**:
```bash
POST /api/v1/serverless/presets/123/share
```

**응답**:
```json
{
  "success": true,
  "data": {
    "share_code": "abc12345",
    "share_url": "https://stock-vis.com/screener/presets/shared/abc12345"
  }
}
```

### 2. get_shared_preset (GET /api/v1/serverless/presets/shared/{share_code})
- 공유 코드로 프리셋 조회
- 조회수(view_count) 자동 증가
- 공개 프리셋만 조회 가능

**요청**:
```bash
GET /api/v1/serverless/presets/shared/abc12345
```

**응답**:
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "고배당 우량주",
    "description": "배당수익률 5% 이상 + ROE 15% 이상",
    "filters_json": {...},
    "view_count": 150,
    "use_count": 50,
    "owner_email": "use***@example.com"
  }
}
```

### 3. import_preset (POST /api/v1/serverless/presets/import/{share_code})
- 공유 프리셋을 내 프리셋으로 복사
- 인증 필요 (IsAuthenticated)
- 복사본은 비공개(is_public=False)

**요청**:
```bash
POST /api/v1/serverless/presets/import/abc12345
Content-Type: application/json

{
  "name": "복사된 프리셋 이름"  # optional
}
```

**응답**:
```json
{
  "success": true,
  "data": {
    "id": 456,
    "message": "Preset imported successfully"
  }
}
```

### 4. trending_presets (GET /api/v1/serverless/presets/trending)
- 인기 프리셋 목록 (view_count, use_count 기준)
- 최근 N일 데이터 (기본값: 7일, 최대: 30일)
- 상위 10개 반환

**요청**:
```bash
GET /api/v1/serverless/presets/trending?days=7
```

**응답**:
```json
{
  "success": true,
  "data": {
    "count": 10,
    "days": 7,
    "presets": [
      {
        "id": 123,
        "name": "고배당 우량주",
        "view_count": 500,
        "use_count": 200,
        "share_code": "abc12345",
        ...
      }
    ]
  }
}
```

## 데이터베이스 변경

### ScreenerPreset 모델 추가 필드

```python
# 통계
use_count = models.IntegerField(default=0, help_text="사용 횟수")
view_count = models.IntegerField(default=0, help_text="조회 횟수 (Phase 2.1)")
last_used_at = models.DateTimeField(null=True, blank=True)

# 인덱스 추가
models.Index(fields=['is_public', '-view_count'])  # 트렌딩용
```

### 마이그레이션

```bash
python manage.py makemigrations serverless --name add_view_count_to_preset
python manage.py migrate serverless
```

**생성된 마이그레이션**: `serverless/migrations/0007_add_view_count_to_preset.py`

## URL 패턴

```python
# serverless/urls.py
path('presets/trending', views.trending_presets, name='trending-presets'),
path('presets/shared/<str:share_code>', views.get_shared_preset, name='get-shared-preset'),
path('presets/import/<str:share_code>', views.import_preset, name='import-preset'),
path('presets/<int:preset_id>/share', views.share_preset, name='share-preset'),
```

**순서 주의**: 구체적인 경로(`trending`, `shared`, `import`)가 동적 경로(`<int:preset_id>`)보다 먼저 와야 함.

## Serializer 변경

### ScreenerPresetSerializer
- `view_count` 필드 추가 (read_only)

### ScreenerPresetListSerializer
- `view_count` 필드 추가 (트렌딩 프리셋용)
- `share_code` 필드 추가 (공유 URL 생성용)

## 테스트 결과

**테스트 스크립트**: `test_preset_sharing.py`

```bash
python test_preset_sharing.py
```

**결과**: ✅ 모든 테스트 통과

1. ✅ 공유 코드 생성
2. ✅ 공유 프리셋 조회 (조회수 증가 확인)
3. ✅ 프리셋 복사 (인증 사용자)
4. ✅ 인기 프리셋 목록

## 보안 고려사항

### 1. 인증 및 권한
- `share_preset`: 소유자만 공유 가능
- `import_preset`: 인증된 사용자만 복사 가능
- `get_shared_preset`: 공개 API (is_public=True 필터)
- `trending_presets`: 공개 API

### 2. 프라이버시
- 소유자 이메일 마스킹: `abc***@domain.com`
- 복사본은 기본적으로 비공개(is_public=False)

### 3. 공유 코드 생성
- `secrets.token_urlsafe(6)[:8]` 사용 (암호학적으로 안전)
- 중복 체크 로직 포함
- 8자리 영숫자 (약 2.8조 조합 = 62^8)

### 4. Rate Limiting
- 현재 미구현
- 프로덕션 배포 시 추가 필요 (예: Django Ratelimit, Redis)

## 프론트엔드 통합 가이드

### 1. 프리셋 공유 버튼
```typescript
// 프리셋 공유 API 호출
const sharePreset = async (presetId: number) => {
  const response = await fetch(`/api/v1/serverless/presets/${presetId}/share`, {
    method: 'POST'
  });
  const { data } = await response.json();
  return data.share_url;  // 공유 URL 반환
};
```

### 2. 공유 프리셋 조회 페이지
```typescript
// /screener/presets/shared/[shareCode]
const SharedPresetPage = ({ shareCode }) => {
  const { data } = useQuery(['shared-preset', shareCode], () =>
    fetch(`/api/v1/serverless/presets/shared/${shareCode}`).then(r => r.json())
  );
  // ...
};
```

### 3. 프리셋 복사 버튼
```typescript
const importPreset = async (shareCode: string) => {
  const response = await fetch(`/api/v1/serverless/presets/import/${shareCode}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: '복사된 프리셋' })
  });
  const { data } = await response.json();
  return data.id;  // 복사된 프리셋 ID
};
```

### 4. 트렌딩 프리셋 목록
```typescript
const TrendingPresets = () => {
  const { data } = useQuery('trending-presets', () =>
    fetch('/api/v1/serverless/presets/trending?days=7').then(r => r.json())
  );
  // ...
};
```

## 다음 단계 (Phase 2.2)

- [ ] Chain Sight DNA 서비스 구현
  - 프리셋 결합 엔진
  - 3개 프리셋까지 AND/OR 조합
  - 결과 교집합/합집합 계산

- [ ] Phase 2.3: 투자 테제 빌더
  - AI 생성 투자 테제
  - 5개 Top Picks 추천
  - 리스크 요인 분석

## 참고 문서

- CLAUDE.md: 프로젝트 전체 아키텍처
- SCREENER_UPGRADE_PLAN.md: 스크리너 업그레이드 로드맵
- serverless/models.py: ScreenerPreset 모델 정의
- serverless/views.py: 프리셋 공유 API 구현

---

**구현 완료일**: 2026-01-29
**담당**: @backend
**테스트**: ✅ 통과 (4개 엔드포인트)
**마이그레이션**: ✅ 적용 (0007_add_view_count_to_preset)
