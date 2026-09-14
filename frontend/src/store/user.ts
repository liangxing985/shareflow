import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getCurrentUser } from '@/api/auth'

export interface UserInfo {
  id: number
  username: string
  email?: string
  full_name?: string
  role: string
  status: string
  avatar?: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('sf_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('sf_refresh_token') || '')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')

  async function login(username: string, password: string) {
    const res = await loginApi(username, password)
    token.value = res.access_token
    refreshToken.value = res.refresh_token
    localStorage.setItem('sf_token', res.access_token)
    localStorage.setItem('sf_refresh_token', res.refresh_token)
    await fetchUserInfo()
    return res
  }

  async function fetchUserInfo() {
    const res = await getCurrentUser()
    userInfo.value = res
    return res
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem('sf_token')
    localStorage.removeItem('sf_refresh_token')
  }

  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    isAdmin,
    login,
    fetchUserInfo,
    logout
  }
})
