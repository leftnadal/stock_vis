// 앵커 계약 — 가이드 데이터의 anchor ↔ 소스의 data-guide 속성이 어긋나지 않음을 보장 (D-GUIDE-TRACK)
//
// 오버레이는 CSS 셀렉터가 아니라 data-guide 속성만 참조하므로, 데이터와 JSX가 따로 움직이면
// 배지가 조용히 사라진다(무소음 실패). 이 테스트가 그 drift를 잡는다.
import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { GUIDE_SCREENS } from '@/lib/guide'

const ROOT = path.resolve(__dirname, '../..')
const SCAN_DIRS = ['app', 'components']

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    if (statSync(full).isDirectory()) {
      if (entry === 'node_modules' || entry === '.next') continue
      walk(full, out)
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

/** 소스에 실제로 박혀 있는 data-guide 앵커 → 등장한 파일 목록 */
function sourceAnchors(): Map<string, string[]> {
  const map = new Map<string, string[]>()
  for (const dir of SCAN_DIRS) {
    for (const file of walk(path.join(ROOT, dir))) {
      // 오버레이 자신은 속성을 "읽는" 쪽 — 선언부가 아니므로 제외
      if (file.includes(path.join('components', 'guide'))) continue
      const src = readFileSync(file, 'utf-8')
      for (const m of src.matchAll(/data-guide="([^"]+)"/g)) {
        const list = map.get(m[1]) ?? []
        list.push(path.relative(ROOT, file))
        map.set(m[1], list)
      }
    }
  }
  return map
}

// 가이드 등재 예정 앵커(고아 허용) — 유예는 면제가 아니고 **기한부**다.
// 날짜가 지나면 아래 '기한' 테스트가 스스로 터진다. allowlist가 조용히 자라는 것을
// 막는 유일한 구조다(D-GUIDE-ORPHAN-BACKBONE 애든덤, 2026-09-10).
//
// ⚠️ 감수하는 단점: 이것은 **코드 변경 없이 날짜만으로 RED가 되는 테스트**다. 일반적으로
//    안티패턴이지만(빌드 재현성을 시간에 결합시킨다) 여기서는 의도된 트립와이어다.
//    그래서 실패 메시지가 스스로를 설명해야 한다 — 무엇을, 왜, 어떻게 하면 되는지.
//
// 기한을 미루려면 그 결정을 DECISIONS.md에 남긴다. **코드에서 조용히 날짜만 바꾸지 말 것** —
// 그 순간 이 구조는 무한 연장 가능한 장식이 된다.
const PENDING_ANCHORS: Record<string, { until: string; why: string }> = {
  'chainsight.backbone': {
    until: '2026-09-30',
    why: '3e7b15c3(RC-C-1, 08-31) 도입·문구 미작성 — GUIDE-CS-REFRESH 2단계에서 등재',
  },
  'dashboard.tabs': {
    until: '2026-09-30',
    why: 'DASH-TAB(09-09) 도입·문구 미작성 — TASKQUEUE GUIDE-ORPHAN-DASHTABS, dashboard 트랙 소유',
  },
}

describe('data-guide 앵커 계약', () => {
  const declared = new Set(GUIDE_SCREENS.flatMap((s) => s.regions.map((r) => r.anchor)))
  const inSource = sourceAnchors()

  it('가이드 데이터가 선언한 앵커는 모두 소스에 존재한다', () => {
    const missing = [...declared].filter((a) => !inSource.has(a))
    expect(missing, `소스에 없는 앵커: ${missing.join(', ')}`).toEqual([])
  })

  it('소스에 박힌 앵커는 모두 가이드 데이터에 선언돼 있다 (고아 앵커 금지)', () => {
    const orphans = [...inSource.keys()].filter((a) => !declared.has(a) && !(a in PENDING_ANCHORS))
    expect(orphans, `데이터에 없는 앵커: ${orphans.join(', ')}`).toEqual([])
  })

  // 유예의 기한. 이 테스트만이 allowlist를 "언젠가 치우자"에서 "그날 치운다"로 바꾼다.
  it('PENDING_ANCHORS의 유예 기한이 지나지 않았다', () => {
    const today = new Date().toISOString().slice(0, 10)
    const expired = Object.entries(PENDING_ANCHORS)
      .filter(([, v]) => v.until < today)
      .map(
        ([anchor, v]) =>
          `${anchor} — 유예 기한 ${v.until} 만료 (오늘 ${today})\n` +
          `    사유: ${v.why}\n` +
          `    해결: ⑴ 가이드 데이터에 등재하고 PENDING_ANCHORS에서 제거 ` +
          `⑵ 또는 앵커(data-guide)를 소스에서 제거 ` +
          `⑶ 또는 기한 연장을 DECISIONS.md에 근거와 함께 남긴 뒤 until 갱신`,
      )

    expect(expired, `\n${expired.join('\n')}`).toEqual([])
  })

  // allowlist는 유예이지 면제가 아니다. 목록이 스스로 만료를 주장하게 만든다 —
  // 등재를 마치고 빼는 것을 잊으면(= 가드가 그 앵커에 영영 눈감으면) 여기서 걸린다.
  it('PENDING_ANCHORS는 죽은 항목을 남기지 않는다 (등재 완료·소스 삭제 시 제거)', () => {
    const stale = Object.keys(PENDING_ANCHORS).map((a) => {
      if (declared.has(a)) {
        return `${a} — 가이드 데이터에 등재 완료됐으니 PENDING_ANCHORS에서 제거하세요`
      }
      if (!inSource.has(a)) {
        return `${a} — 소스에서 사라졌으니 PENDING_ANCHORS에서 제거하세요`
      }
      return null
    })

    expect(stale.filter(Boolean), `\n${stale.filter(Boolean).join('\n')}`).toEqual([])
  })

  it('앵커는 한 파일에서만 선언된다 (중복 선언 시 배지 위치가 비결정적)', () => {
    const dup = [...inSource.entries()].filter(([, files]) => new Set(files).size > 1)
    expect(dup.map(([a]) => a), '여러 파일에 중복 선언된 앵커').toEqual([])
  })
})

