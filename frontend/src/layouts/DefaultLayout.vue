<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <el-icon :size="24" color="#fff"><Money /></el-icon>
        <span v-if="!isCollapse" class="logo-text">ShareFlow</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.full_name || userStore.userInfo?.username }}</span>
              <el-tag size="small" :type="roleTagType">{{ roleText }}</el-tag>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import { UserFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)

const menuItems = [
  { path: '/dashboard', title: '数据看板', icon: 'DataAnalysis' },
  { path: '/orders', title: '订单管理', icon: 'Document' },
  { path: '/shareholders', title: '分账方管理', icon: 'User' },
  { path: '/share-rules', title: '分账规则', icon: 'Setting' },
  { path: '/share-records', title: '分账明细', icon: 'Tickets' },
  { path: '/settlements', title: '结算管理', icon: 'Money' },
  { path: '/payment-accounts', title: '收款账户', icon: 'Wallet' },
  { path: '/reconciliations', title: '对账管理', icon: 'DocumentChecked' },
  { path: '/users', title: '用户管理', icon: 'Avatar', roles: ['admin'] }
]

const visibleMenuItems = computed(() => {
  return menuItems.filter(item => {
    if (!item.roles) return true
    return item.roles.includes(userStore.userInfo?.role || '')
  })
})

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title as string || '')

const roleText = computed(() => {
  const map: Record<string, string> = {
    admin: '管理员',
    manager: '运营主管',
    finance: '财务',
    operator: '运营',
    viewer: '只读'
  }
  return map[userStore.userInfo?.role || ''] || '运营'
})

const roleTagType = computed(() => {
  const map: Record<string, string> = {
    admin: 'danger',
    manager: 'warning',
    finance: 'success',
    operator: '',
    viewer: 'info'
  }
  return map[userStore.userInfo?.role || ''] || ''
})

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      userStore.logout()
      ElMessage.success('已退出登录')
      router.push({ name: 'Login' })
    }).catch(() => {})
  } else if (command === 'profile') {
    ElMessage.info('个人信息功能开发中')
  }
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #001529;
  transition: width 0.3s;
  overflow: hidden;

  :deep(.el-menu) {
    border-right: none;
  }
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #ffffff1a;

  .logo-text {
    white-space: nowrap;
  }
}

.header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  &:hover {
    color: #409eff;
  }
}

.header-right {
  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    .username {
      font-size: 14px;
      color: #303133;
    }
  }
}

.main-content {
  background-color: #f0f2f5;
  padding: 0;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
