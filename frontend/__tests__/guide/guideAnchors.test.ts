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

describe('data-guide 앵커 계약', () => {
  const declared = new Set(GUIDE_SCREENS.flatMap((s) => s.regions.map((r) => r.anchor)))
  const inSource = sourceAnchors()

  it('가이드 데이터가 선언한 앵커는 모두 소스에 존재한다', () => {
    const missing = [...declared].filter((a) => !inSource.has(a))
    expect(missing, `소스에 없는 앵커: ${missing.join(', ')}`).toEqual([])
  })

  it('소스에 박힌 앵커는 모두 가이드 데이터에 선언돼 있다 (고아 앵커 금지)', () => {
    const orphans = [...inSource.keys()].filter((a) => !declared.has(a))
    expect(orphans, `데이터에 없는 앵커: ${orphans.join(', ')}`).toEqual([])
  })

  it('앵커는 한 파일에서만 선언된다 (중복 선언 시 배지 위치가 비결정적)', () => {
    const dup = [...inSource.entries()].filter(([, files]) => new Set(files).size > 1)
    expect(dup.map(([a]) => a), '여러 파일에 중복 선언된 앵커').toEqual([])
  })
})
