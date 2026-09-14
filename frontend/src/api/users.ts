import { get, post, put, del } from '@/utils/request'
import type { User, PageResponse, PageQuery } from '@/types'

export function getUsers(params: PageQuery): Promise<PageResponse<User>> {
  return get('/users', params)
}

export function createUser(data: any): Promise<User> {
  return post('/users', data)
}

export function updateUser(id: number, data: any): Promise<User> {
  return put(`/users/${id}`, data)
}

export function deleteUser(id: number): Promise<any> {
  return del(`/users/${id}`)
}
