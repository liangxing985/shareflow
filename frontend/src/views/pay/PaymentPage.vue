<template>
  <div class="payment-page">
    <div class="payment-container">
      <!-- 顶部标题 -->
      <div class="payment-header">
        <h1>订单支付</h1>
        <p class="order-no">订单号：{{ orderInfo.order_no }}</p>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-box">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p>加载中...</p>
      </div>

      <!-- 待支付状态 -->
      <div v-else-if="orderInfo.pay_status === 'pending_pay'" class="payment-content">
        <!-- 金额 -->
        <div class="amount-box">
          <span class="amount-label">应付金额</span>
          <span class="amount-value">¥{{ Number(orderInfo.total_amount).toFixed(2) }}</span>
        </div>

        <!-- 商品信息 -->
        <div v-if="orderInfo.product_name" class="product-info">
          <el-icon><Goods /></el-icon>
          <span>{{ orderInfo.product_name }}</span>
        </div>

        <!-- 倒计时 -->
        <div class="countdown-box" v-if="remainingSeconds > 0">
          <el-icon><Timer /></el-icon>
          <span>支付剩余时间：<b class="countdown-text">{{ formattedTime }}</b></span>
        </div>
        <div v-else class="countdown-box expired">
          <el-icon><Warning /></el-icon>
          <span>支付链接已过期</span>
        </div>

        <!-- 收款码区域 -->
        <div class="qrcode-section">
          <div class="qrcode-tabs">
            <button
              v-for="acc in paymentAccounts"
              :key="acc.id"
              class="tab-btn"
              :class="{ active: currentPlatform === acc.platform }"
              @click="currentPlatform = acc.platform"
            >
              <el-icon><component :is="acc.platform === 'wechat' ? 'ChatDotSquare' : 'Money'" /></el-icon>
              {{ acc.platform === 'wechat' ? '微信支付' : '支付宝' }}
            </button>
          </div>

          <div class="qrcode-box">
            <div v-if="currentAccount && currentAccount.qr_code_url" class="qrcode-img">
              <img :src="currentAccount.qr_code_url" alt="收款码" />
            </div>
            <div v-else class="qrcode-placeholder">
              <el-icon :size="48"><Picture /></el-icon>
              <p>收款码未配置</p>
            </div>
            <p class="qrcode-tip">
              请使用{{ currentPlatform === 'wechat' ? '微信' : '支付宝' }}扫码支付
            </p>
          </div>
        </div>

        <!-- 我已支付按钮 -->
        <el-button
          type="success"
          size="large"
          class="pay-btn"
          :loading="confirming"
          :disabled="remainingSeconds <= 0"
          @click="handleConfirmPay"
        >
          <el-icon><Check /></el-icon>
          我已支付
        </el-button>

        <p class="tip-text">支付完成后请点击上方按钮，商家确认后订单生效</p>
      </div>

      <!-- 待确认状态 -->
      <div v-else-if="orderInfo.pay_status === 'pending_confirm'" class="status-content">
        <div class="status-icon warning">
          <el-icon :size="64"><Clock /></el-icon>
        </div>
        <h2>等待商家确认收款</h2>
        <p>您已确认支付，商家正在核实到账情况</p>
        <p class="order-amount">订单金额：<b>¥{{ Number(orderInfo.total_amount).toFixed(2) }}</b></p>
        <el-button type="primary" @click="loadOrderInfo">刷新状态</el-button>
      </div>

      <!-- 已支付状态 -->
      <div v-else-if="orderInfo.pay_status === 'paid'" class="status-content">
        <div class="status-icon success">
          <el-icon :size="64"><CircleCheck /></el-icon>
        </div>
        <h2>支付成功</h2>
        <p>订单已支付完成，感谢您的购买</p>
        <p class="order-amount">支付金额：<b>¥{{ Number(orderInfo.total_amount).toFixed(2) }}</b></p>
        <p class="pay-time">支付时间：{{ orderInfo.paid_at ? formatTime(orderInfo.paid_at) : '-' }}</p>
      </div>

      <!-- 已过期状态 -->
      <div v-else-if="orderInfo.pay_status === 'expired'" class="status-content">
        <div class="status-icon error">
          <el-icon :size="64"><CircleClose /></el-icon>
        </div>
        <h2>订单已过期</h2>
        <p>支付链接已超过有效期，请重新下单</p>
        <p class="order-amount">订单金额：<b>¥{{ Number(orderInfo.total_amount).toFixed(2) }}</b></p>
      </div>

      <!-- 底部 -->
      <div class="payment-footer">
        <p>支付遇到问题？请联系客服</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Loading, Timer, Warning, Goods, Picture, Check,
  Clock, CircleCheck, CircleClose, ChatDotSquare, Money
} from '@element-plus/icons-vue'
import request from '@/utils/request'

const route = useRoute()

