import { get, post, put } from '@/utils/request'
import type { Shareholder, PageResponse, PageQuery } from '@/types'

export function getShareholders(params: PageQuery): Promise<PageResponse<Shareholder>> {
  return get('/shareholders', params)
}

export function getShareholdersWithBalance(params: PageQuery): Promise<PageResponse<Shareholder>> {
  return get('/shareholders/with-balance', params)
}

export function getShareholder(id: number): Promise<Shareholder> {
  return get(`/shareholders/${id}`)
}

export function createShareholder(data: any): Promise<Shareholder> {
  return post('/shareholders', data)
}

export function updateShareholder(id: number, data: any): Promise<Shareholder> {
  return put(`/shareholders/${id}`, data)
}

export function toggleBlacklist(id: number): Promise<any> {
  return post(`/shareholders/${id}/toggle-blacklist`)
}

export function getShareholderRecords(id: number, params: PageQuery): Promise<PageResponse<any>> {
  return get(`/shareholders/${id}/records`, params)
}
