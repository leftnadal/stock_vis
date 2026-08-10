import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { SURFACES } from '@/constants/surfaces'

/**
 * SURFACES 가드 (D-C2-S1-CONST-UNIFY ⓒ-3 · S1-B2-SHARED).
 *
 * frontend 소스 전수 스캔(테스트 파일 제외) — SURFACES 모듈 외부에서 surface
 * 문자열 리터럴('dashboard_eod' 등)을 직접 사용하면 FAIL. 값 단일 출처 강제 +
 * 신규 stray 리터럴 유입 차단. 동결 목록(KNOWN_VIOLATIONS) 없음 — 치환 완료가 전제.
 */

const FRONTEND_ROOT = process.cwd() // vitest cwd = frontend/
const MODULE_REL = join('constants', 'surfaces.ts') // 단일 출처(허용)
const SURFACE_VALUES = Object.values(SURFACES)

// 주석(block/line)을 제거 — URL의 '://'는 line-comment로 오인하지 않는다.
function stripComments(src: string): string {
  const noBlock = src.replace(/\/\*[\s\S]*?\*\//g, '')
  return noBlock.replace(/(^|[^:])\/\/[^\n]*/g, '$1')
}

// 주석 제거 후 남은 코드에 surface 문자열 리터럴이 있으면 그 값을 반환(없으면 null).
function findSurfaceLiteral(source: string): string | null {
  const code = stripComments(source)
  for (const val of SURFACE_VALUES) {
    if (new RegExp(`['"]${val}['"]`).test(code)) return val
  }
  return null
}

function collectSourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (
        entry.name === 'node_modules' ||
        entry.name === '__tests__' ||
        entry.name.startsWith('.next')
      ) {
        continue
      }
      collectSourceFiles(full, acc)
    } else if (
      /\.(ts|tsx)$/.test(entry.name) &&
      !/\.(test|spec)\.(ts|tsx)$/.test(entry.name)
    ) {
      acc.push(full)
    }
  }
  return acc
}

describe('SURFACES guard — surface 리터럴 단일 출처', () => {
  // ── 케이스 1: 실 소스 전수 스캔 정상 통과 ──
  it('surfaces.ts 외부 소스에 surface 문자열 리터럴 직접 사용 = 0', () => {
    const files = collectSourceFiles(FRONTEND_ROOT).filter(
      (f) => relative(FRONTEND_ROOT, f) !== MODULE_REL,
    )
    // 스캔 대상이 실제로 수집됐는지 sanity (경로 가정 붕괴 시 조용한 pass 방지)
    expect(files.length).toBeGreaterThan(0)

    const offenders: string[] = []
    for (const file of files) {
      const val = findSurfaceLiteral(readFileSync(file, 'utf8'))
      if (val) offenders.push(`${relative(FRONTEND_ROOT, file).split(sep).join('/')} → '${val}'`)
    }
    expect(offenders).toEqual([])
  })

  // ── 케이스 2: 위반 시뮬 — 탐지 로직 실효성(positive/negative control) ──
  it('가드 탐지 로직: 코드 리터럴은 잡고 주석·URL은 무시', () => {
    // 위반(코드 내 raw 리터럴) → 탐지
    expect(findSurfaceLiteral(`const s = 'dashboard_eod'`)).toBe('dashboard_eod')
    expect(findSurfaceLiteral(`useTracker("news_chip", ref)`)).toBe('news_chip')
    // 비위반(주석) → 무시
    expect(findSurfaceLiteral(`// surface='coverage_detail' 발신`)).toBeNull()
    expect(findSurfaceLiteral(`/* 유기 노출 'dashboard_eod' 참고 */`)).toBeNull()
    // 비위반(URL '://'을 line-comment로 오인하지 않음 + 리터럴 없음) → 무시
    expect(findSurfaceLiteral(`const u = 'https://ex.com/news_chip-path'`)).toBeNull()
    // 상수 참조(SURFACES.X)는 리터럴이 아니므로 무시
    expect(findSurfaceLiteral(`const s = SURFACES.DASHBOARD_EOD`)).toBeNull()
  })

  // ── 케이스 3: 백엔드 SURFACE_CHOICES 값 스냅샷 동결 ──
  it('백엔드 SURFACE_CHOICES 값 스냅샷 동결 (2026-08-10 실측)', () => {
    // packages/shared/stocks/models.py:1263-1266 미러. 값 변경 시 백엔드 동반 갱신.
    expect([...SURFACE_VALUES].sort()).toEqual([
      'chain_sight',
      'coverage_detail',
      'dashboard_eod',
      'news_chip',
    ])
  })
})