const loading = ref(true)
const confirming = ref(false)
const orderInfo = ref<any>({})
const paymentAccounts = ref<any[]>([])
const currentPlatform = ref('wechat')
const remainingSeconds = ref(0)
let timer: any = null

const currentAccount = computed(() => {
  return paymentAccounts.value.find(a => a.platform === currentPlatform.value)
})

const formattedTime = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60)
  const s = remainingSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

async function loadOrderInfo() {
  loading.value = true
  try {
    const orderNo = route.params.orderNo
    const res: any = await request.get(`/orders/pay/${orderNo}`)
    orderInfo.value = res
    paymentAccounts.value = res.payment_accounts || []

    // 默认选中微信，如果没有微信则选第一个
    if (paymentAccounts.value.length > 0) {
      const wechat = paymentAccounts.value.find((a: any) => a.platform === 'wechat')
      currentPlatform.value = wechat ? 'wechat' : paymentAccounts.value[0].platform
    }

    // 计算倒计时
    if (res.pay_expire_at) {
      const expireTime = new Date(res.pay_expire_at).getTime()
      const now = Date.now()
      remainingSeconds.value = Math.max(0, Math.floor((expireTime - now) / 1000))
      startCountdown()
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载订单失败')
  } finally {
    loading.value = false
  }
}

function startCountdown() {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value--
    } else {
      clearInterval(timer)
      // 过期后刷新状态
      if (orderInfo.value.pay_status === 'pending_pay') {
        loadOrderInfo()
      }
    }
  }, 1000)
}

async function handleConfirmPay() {
  if (remainingSeconds.value <= 0) {
    ElMessage.warning('支付链接已过期')
    return
  }
  confirming.value = true
  try {
    const orderNo = route.params.orderNo
    await request.post(`/orders/pay/${orderNo}/confirm`)
    ElMessage.success('已确认支付，等待商家确认收款')
    await loadOrderInfo()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    confirming.value = false
  }
}

function formatTime(timeStr: string) {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  loadOrderInfo()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped lang="scss">
.payment-page {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.payment-container {
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.payment-header {
  text-align: center;
  padding: 30px 20px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;

  h1 {
    margin: 0 0 8px;
    font-size: 24px;
  }

  .order-no {
    margin: 0;
    font-size: 13px;
    opacity: 0.9;
  }
}

.loading-box {
  text-align: center;
  padding: 60px 20px;
  color: #909399;

  p {
    margin-top: 16px;
  }
}

.payment-content {
  padding: 24px;
}

.amount-box {
  text-align: center;
  margin-bottom: 16px;

  .amount-label {
    display: block;
    font-size: 14px;
    color: #909399;
    margin-bottom: 8px;
  }

  .amount-value {
    font-size: 42px;
    font-weight: bold;
    color: #f56c6c;
  }
}

.product-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  margin-bottom: 16px;
}

.countdown-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  background: #f0f9eb;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #67c23a;

  &.expired {
    background: #fef0f0;
    color: #f56c6c;
  }

  .countdown-text {
    color: #f56c6c;
    font-size: 18px;
  }
}

.qrcode-section {
  margin-bottom: 24px;
}

.qrcode-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;

  .tab-btn {
    flex: 1;
    padding: 12px;
    border: none;
    background: #fff;
    cursor: pointer;
    font-size: 14px;
    color: #606266;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: all 0.3s;

    &.active {
      background: #409eff;
      color: #fff;
    }

    &:first-child {
      border-right: 1px solid #dcdfe6;
    }
  }
}

.qrcode-box {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 12px;

  .qrcode-img {
    width: 220px;
    height: 220px;
    margin: 0 auto 12px;
    background: #fff;
    border-radius: 8px;
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
  }

  .qrcode-placeholder {
    width: 220px;
    height: 220px;
    margin: 0 auto 12px;
    background: #fff;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #c0c4cc;

    p {
      margin-top: 12px;
      font-size: 14px;
    }
  }

  .qrcode-tip {
    margin: 0;
    font-size: 14px;
    color: #606266;
  }
}

.pay-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-bottom: 12px;
}

.tip-text {
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.status-content {
  text-align: center;
  padding: 40px 24px;

  .status-icon {
    margin-bottom: 20px;

    &.success {
      color: #67c23a;
    }

    &.warning {
      color: #e6a23c;
    }

    &.error {
      color: #f56c6c;
    }
  }

  h2 {
    margin: 0 0 12px;
    font-size: 22px;
    color: #303133;
  }

  p {
    margin: 8px 0;
    color: #606266;
    font-size: 14px;
  }

  .order-amount {
    font-size: 16px;
    margin: 16px 0;

    b {
      color: #f56c6c;
      font-size: 20px;
    }
  }

  .pay-time {
    font-size: 13px;
    color: #909399;
  }
}

.payment-footer {
  text-align: center;
  padding: 16px;
  background: #f5f7fa;
  border-top: 1px solid #ebeef5;

  p {
    margin: 0;
    font-size: 12px;
    color: #909399;
  }
}
</style>
