import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import router from '@/router'

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const userStore = useUserStore()
    const status = error.response?.status
    const message = error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败'

    if (status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      userStore.logout()
      router.push({ name: 'Login' })
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (status === 422) {
      const details = error.response?.data?.detail
      if (Array.isArray(details)) {
        ElMessage.error(details.map((d: any) => d.msg).join('; '))
      } else {
        ElMessage.error('参数校验失败')
      }
    } else if (status === 500) {
      ElMessage.error(message || '服务器内部错误')
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export default request

// 通用请求方法（响应拦截器已返回response.data）
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return request.get(url, { params, ...config }) as unknown as Promise<T>
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return request.post(url, data, config) as unknown as Promise<T>
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return request.put(url, data, config) as unknown as Promise<T>
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request.delete(url, config) as unknown as Promise<T>
}
