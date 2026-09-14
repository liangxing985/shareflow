import { get, post, put, del } from '@/utils/request'
import type { ShareRule, PageResponse, PageQuery } from '@/types'

export function getShareRules(params: PageQuery): Promise<PageResponse<ShareRule>> {
  return get('/share-rules', params)
}

export function getShareRule(id: number): Promise<ShareRule> {
  return get(`/share-rules/${id}`)
}

export function createShareRule(data: any): Promise<ShareRule> {
  return post('/share-rules', data)
}

export function updateShareRule(id: number, data: any): Promise<ShareRule> {
  return put(`/share-rules/${id}`, data)
}

export function deleteShareRule(id: number): Promise<any> {
  return del(`/share-rules/${id}`)
}

export function setDefaultRule(id: number): Promise<any> {
  return post(`/share-rules/${id}/set-default`)
}
