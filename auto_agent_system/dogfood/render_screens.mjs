/**
 * AGENT-S2 — 렌더 후 DOM에서 "화면이 실제로 보여준 것"만 추출한다.
 *
 * 왜 별도 스크립트인가: 기존 e2e(frontend/e2e/*.spec.ts)는 route interception으로
 * 백엔드를 모킹한다 — 결정론 회귀에는 맞지만 "오늘 데이터로 답했는가"는 평가할 수
 * 없다. 여기서는 **라이브 :3000 + 실 로그인**으로 오늘의 실제 화면을 읽는다.
 *
 * 실행 트리: sv-worker-runtime에는 frontend/node_modules가 없다. 이 스크립트는
 * **sv-web-runtime/frontend를 cwd로** 실행해야 playwright가 해석된다(collect_rendered.py가 처리).
 *
 * 행동 규율(절대):
 *   - GET 네비게이션과 로그인 1회만. 클릭/폼 제출/POST·PUT·DELETE 금지.
 *   - 상태를 바꾸지 않는다. 실패 화면은 기록하고 계속한다.
 *
 * 출력: stdout에 JSON 1개(수집 결과). 로그는 stderr로.
 */

// playwright는 실행 트리 밖(sv-web-runtime/frontend/node_modules)에 있다. ESM은
// NODE_PATH를 무시하므로 절대 경로를 동적 import 한다(collect_rendered.py가 주입).
// playwright는 CommonJS라 동적 import 결과가 default에 감싸일 수 있다(interop).
const playwrightModule = process.env.DOGFOOD_PLAYWRIGHT_MODULE ?? 'playwright'
const _pw = await import(playwrightModule)
const chromium = _pw.chromium ?? _pw.default?.chromium
if (!chromium) {
  process.stderr.write(`[render] playwright 로드 실패: ${playwrightModule}\n`)
  process.exit(1)
}

const BASE = process.env.DOGFOOD_BASE_URL ?? 'http://localhost:3000'
const API = process.env.DOGFOOD_API_URL ?? 'http://127.0.0.1:18765'
const USER = process.env.DOGFOOD_USER ?? ''
const PASS = process.env.DOGFOOD_PASSWORD ?? ''
const NAV_TIMEOUT = Number(process.env.DOGFOOD_NAV_TIMEOUT ?? 25000)
const SETTLE_MS = Number(process.env.DOGFOOD_SETTLE_MS ?? 2500)
const MAX_CHARS = Number(process.env.DOGFOOD_MAX_CHARS ?? 1800)
// 앵커에서 이만큼도 못 건지면 화면 본문으로 보완한다(앵커 이름 drift 대비).
const MIN_ANCHOR_CHARS = Number(process.env.DOGFOOD_MIN_ANCHOR_CHARS ?? 200)

const log = (m) => process.stderr.write(`[render] ${m}\n`)

/** 화면 정의는 python(targets.py)이 stdin으로 넘긴다 — 목록 단일 출처 유지. */
async function readStdin() {
  const chunks = []
  for await (const c of process.stdin) chunks.push(c)
  return JSON.parse(Buffer.concat(chunks).toString('utf-8'))
}

/** API 직접 로그인 → 토큰. 폼 로그인보다 안정적이고 클릭이 없다(행동 규율). */
/** 미인증 사유를 구분해 남긴다 — 다음에 같은 증상이 오면 로그만으로 판별된다. */
let authFailReason = ''

