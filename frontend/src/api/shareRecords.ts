import { get, post } from '@/utils/request'
import type { ShareRecord, PageResponse, PageQuery } from '@/types'

export function getShareRecords(params: PageQuery): Promise<PageResponse<ShareRecord>> {
  return get('/share-records', params)
}

export function adjustRecord(id: number, actual_amount: number, reason: string): Promise<any> {
  return post(`/share-records/${id}/adjust`, null, { params: { actual_amount, reason } })
}

export function getShareRecordsStats(): Promise<any> {
  return get('/share-records/stats/summary')
}
