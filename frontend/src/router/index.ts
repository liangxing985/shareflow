import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue'),
        meta: { title: '数据看板', icon: 'DataAnalysis' }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/orders/OrderList.vue'),
        meta: { title: '订单管理', icon: 'Document' }
      },
      {
        path: 'shareholders',
        name: 'Shareholders',
        component: () => import('@/views/shareholders/ShareholderList.vue'),
        meta: { title: '分账方管理', icon: 'User' }
      },
      {
        path: 'share-rules',
        name: 'ShareRules',
        component: () => import('@/views/rules/ShareRuleList.vue'),
        meta: { title: '分账规则', icon: 'Setting' }
      },
      {
        path: 'share-records',
        name: 'ShareRecords',
        component: () => import('@/views/rules/ShareRecordList.vue'),
        meta: { title: '分账明细', icon: 'Tickets' }
      },
      {
        path: 'settlements',
        name: 'Settlements',
        component: () => import('@/views/settlements/SettlementList.vue'),
        meta: { title: '结算管理', icon: 'Money' }
      },
      {
        path: 'payment-accounts',
        name: 'PaymentAccounts',
        component: () => import('@/views/payment/PaymentAccountList.vue'),
        meta: { title: '收款账户', icon: 'Wallet' }
      },
      {
        path: 'reconciliations',
        name: 'Reconciliations',
        component: () => import('@/views/reconciliation/ReconciliationList.vue'),
        meta: { title: '对账管理', icon: 'DocumentChecked' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/UserList.vue'),
        meta: { title: '用户管理', icon: 'Avatar', roles: ['admin'] }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/auth/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  document.title = `${to.meta.title || 'ShareFlow'} - ShareFlow分账系统`

  if (to.meta.requiresAuth !== false && !userStore.token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && userStore.token) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
