// monitorService 데이터 레이어 검증 (MON-P3-S0)
import { beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()
const post = vi.fn()
const patch = vi.fn()
const del = vi.fn()

vi.mock('@/lib/api/authAxios', () => ({
  authAxios: {
    get: (...a: unknown[]) => get(...a),
    post: (...a: unknown[]) => post(...a),
    patch: (...a: unknown[]) => patch(...a),
    delete: (...a: unknown[]) => del(...a),
  },
}))

import { monitorService } from '@/services/monitorService'

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  patch.mockReset()
  del.mockReset()
})

describe('monitorService', () => {
  it('list는 페이지네이션 응답을 언랩한다', async () => {
    get.mockResolvedValue({ data: { results: [{ id: '1' }], count: 1 } })
    const res = await monitorService.list()
    expect(res).toEqual([{ id: '1' }])
    expect(get).toHaveBeenCalledWith('/monitor/monitors/')
  })

  it('list는 배열 응답도 수용한다', async () => {
    get.mockResolvedValue({ data: [{ id: '2' }] })
    const res = await monitorService.list()
    expect(res).toEqual([{ id: '2' }])
  })

  it('경로에 /api/v1 중복이 없다 (baseURL 규약)', async () => {
    get.mockResolvedValue({ data: [] })
    await monitorService.list()
    const path = get.mock.calls[0][0] as string
    expect(path.startsWith('/monitor/')).toBe(true)
    expect(path).not.toContain('/api/v1')
  })

  it('create는 payload를 POST한다', async () => {
    post.mockResolvedValue({ data: { id: '3', target_ref: 'AAPL' } })
    const res = await monitorService.create({
      scope: 'stock',
      target_ref: 'aapl',
      name: '애플',
    })
    expect(post).toHaveBeenCalledWith('/monitor/monitors/', {
      scope: 'stock',
      target_ref: 'aapl',
      name: '애플',
    })
    expect(res.id).toBe('3')
  })

  it('evaluate는 평가 action을 POST한다', async () => {
    post.mockResolvedValue({ data: { monitor_id: '5', overall_score: 0.3 } })
    const res = await monitorService.evaluate('5')
    expect(post).toHaveBeenCalledWith('/monitor/monitors/5/evaluate/')
    expect(res.overall_score).toBe(0.3)
  })

  it('getCatalog는 scope로 카탈로그를 조회하고 indicators를 언랩한다', async () => {
    get.mockResolvedValue({ data: { scope: 'stock', indicators: [{ key: 'eod_composite' }] } })
    const res = await monitorService.getCatalog('stock')
    expect(get).toHaveBeenCalledWith('/monitor/catalog/', { params: { scope: 'stock' } })
    expect(res).toEqual([{ key: 'eod_composite' }])
  })
})
