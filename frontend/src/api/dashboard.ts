import { get } from '@/utils/request'

export function getDashboardOverview(): Promise<any> {
  return get('/dashboard/overview')
}

export function getDashboardTrend(days: number = 7): Promise<any> {
  return get('/dashboard/trend', { days })
}

export function getShareholderRanking(limit: number = 10): Promise<any> {
  return get('/dashboard/shareholder-ranking', { limit })
}

export function getPlatformFeeTrend(days: number = 30): Promise<any> {
  return get('/dashboard/platform-fee-trend', { days })
}
