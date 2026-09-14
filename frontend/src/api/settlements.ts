import { get, post } from '@/utils/request'
import type { Settlement, PageResponse, PageQuery } from '@/types'

export function getSettlements(params: PageQuery): Promise<PageResponse<Settlement>> {
  return get('/settlements', params)
}

export function getSettlement(id: number): Promise<Settlement> {
  return get(`/settlements/${id}`)
}

export function createSettlement(data: any): Promise<Settlement> {
  return post('/settlements', data)
}

export function batchCreateSettlements(data: any): Promise<any> {
  return post('/settlements/batch', data)
}

export function markTransferred(id: number, data: any): Promise<Settlement> {
  return post(`/settlements/${id}/transfer`, data)
}

export function confirmSettlement(id: number, data?: any): Promise<Settlement> {
  return post(`/settlements/${id}/confirm`, data || {})
}

export function cancelSettlement(id: number): Promise<any> {
  return post(`/settlements/${id}/cancel`)
}

export function exportTransferList(status?: string): Promise<Blob> {
  return get('/settlements/transfer-list/export', { status }, { responseType: 'blob' })
}

export function getSettlementStats(): Promise<any> {
  return get('/settlements/stats/summary')
}