// ── 앵커 ↔ 라우트 동거 (GUIDE-CS-GUARD-1) ────────────────────────────────
//
// 위 세 테스트는 앵커가 "레포 어딘가에" 있으면 통과한다. 그래서 2026-09-02 랜딩 역전
// (/chainsight: 이벤트 보드 → 이야기 피드)에서 앵커 3종이 EventBoard.tsx에 그대로 남아
// GREEN이었지만, 정문에서는 배지가 0개였다(09-04 야간 렌더 실증: anchor_chars 0).
// 선언과 사용처가 "같은 문맥"에 있는지까지 봐야 그 drift가 잡힌다.
//
// 알려진 한계: 조건부 렌더(에러 분기 안의 앵커)도 "도달 가능"으로 센다. 이 가드가 잡는
// 것은 그 라우트가 아예 import하지 않는 컴포넌트에 앵커가 있는 부류다. 런타임 진위는
// 야간 도그푸딩의 missing_anchors 관측(report_mail)이 사후에 보완한다.

const EXTENSIONS = ['.tsx', '.ts', '/index.tsx', '/index.ts']

/** import 지정자 → 실제 파일 경로. 로컬(@/ · 상대경로)만 해석하고 패키지는 null. */
function resolveLocal(spec: string, fromFile: string): string | null {
  let base: string
  if (spec.startsWith('@/')) base = path.join(ROOT, spec.slice(2))
  else if (spec.startsWith('./') || spec.startsWith('../')) base = path.resolve(path.dirname(fromFile), spec)
  else return null // node_modules · 패키지 import

  for (const ext of ['', ...EXTENSIONS]) {
    const candidate = base + ext
    try {
      if (statSync(candidate).isFile()) return candidate
    } catch {
      /* 없으면 다음 후보 */
    }
  }
  return null
}

/** 파일에서 시작해 로컬 import를 재귀적으로 따라간 모듈 그래프. */
function moduleGraph(entries: string[]): Set<string> {
  const visited = new Set<string>()
  const queue = entries.filter((f) => {
    try {
      return statSync(f).isFile()
    } catch {
      return false
    }
  })

  while (queue.length) {
    const file = queue.pop()!
    if (visited.has(file)) continue
    visited.add(file)

    const src = readFileSync(file, 'utf-8')
    const specs = [
      ...[...src.matchAll(/from\s+['"]([^'"]+)['"]/g)].map((m) => m[1]),
      ...[...src.matchAll(/import\s*\(\s*['"]([^'"]+)['"]\s*\)/g)].map((m) => m[1]),
    ]
    for (const spec of specs) {
      const resolved = resolveLocal(spec, file)
      if (resolved && !visited.has(resolved)) queue.push(resolved)
    }
  }
  return visited
}

/**
 * 라우트의 진입 파일들 — page.tsx + 그 위의 모든 layout.
 * App Router는 page와 조상 layout을 함께 렌더하므로 layout의 앵커도 도달 가능하다.
 */
function routeEntries(route: string): string[] {
  const segments = route.split('/').filter(Boolean)
  const out: string[] = []
  for (let i = 0; i <= segments.length; i++) {
    const dir = path.join(ROOT, 'app', ...segments.slice(0, i))
    out.push(path.join(dir, 'layout.tsx'), path.join(dir, 'layout.ts'))
  }
  const pageDir = path.join(ROOT, 'app', ...segments)
  out.push(path.join(pageDir, 'page.tsx'), path.join(pageDir, 'page.ts'))
  return out
}

describe('앵커는 자기 화면의 라우트에서 도달 가능하다', () => {
  const inSource = sourceAnchors()

  it.each(GUIDE_SCREENS.map((s) => [s.id, s] as const))(
    '%s — 선언 앵커가 모두 그 라우트의 모듈 그래프 안에 있다',
    (_id, screen) => {
      const entries = routeEntries(screen.route)
      expect(
        entries.some((f) => {
          try {
            return statSync(f).isFile()
          } catch {
            return false
          }
        }),
        `${screen.id} — route ${screen.route} 의 page 파일을 찾지 못했습니다`,
      ).toBe(true)

      const graph = moduleGraph(entries)
      const reachable = new Set<string>()
      for (const file of graph) {
        for (const m of readFileSync(file, 'utf-8').matchAll(/data-guide="([^"]+)"/g)) {
          reachable.add(m[1])
        }
      }

      const unreachable = screen.regions
        .map((r) => r.anchor)
        .filter((a) => !reachable.has(a))
        .map((a) => `${a} — 선언 route ${screen.route} 의 그래프에 없음 (실제 위치: ${
          (inSource.get(a) ?? ['소스 어디에도 없음']).join(', ')
        })`)

      expect(unreachable, `\n${unreachable.join('\n')}`).toEqual([])
    },
  )
})
