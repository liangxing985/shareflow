<template>
  <div class="system-config">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统配置</span>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="支付对接配置" name="payment">
          <el-form :model="form" label-width="160px" label-position="right">
            <el-form-item label="商户ID / AppID" required>
              <el-input
                v-model="form.payment_app_id"
                placeholder="例如：peiwan_app_001"
                maxlength="64"
                show-word-limit
              />
              <div class="form-tip">调用创建订单接口时，app_id 参数必须与此一致</div>
            </el-form-item>

            <el-form-item label="API Key（通信密钥）" required>
              <el-input
                v-model="form.api_keys"
                type="textarea"
                :rows="2"
                placeholder="例如：sk_xxxxxxxxxxxxxxxx"
                show-word-limit
              />
              <div class="form-tip">
                用于MD5签名验证，多个Key用逗号分隔。
                <el-button link type="primary" @click="generateApiKey">生成随机Key</el-button>
              </div>
            </el-form-item>

            <el-form-item label="支付回调地址">
              <el-input
                v-model="form.payment_notify_url"
                placeholder="例如：https://api.peiwan.com/api/payment/notify"
                maxlength="500"
              />
              <div class="form-tip">
                管理员确认收款后，系统会自动POST通知到这个地址。必须是公网可访问的URL。
              </div>
            </el-form-item>

            <el-form-item label="回调最大重试次数">
              <el-input-number
                v-model="form.payment_notify_retry_max"
                :min="0"
                :max="10"
                :step="1"
              />
              <div class="form-tip">回调失败后的最大重试次数，默认3次</div>
            </el-form-item>

            <el-form-item label="启用签名验证">
              <el-switch v-model="form.payment_sign_enabled" />
              <div class="form-tip">生产环境必须开启，关闭后所有请求无需签名即可创建订单（不安全）</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 配置说明卡片 -->
    <el-card class="mt-4">
      <template #header>
        <span>对接说明</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="创建订单接口">
          <code>POST /api/v1/payment/create</code>
        </el-descriptions-item>
        <el-descriptions-item label="查询支付状态">
          <code>GET /api/v1/payment/status/{order_no}</code>
        </el-descriptions-item>
        <el-descriptions-item label="签名算法">
          MD5，参数按ASCII排序，空值不参与，金额保留2位小数，末尾拼接 &key=API_Key
        </el-descriptions-item>
        <el-descriptions-item label="回调触发时机">
          管理员在订单管理中点击"确认收款"后，系统自动分账并POST回调到上方配置的回调地址
        </el-descriptions-item>
        <el-descriptions-item label="回调成功标识">
          你的系统必须返回 <code>{"code": 0, "msg": "success"}</code>，否则系统会自动重试
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('payment')
const saving = ref(false)
const loading = ref(false)

const form = reactive({
  payment_app_id: '',
  api_keys: '',
  payment_notify_url: '',
  payment_notify_retry_max: 3,
  payment_sign_enabled: true
})

// 获取配置
async function loadConfig() {
  loading.value = true
  try {
    const token = localStorage.getItem('sf_token')
    const res = await fetch('/api/v1/system-config', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.success && data.data) {
      data.data.forEach((item: any) => {
        if (item.key === 'payment_app_id') form.payment_app_id = item.value
        if (item.key === 'api_keys') form.api_keys = item.value
        if (item.key === 'payment_notify_url') form.payment_notify_url = item.value
        if (item.key === 'payment_notify_retry_max') form.payment_notify_retry_max = item.value
        if (item.key === 'payment_sign_enabled') form.payment_sign_enabled = item.value
      })
    }
  } catch (e) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

// 保存配置
async function saveConfig() {
  // 校验
  if (!form.payment_app_id.trim()) {
    ElMessage.warning('商户ID不能为空')
    return
  }
  if (!form.api_keys.trim()) {
    ElMessage.warning('API Key不能为空')
    return
  }
  if (form.payment_notify_url && !form.payment_notify_url.startsWith('http')) {
    ElMessage.warning('回调地址必须以http或https开头')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确认保存配置？保存后立即生效。',
      '确认保存',
      { type: 'warning' }
    )
  } catch {
    return
  }

  saving.value = true
  try {
    const token = localStorage.getItem('sf_token')
    const res = await fetch('/api/v1/system-config', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        configs: {
          payment_app_id: form.payment_app_id.trim(),
          api_keys: form.api_keys.trim(),
          payment_notify_url: form.payment_notify_url.trim(),
          payment_notify_retry_max: form.payment_notify_retry_max,
          payment_sign_enabled: form.payment_sign_enabled
        }
      })
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('配置保存成功')
    } else {
      ElMessage.error(data.detail || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

// 生成随机API Key
function generateApiKey() {
  const chars = 'abcdef0123456789'
  let key = 'sk_'
  for (let i = 0; i < 64; i++) {
    key += chars[Math.floor(Math.random() * chars.length)]
  }
  form.api_keys = key
  ElMessage.success('已生成随机API Key，请复制保存')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.system-config {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.form-tip {
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}
.mt-4 {
  margin-top: 16px;
}
code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e6a23c;
  font-size: 13px;
}
</style>
