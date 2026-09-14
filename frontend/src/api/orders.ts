import { get, post, put } from '@/utils/request'
import type { Order, PageResponse, PageQuery } from '@/types'

export function getOrders(params: PageQuery): Promise<PageResponse<Order>> {
  return get('/orders', params)
}

export function getOrder(id: number): Promise<Order> {
  return get(`/orders/${id}`)
}

export function createOrder(data: any): Promise<Order> {
  return post('/orders', data)
}

export function apiCreateOrder(data: any): Promise<Order> {
  return post('/orders/api/create', data)
}

export function updateOrder(id: number, data: any): Promise<Order> {
  return put(`/orders/${id}`, data)
}

export function reshareOrder(id: number, share_rule_id?: number): Promise<any> {
  return post(`/orders/${id}/reshare`, null, { params: { share_rule_id } })
}

export function getOrderStats(): Promise<any> {
  return get('/orders/stats/summary')
}
