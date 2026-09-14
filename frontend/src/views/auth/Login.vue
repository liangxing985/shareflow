<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <el-icon :size="48" color="#409eff"><Money /></el-icon>
        <h1>ShareFlow 分账系统</h1>
        <p>个人收款 · 智能分账 · 批量结算</p>
      </div>

      <!-- 登录表单 -->
      <el-form v-if="mode === 'login'" ref="loginFormRef" :model="loginForm" :rules="loginRules" class="login-form">
        <el-form-item prop="username">
          <el-input v-model="loginForm.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">登 录</el-button>
        </el-form-item>
      </el-form>

      <!-- 注册表单 -->
      <el-form v-else ref="registerFormRef" :model="registerForm" :rules="registerRules" class="login-form">
        <el-form-item prop="username">
          <el-input v-model="registerForm.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="full_name">
          <el-input v-model="registerForm.full_name" placeholder="姓名（可选）" size="large" :prefix-icon="UserFilled" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="密码（至少6位）" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleRegister" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleRegister">注 册</el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p v-if="mode === 'login'">
          还没有账号？<el-link type="primary" :underline="false" @click="mode = 'register'">立即注册</el-link>
        </p>
        <p v-else>
          已有账号？<el-link type="primary" :underline="false" @click="mode = 'login'">返回登录</el-link>
        </p>
        <p class="tip">首个注册用户自动成为管理员</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, UserFilled, Money } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { register } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度3-20位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function handleLogin() {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(loginForm.username, loginForm.password)
      ElMessage.success('登录成功')
      const redirect = route.query.redirect as string || '/dashboard'
      router.push(redirect)
    } catch (e: any) {
      // 错误已在拦截器处理
    } finally {
      loading.value = false
    }
  })
}

async function handleRegister() {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await register({
        username: registerForm.username,
        password: registerForm.password,
        full_name: registerForm.full_name || undefined
      })
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      loginForm.username = registerForm.username
      loginForm.password = ''
    } catch (e: any) {
      // 错误已在拦截器处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 420px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;

  h1 {
    font-size: 24px;
    color: #303133;
    margin: 12px 0 8px;
  }

  p {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }
}

.login-form {
  .login-btn {
    width: 100%;
  }
}

.login-footer {
  text-align: center;
  margin-top: 20px;

  p {
    font-size: 13px;
    color: #909399;
    margin: 8px 0;
  }

  .tip {
    font-size: 12px;
    color: #c0c4cc;
  }
}
</style>
