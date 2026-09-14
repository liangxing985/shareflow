import { get, post, put, del } from '@/utils/request'
import type { PaymentAccount, PageResponse, PageQuery } from '@/types'

export function getPaymentAccounts(params: PageQuery): Promise<PageResponse<PaymentAccount>> {
  return get('/payment-accounts', params)
}

export function createPaymentAccount(data: any): Promise<PaymentAccount> {
  return post('/payment-accounts', data)
}

export function updatePaymentAccount(id: number, data: any): Promise<PaymentAccount> {
  return put(`/payment-accounts/${id}`, data)
}

export function deletePaymentAccount(id: number): Promise<any> {
  return del(`/payment-accounts/${id}`)
}
