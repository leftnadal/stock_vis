# C-3 작업 지시서 — Django 5.2 LTS 마이그레이션

> 대상: Claude Code 실행 환경
> 슬라이스: 보안 'C 계획' C-3 (마지막 보안 슬라이스)
> 작성 근거: 결정 사이클 4건 확정 — ① 목표 버전 5.2.14 ② channels/daphne 현행 유지 + ASGI 영구 게이트 ③ 2-스텝 커밋 구조 ④ 미처리 2건 분리 처리

---

## 0. 컨텍스트 & 작업 원칙

### 0.1 현재 위치

- 14슬라이스(백엔드 + API 6진입점) 완료. Slice 15(프론트 코치 화면) 진입 직전.
- 보안 'C 계획' C-1(프론트 hotfix)·C-2(백엔드 의존성) 종결. **C-3가 마지막.**
- C-1·C-2·C-3는 모두 `slice14`(`00dc18d`)에서 분기한 **독립 형제 브랜치**. C-3 종결 후 셋을 한 묶음으로 `slice14`에 머지 → 그 다음 Slice 15.

### 0.2 사전 조사 결과 (이미 확인됨 — 재조사 불필요)

- Django 5.1.7은 **보안 지원 종료 상태** (5.1 보안 수정은 2025-12 종료). → C-3는 지연된 작업.
- deprecation 경고 0건 / 미적용 마이그레이션 0 / 위험 표면 좁음.
- channels는 Django 5.2+ 공식 호환. daphne는 Django에 직접 의존하지 않는 ASGI 프로토콜 서버로 channels를 추종. → **channels/daphne 버전 변경 없음.** 대신 ASGI 통합 테스트를 회귀에 영구 추가(아래 Step 1).
- 5.2 LTS 최신 패치 = **5.2.14** (2026-05-05 보안 릴리스). 지원 종료 2028-04.

### 0.3 브랜치

```
git checkout 00dc18d
git checkout -b security/c3-django-52-lts
```

C-3 브랜치에 총 **3커밋**: ① 도입 housekeeping ② Step 0 ③ Step 1(종결).

### 0.4 작업 원칙 (HALT 규칙)

- **드리프트 게이트**: `makemigrations --check`가 변경을 감지하거나, 미적용 마이그레이션이 0이 아니면 → **즉시 중단, 커밋 금지, 병진에게 보고.** 조사상 0건이 예상되므로 비-0은 예상치 못한 드리프트 신호.
- **회귀 게이트**: 기존 740 회귀 중 Django 승격發 신규 실패가 1건이라도 발생하면 → **즉시 중단, 실패 테스트 목록 보고, 종결 단계 진입 금지.**
- LLM 호출 0 — C-3는 코드/의존성/문서 작업뿐. 예상 비용 $0.

---

## 도입 커밋 (커밋 #1) — C-2 문서 cryptography 표기 정정

C-2 종결 문서의 cryptography 항목이 사실과 다르게 적혀 있어 정정한다. 독립적이고 사소하므로 머지까지 떠다니지 않도록 C-3 첫 커밋으로 즉시 박제(결정 ④).

**대상 파일**: `docs/portfolio/coach/security/slices/c2_backend_deps.md`

**작업**:

1. 파일 내 cryptography 항목을 찾는다(현재 "메이저 경계 강제" 취지로 기술됨).
2. 다음 사실에 맞게 1줄 정정:
   - **틀린 표현**: cryptography를 "메이저 경계 강제"로 묘사
   - **정확한 사실**: `cryptography 46.0.3 → 46.0.7` **패치 업그레이드** + `pyproject.toml` 미명시 → **명시 승격**
3. 다른 항목·수치는 건드리지 않는다. 표기 정정 범위만.

**커밋 메시지 예**: `docs(c3): correct cryptography entry in c2 closing — patch bump, not major-boundary`

---

## Step 0 (커밋 #2) — Django 5.1.7 → 5.2.14 버전 승격 + 마이그레이션 점검

버전 승격과 검증을 분리하는 2-스텝 구조의 첫 단계(결정 ③). 이 커밋에는 **검증·문서를 넣지 않는다** — 오직 버전 핀 변경 + 마이그레이션 무드리프트 확인까지.

### S0-1. Python 버전 가드

- 프로젝트의 Python 버전을 확인한다(`python --version`).
- Django 5.2는 Python **3.10~3.14**만 지원. 범위 밖이면 → **중단, 보고.** (조사상 통과 예상.)

### S0-2. Django 버전 핀 변경

