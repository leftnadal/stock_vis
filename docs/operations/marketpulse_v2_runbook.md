# Market Pulse v2 — 운영 Runbook

## Daily checklist (한국 시간 기준)

| 시각 | task | 체크 포인트 |
|------|------|------------|
| 03:00 | `mp_purge_news_daily` | 90일 초과 미노출 뉴스 삭제 카운트 |
| 03:05 | `mp_purge_news_view_log_daily` | 24h+ 로그 삭제 |
| 05:30 (NY 16:30) | `mp_finalize_daily` | 4 스냅샷 finalize, mp:* 캐시 invalidate |
| 06:15 (NY 17:15) | `mp_generate_brief_daily` | BriefingLog status=OK / token 사용량 |
| 매시 :05 | `mp_fetch_news_hourly` | 6 카테고리 분포 |
| 평일 :*/5 | `mp_calc_breadth_5min`, `mp_calc_sector_5min`, `mp_detect_anomaly_5min` | 데이터 신선도 |
| 평일 17:15 | `mp_calc_concentration_daily` | top10 weight |
| 매 15분 | `mp_calc_regime_15min` | coverage ≥ 0.6 |

> 모든 schedule은 `python manage.py setup_marketpulse_beat`로 DB(`PeriodicTask`)에 등록 (Bug #28 회피).
> 등록 결과: 10 PeriodicTask (`mp_*`).

## 사전 체크 (배포 전)

```bash
# 1) env 변수 확인 (운영 .env)
grep -E "^(GEMINI_API_KEY|FMP_API_KEY|MARKETAUX_API_KEY|FRED_API_KEY|JWT_SIGNING_KEY|SECRET_KEY|NEO4J_PASSWORD)=" /path/to/prod/.env

# 2) DB 마이그레이션 plan
DJANGO_DEBUG=True poetry run python manage.py showmigrations macro marketpulse
# 적용 대상: macro 0002~0004 + marketpulse 0001
```

## 배포 단계

```bash
# 1. DB migrate
poetry run python manage.py migrate macro
poetry run python manage.py migrate marketpulse

# 2. Beat 등록 (멱등)
poetry run python manage.py setup_marketpulse_beat

# 3. FRED 신규 series 백필 (선택, 90일 권장)
poetry run python manage.py sync_marketpulse_v2_indicators --limit 365

# 4. Celery worker 재시작
brew services restart celery   # 또는 systemd / docker

# 5. Smoke test
TOKEN=$(curl -s -X POST -d 'username=...&password=...' /api/v1/users/token/ | jq -r '.access')
curl -H "Authorization: Bearer $TOKEN" /api/v2/market-pulse/overview | jq '._meta'
curl /api/v2/swagger/      # Swagger UI 노출 확인
```

## 비용 모니터링

- **Gemini token**: BriefingLog의 prompt_tokens + completion_tokens 매일 합산
- **FMP rate limit**: Starter Plan 300/min, 10,000/day (audit P0 #7) — 실측은 `/health` 응답의 `last_runs` 비교
- **Marketaux**: Basic Plan 일 2,500 calls — 1시간 주기 24회 호출 = 24/일, 충분

## Incident response

### Gemini LLM 실패 (KST 06:15)
1. `mp_generate_brief_daily.apply()` 재실행
2. CB 상태 확인: `get_circuit('gemini').get_state()` — OPEN이면 60s 후 자동 HALF_OPEN
3. 24h+ 실패 시 fallback 텍스트로 status=FAILED 명시

### FMP 외부 API 차단 (Circuit Breaker OPEN)
- 4 cb 상태:
  ```python
  for name in ('fmp_news', 'fmp_etf', 'gemini', 'marketaux'):
      print(name, get_circuit(name).get_state())
  ```
- 자동 회복 못 하면 `cb.reset()` + FMP 키/플랜 점검

### Coverage 미달 (RegimeSnapshot.status=INSUFFICIENT_DATA)
- `RegimeSnapshot.objects.latest('date').inputs` — 누락 키 확인
- `python manage.py sync_marketpulse_v2_indicators` 재실행
- VIX3M / MOVE는 FRED 미지원 — 별도 provider 필요 (후속 PR)

### Beat drift (Bug #28)
- DB 등록 확인: `PeriodicTask.objects.filter(name__startswith='mp_').values('name', 'enabled')`
- `python manage.py setup_marketpulse_beat` 재실행 (멱등)

## Rollback

- API: `config/urls.py`의 v2 mount 주석 처리
- Tasks: `setup_marketpulse_beat --disable`로 enabled=False
- Models: 마이그레이션 reverse_code 가능 (시드 row만 삭제, 기존 row 보존)

## Bug 참조

- #8 Celery LLM 비동기 금지 — Briefing은 동기 `genai.Client`만 사용
- #25 macOS fork SIGSEGV — 운영에서 `solo` pool 또는 `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`
- #28 Beat drift — DB 단일 진실의 소스
