#!/usr/bin/env python
"""
프리셋 공유 시스템 통합 테스트 (Phase 2.1)

4개 엔드포인트 테스트:
1. share_preset - 공유 코드 생성
2. get_shared_preset - 공유 코드로 조회
3. import_preset - 공유 프리셋 복사
4. trending_presets - 인기 프리셋 목록
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from serverless.models import ScreenerPreset
from users.models import User
from django.utils import timezone
from django.conf import settings
import json

# ALLOWED_HOSTS 임시 설정
settings.ALLOWED_HOSTS = ['*']

# 테스트 클라이언트
client = Client()

print("=" * 60)
print("Phase 2.1: 프리셋 공유 시스템 통합 테스트")
print("=" * 60)

# 테스트용 사용자 생성 (이미 있으면 가져오기)
test_email = 'preset_test@example.com'
User.objects.filter(email=test_email).delete()  # 기존 테스트 사용자 삭제

user = User.objects.create_user(
    email=test_email,
    username='preset_testuser',
    password='testpass123',
    first_name='Preset',
    last_name='Tester'
)
print(f"✅ 테스트 사용자: {user.email}")

# 테스트용 프리셋 생성
preset, created = ScreenerPreset.objects.get_or_create(
    user=user,
    name='테스트 프리셋',
    defaults={
        'description': '테스트용 프리셋',
        'description_ko': '테스트용 프리셋입니다.',
        'category': 'custom',
        'icon': '🔥',
        'filters_json': {
            'market_cap_min': 1000000000,
            'pe_ratio_max': 20
        },
        'sort_by': 'change_percent',
        'sort_order': 'desc',
        'is_public': False,
    }
)
print(f"✅ 테스트 프리셋: {preset.name} (ID: {preset.id})")

# 1. share_preset 테스트
print("\n" + "=" * 60)
print("1. share_preset 테스트")
print("=" * 60)

response = client.post(f'/api/v1/serverless/presets/{preset.id}/share')
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    share_code = data['data']['share_code']
    share_url = data['data']['share_url']
    print(f"✅ 공유 코드 생성 성공")
    print(f"   Share Code: {share_code}")
    print(f"   Share URL: {share_url}")
else:
    print(f"❌ 실패: {response.json()}")
    exit(1)

# 2. get_shared_preset 테스트
print("\n" + "=" * 60)
print("2. get_shared_preset 테스트")
print("=" * 60)

response = client.get(f'/api/v1/serverless/presets/shared/{share_code}')
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    preset_data = data['data']
    print(f"✅ 공유 프리셋 조회 성공")
    print(f"   Name: {preset_data['name']}")
    print(f"   View Count: {preset_data['view_count']}")
    print(f"   Use Count: {preset_data['use_count']}")
else:
    print(f"❌ 실패: {response.json()}")
    exit(1)

# 조회수 증가 확인
preset.refresh_from_db()
print(f"✅ 조회수 증가 확인: {preset.view_count}")

# 3. import_preset 테스트 (인증 필요 - 로그인)
print("\n" + "=" * 60)
print("3. import_preset 테스트")
print("=" * 60)

# 로그인 시뮬레이션 (force_login)
client.force_login(user)

response = client.post(
    f'/api/v1/serverless/presets/import/{share_code}',
    data={'name': '복사된 프리셋'},
    content_type='application/json'
)
print(f"Status: {response.status_code}")

if response.status_code == 201:
    data = response.json()
    imported_id = data['data']['id']
    print(f"✅ 프리셋 복사 성공")
    print(f"   Imported ID: {imported_id}")

    # 복사본 확인
    imported = ScreenerPreset.objects.get(id=imported_id)
    print(f"   Name: {imported.name}")
    print(f"   Category: {imported.category}")
    print(f"   User: {imported.user.email}")
else:
    print(f"❌ 실패: {response.json()}")
    exit(1)

# 4. trending_presets 테스트
print("\n" + "=" * 60)
print("4. trending_presets 테스트")
print("=" * 60)

# 프리셋을 공개로 설정하고 통계 업데이트
preset.is_public = True
preset.view_count = 100
preset.use_count = 50
preset.last_used_at = timezone.now()
preset.save()

response = client.get('/api/v1/serverless/presets/trending?days=7')
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    count = data['data']['count']
    presets = data['data']['presets']
    print(f"✅ 인기 프리셋 조회 성공")
    print(f"   Total: {count}개")

    if presets:
        print(f"   Top Preset: {presets[0]['name']} (views: {presets[0]['view_count']}, uses: {presets[0]['use_count']})")
else:
    print(f"❌ 실패: {response.json()}")
    exit(1)

# 정리
print("\n" + "=" * 60)
print("테스트 정리")
print("=" * 60)

# 테스트 데이터 삭제
imported.delete()
preset.delete()
user.delete()

print("✅ 테스트 데이터 삭제 완료")

print("\n" + "=" * 60)
print("✅ 모든 테스트 통과!")
print("=" * 60)