1. Django 핀이 어디 있는지 탐색한다 — `pyproject.toml`, `requirements*.txt`, `requirements/` 등. `grep -ri "django" pyproject.toml requirements*` 로 위치 확인. **경로를 추정하지 말고 실제로 찾을 것.**
2. Django 핀을 `5.1.7` → `~=5.2.14` 로 변경.
   - `~=5.2.14`는 `>=5.2.14, ==5.2.*` 의미 — 5.2 LTS 라인 내 향후 패치는 자동 흡수하되 5.3은 차단. LTS 라인에 맞는 핀.
3. 환경 동기화: `pip install -e .` 또는 프로젝트의 의존성 설치 방식대로 실행.
4. 설치 확인: `python -c "import django; print(django.get_version())"` → `5.2.14` 출력 확인.

### S0-3. channels/daphne — 변경 금지

- channels·daphne 버전은 **그대로 둔다**(결정 ②). 이미 5.2+ 호환. 검증은 Step 1의 ASGI 테스트가 담당.

### S0-4. 마이그레이션 드리프트 점검 (HALT 게이트)

1. `python manage.py makemigrations --check --dry-run`
   - 기대 결과: `No changes detected`
   - 변경이 감지되면 → **즉시 중단.** 어떤 앱/모델에서 무엇이 감지됐는지 출력 그대로 병진에게 보고. 커밋하지 않는다.
2. `python manage.py showmigrations` (또는 `migrate --plan`)
   - 미적용 마이그레이션이 **0**인지 확인. 0이 아니면 → 중단, 보고.

### S0-5. 커밋

- 위 게이트를 모두 통과한 경우에만 커밋.
- 포함 파일: `pyproject.toml`(+ 해당 requirements 파일).
- **커밋 메시지 예**: `chore(c3): bump Django 5.1.7 -> 5.2.14 LTS; migrations clean`

---

## Step 1 (커밋 #3, 종결) — 회귀 + ASGI 게이트 + 종결 문서

승격이 안전함을 검증하고, ASGI 영구 게이트를 추가하고, 슬라이스를 종결한다.

### S1-1. 전체 회귀 (HALT 게이트)

1. 전체 테스트 스위트 실행 (`pytest`).
2. 기준선: **740 전건 통과** (Slice 14 Step 0 시점 회귀 수).
3. Django 승격으로 인한 신규 실패가 1건이라도 있으면 → **즉시 중단.** 실패 테스트 전체 목록 + 실패 사유(traceback 요지)를 병진에게 보고. **종결 단계로 넘어가지 않는다.**

### S1-2. IDENTICAL 결정성 검증 (HALT 게이트)

- 프로젝트의 기존 IDENTICAL 검증 메커니즘을 실행 (새로 만들지 말 것 — 기존 스크립트/테스트 사용).
- 결과 **31/31 유지** 확인. 깨지면 → 중단, 어느 해시가 어긋났는지 보고.

### S1-3. ASGI 통합 테스트 신규 추가 (결정 ②의 영구 게이트)

channels consumer가 Django 5.2 위에서 정상 동작함을 회귀가 자동으로 보증하도록, ASGI 통합 테스트를 **영구 회귀 자산으로 추가**한다.

**작업**:

1. 기존 테스트 인프라를 먼저 확인 — consumer 테스트가 이미 있는지, async 테스트 설정(`pytest-asyncio` 또는 channels 테스트 유틸)이 갖춰져 있는지. 있으면 그 패턴을 재사용.
2. channels의 `WebsocketCommunicator`를 사용하는 통합 테스트를 작성. 테스트는 최소한 다음을 검증:
   - 프로젝트 ASGI application의 routing을 통해 WebSocket consumer에 연결 시도
   - `connected`가 `True` (핸드셰이크 성공)
   - 가능하면 간단한 메시지 송신 → 수신 round-trip 1회
   - `disconnect()` 정상 처리
3. 테스트 파일 위치: 기존 consumer/channels 앱의 테스트 디렉터리 관례를 따른다.
4. 이 테스트는 회귀 스위트에 포함되어 매 실행 시 돌아가야 한다.

**회귀 수 갱신**: 신규 테스트 N개 추가 → 총 회귀 `740 → 740+N`. 기존 740은 전건 통과 유지(S1-1), 신규 N건도 통과. 이는 Stock-Vis의 additive-test 패턴과 동일.

### S1-4. daphne consumer 기동 확인

- `daphne`로 ASGI application을 실제 기동해 consumer가 에러 없이 뜨는지 1회 확인 (예: `daphne -p <포트> <project>.asgi:application` 기동 → 로그상 정상 시작 확인 → 종료).
- S1-3의 자동 테스트가 본질을 커버하지만, 실서버 기동 경로도 한 번 눈으로 확인.

### S1-5. 종결 문서 작성

**신규 파일**: `docs/portfolio/coach/security/slices/c3_django52.md`