async function login() {
  if (!USER || !PASS) {
    authFailReason = `자격증명 부재(DOGFOOD_USER=${USER ? '있음' : '없음'}, DOGFOOD_PASSWORD=${PASS ? '있음' : '없음'})`
    return null
  }
  const res = await fetch(`${API}/api/v1/users/jwt/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: USER, password: PASS }),
  })
  if (!res.ok) {
    authFailReason = `로그인 거부 status=${res.status}`
    log(`로그인 실패 status=${res.status}`)
    return null
  }
  const data = await res.json()
  const access = data.access ?? data.access_token ?? data.token
  const refresh = data.refresh ?? data.refresh_token ?? ''
  if (!access) {
    authFailReason = '로그인 응답에 access 토큰 없음'
    log('로그인 응답에 access 토큰 없음')
    return null
  }
  return { access, refresh }
}

function squash(text) {
  return (text ?? '').replace(/\s+/g, ' ').trim()
}

/**
 * 빈 상태 마커(실측 문구). 계정에 데이터가 없어서 비어 있는 화면은 coreQuestion으로
 * 채점하면 화면 탓이 아닌 점수가 나온다 → 채점 기준을 분기하기 위해 표시만 한다.
 * 문구가 바뀌면 감지가 풀리므로, 마커 외에 "비어있/없어요/0건" 휴리스틱을 함께 본다.
 */
const EMPTY_MARKERS = [
  '아직 모니터링 중인 대상이 없어요',
  '아직 포트폴리오가 비어있습니다',
  '데이터가 없습니다',
  '표시할 항목이 없습니다',
]
const EMPTY_HEURISTIC = /(아직[^.]{0,20}(없|비어)|비어있습니다|등록된[^.]{0,10}없)/

function detectEmptyState(text) {
  const t = squash(text)
  const hit = EMPTY_MARKERS.find((m) => t.includes(m))
  if (hit) return hit
  const m = t.match(EMPTY_HEURISTIC)
  return m ? m[0] : ''
}

async function collectScreen(page, screen) {
  const out = {
    id: screen.id,
    route: screen.route,
    title: screen.title,
    ok: false,
    error: null,
    regions: [],
    fallback_text: '',
    empty_regions: [],
    loading_stuck: [],
    console_errors: [],
    empty_state: '',
  }

  const consoleErrors = []
  const onConsole = (msg) => {
    if (msg.type() === 'error') consoleErrors.push(squash(msg.text()).slice(0, 200))
  }
  page.on('console', onConsole)

  try {
    const resp = await page.goto(`${BASE}${screen.route}`, {
      waitUntil: 'domcontentloaded',
      timeout: NAV_TIMEOUT,
    })
    if (resp && resp.status() >= 400) out.error = `HTTP ${resp.status()}`
    // 클라이언트 렌더 + 데이터 fetch가 끝나기를 기다린다. networkidle은 폴링이 있는
    // 화면에서 영영 오지 않으므로 고정 대기 + 짧은 idle 시도로 절충한다.
    await page.waitForTimeout(SETTLE_MS)
    try {
      await page.waitForLoadState('networkidle', { timeout: 4000 })
    } catch {
      /* 폴링 화면 — 무시 */
    }

    for (const anchor of screen.anchors ?? []) {
      const loc = page.locator(`[data-guide="${anchor}"]`).first()
      const region = { anchor, found: false, text: '' }
      try {
        if ((await loc.count()) > 0) {
          region.found = true
          region.text = squash(await loc.innerText({ timeout: 3000 })).slice(0, MAX_CHARS)
        }
      } catch (e) {
        region.text = ''
        region.error = squash(String(e)).slice(0, 120)
      }
      if (region.found && !region.text) out.empty_regions.push(anchor)
      out.regions.push(region)
    }

    // 앵커를 못 찾았거나, 찾았어도 내용이 사실상 비어 있으면 main 콘텐츠로 보완한다.
    // (가이드 앵커 이름이 실제 DOM과 어긋난 화면이 있다 — 2026-09-03 실측:
    //  chainsight 3/3 부재, monitor 3/4 부재. 앵커 1개만 잡혀 5자만 남는 일을 막는다.)
    const foundAny = out.regions.some((r) => r.found && r.text)
    const anchorChars = out.regions.reduce((n, r) => n + (r.text?.length ?? 0), 0)
    out.anchor_chars = anchorChars
    out.missing_anchors = out.regions.filter((r) => !r.found).map((r) => r.anchor)
    if (!foundAny || anchorChars < MIN_ANCHOR_CHARS) {
      const main = page.locator('main').first()
      const target = (await main.count()) > 0 ? main : page.locator('body')
      out.fallback_text = squash(await target.innerText({ timeout: 5000 })).slice(0, MAX_CHARS * 2)
    }

    // 로딩 잔류: 스켈레톤/스피너가 대기 후에도 남아 있으면 데이터가 안 온 것이다.
    for (const sel of ['[aria-busy="true"]', '.animate-pulse', '[data-loading="true"]']) {
      const n = await page.locator(sel).count()
      if (n > 0) out.loading_stuck.push(`${sel} × ${n}`)
    }

    out.empty_state = detectEmptyState(
      out.regions.map((r) => r.text).join(' ') + ' ' + out.fallback_text,
    )
    out.ok = Boolean((anchorChars > 0 || out.fallback_text) && !out.error)
  } catch (e) {
    out.error = squash(String(e)).slice(0, 200)
  } finally {
    page.off('console', onConsole)
    out.console_errors = consoleErrors.slice(0, 5)
  }
  return out
}

async function main() {
  const screens = await readStdin()
  const tokens = await login()
  log(tokens ? '로그인 성공' : `⚠️ 미인증 진행 — ${authFailReason || '사유 불명'}`)

  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1440, height: 2200 } })

  // 토큰은 localStorage에 심는다(authAxios가 읽는 자리). 로그인 폼 클릭 없음.
  if (tokens) {
    await context.addInitScript(
      ([a, r]) => {
        try {
          localStorage.setItem('access_token', a)
          if (r) localStorage.setItem('refresh_token', r)
        } catch {
          /* storage 접근 불가 — 미인증으로 진행 */
        }
      },
      [tokens.access, tokens.refresh],
    )
  }

  const page = await context.newPage()
  const results = []
  for (const screen of screens) {
    log(`→ ${screen.route}`)
    results.push(await collectScreen(page, screen))
  }

  await browser.close()
  process.stdout.write(
    JSON.stringify(
      {
        base_url: BASE,
        authenticated: Boolean(tokens),
        auth_fail_reason: tokens ? '' : authFailReason,
        screens: results,
      },
      null,
      2,
    ),
  )
}

main().catch((e) => {
  log(`치명 오류: ${e}`)
  process.exit(1)
})
