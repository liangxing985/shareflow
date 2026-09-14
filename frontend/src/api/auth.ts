import { post, get } from '@/utils/request'
import type { User } from '@/types'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return post('/auth/login', { username, password })
}

export function register(data: any): Promise<User> {
  return post('/auth/register', data)
}

export function refreshToken(refresh_token: string): Promise<LoginResponse> {
  return post('/auth/refresh', { refresh_token })
}

export function getCurrentUser(): Promise<User> {
  return get('/auth/me')
}