- 포함 내용: 작업 요약(5.1.7→5.2.14), 결정 4건 반영 근거, 게이트 결과(makemigrations clean / 회귀 740 / IDENTICAL 31/31 / ASGI 테스트 +N / daphne 기동 OK), 비용 $0, 커밋 3개 목록, 잔존 보안 부채 현황.
- 분량은 간결하게 — 결정·결과 보존 수준.

### S1-6. SECURITY_LEDGER 갱신

- `SECURITY_LEDGER.md`에 C-3 종결 항목 추가 (Django 5.1.7 EOL 해소, 5.2.14 LTS 진입).
- ⚠️ **머지 충돌 예고**: C-1·C-2 브랜치도 이 파일을 수정했다. C-3 브랜치의 변경은 정상 진행하되, 실제 통합은 C 묶음 머지 시점에 수행(아래 종결 체크리스트).

### S1-7. 종결 커밋

- 포함: 신규 ASGI 테스트 파일, `c3_django52.md`, `SECURITY_LEDGER.md`, (S1-3로 회귀 설정 파일이 바뀌었다면 그것도).
- **커밋 메시지 예**: `feat(c3): close Django 5.2 LTS migration — regression 740+N, IDENTICAL 31/31, ASGI gate added`

---

## C-3 KPI 매트릭스 (종결 보고에 포함)

| #   | KPI                   | 통과 기준                                         |
| --- | --------------------- | ------------------------------------------------- |
| K1  | Django 버전           | pyproject 핀 `~=5.2.14`, 런타임 `5.2.14` 확인     |
| K2  | Python 지원 범위      | 프로젝트 Python이 3.10~3.14 내                    |
| K3  | 마이그레이션 드리프트 | `makemigrations --check` → No changes detected    |
| K4  | 미적용 마이그레이션   | 0건                                               |
| K5  | 회귀 (기존)           | 740 전건 통과, Django 승격發 신규 실패 0          |
| K6  | IDENTICAL             | 31/31 유지                                        |
| K7  | ASGI 게이트           | 신규 통합 테스트 +N건 추가 및 통과                |
| K8  | daphne 기동           | consumer 정상 기동 확인                           |
| K9  | 비용                  | $0 (LLM 호출 0)                                   |
| K10 | 커밋 구조             | 3커밋 (housekeeping + Step0 + Step1)              |
| K11 | 문서                  | `c3_django52.md` 신설 + `SECURITY_LEDGER.md` 갱신 |

---

## 산출물 목록

1. `docs/portfolio/coach/security/slices/c2_backend_deps.md` — cryptography 표기 1줄 정정
2. `pyproject.toml` (+ 해당 requirements 파일) — Django `~=5.2.14` 핀
3. 신규 ASGI 통합 테스트 파일 — channels consumer 핸드셰이크 검증
4. `docs/portfolio/coach/security/slices/c3_django52.md` — C-3 종결 문서
5. `SECURITY_LEDGER.md` — C-3 항목 갱신
6. (해당 시) 신규 마이그레이션 파일 — 단 K3 통과 시 **0개가 정상**

---

## 종결 체크리스트 — C 묶음 머지 (C-3 종결 직후, 별도 작업)

C-3 종결 후 C-1·C-2·C-3를 한 묶음으로 `slice14`에 머지할 때:

- [ ] **SECURITY_LEDGER.md 3-브랜치 수동 통합** — C-1·C-2·C-3 세 브랜치가 모두 이 파일을 수정했으므로 머지 시 충돌 발생. 세 브랜치 최종본을 보고 수동 통합. (이 시점이 통합의 정석 시점 — C-3 브랜치에서 미리 풀지 말 것.)
- [ ] 머지 후 `slice14`에서 회귀 1회 재확인 (740+N 전건 + IDENTICAL 31/31).
- [ ] C 묶음 머지 완료 후 → Slice 15(프론트 코치 화면) 진입.
- ⏸ ML mini-slice(torch/transformers)는 후순위 별도 트랙 — C 묶음에 포함하지 않음.

---

## 한눈 요약

```
커밋1 (housekeeping)  : c2 문서 cryptography 표기 정정
커밋2 (Step 0)        : Django 5.1.7 → 5.2.14 핀 변경 + makemigrations 무드리프트 확인
커밋3 (Step 1, 종결)  : 회귀 740 + IDENTICAL 31/31 + ASGI 테스트 신규 +N + 종결문서/원장
HALT 게이트           : makemigrations 비-clean / 회귀 신규 실패 / IDENTICAL 깨짐 → 즉시 중단·보고
머지                  : C-3 종결 후 C 묶음 → slice14 (SECURITY_LEDGER 3-way 수동 통합)
```
