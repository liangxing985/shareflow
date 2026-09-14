import { get, post } from '@/utils/request'
import type { Reconciliation, PageResponse, PageQuery } from '@/types'

export function getReconciliations(params: PageQuery): Promise<PageResponse<Reconciliation>> {
  return get('/reconciliations', params)
}

export function getReconciliation(id: number): Promise<Reconciliation> {
  return get(`/reconciliations/${id}`)
}

export function uploadStatement(platform: string, recon_date: string, file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  return post('/reconciliations/upload', formData, {
    params: { platform, recon_date },
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
