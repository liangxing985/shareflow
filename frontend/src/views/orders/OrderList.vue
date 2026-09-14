<template>
  <div class="page-container">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="订单号/付款人/商品" clearable style="width: 200px" />
        </el-form-item>
        <el-form-item label="业务分类">
          <el-input v-model="query.category" placeholder="分类" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="分账状态">
          <el-select v-model="query.share_status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待分账" value="pending" />
            <el-option label="已分账" value="done" />
            <el-option label="已跳过" value="skipped" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付状态">
          <el-select v-model="query.pay_status" placeholder="全部" clearable style="width: 130px">
            <el-option label="待支付" value="pending_pay" />
            <el-option label="待确认" value="pending_confirm" />
            <el-option label="已支付" value="paid" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width: 240px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 -->
    <div class="table-toolbar">
      <div>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog">新建订单</el-button>
        <el-button :icon="Download" @click="exportData">导出</el-button>
      </div>
      <div class="stats-mini">
        <el-tag>共 {{ total }} 单</el-tag>
        <el-tag type="success">总金额 ¥{{ totalAmount }}</el-tag>
      </div>
    </div>

    <!-- 表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe @row-click="showDetail" style="cursor: pointer">
        <el-table-column prop="order_no" label="订单号" width="200" show-overflow-tooltip />
        <el-table-column prop="out_order_no" label="外部订单号" width="160" show-overflow-tooltip />
        <el-table-column prop="product_name" label="商品/业务" min-width="150" show-overflow-tooltip />
        <el-table-column prop="payer_name" label="付款人" width="120" />
        <el-table-column prop="total_amount" label="金额" width="100" align="right">
          <template #default="{ row }">
            <span class="money-text">¥{{ Number(row.total_amount).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="platform_fee" label="平台抽成" width="100" align="right">
          <template #default="{ row }">
            <span class="text-warning">¥{{ Number(row.platform_fee || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="pay_status" label="支付状态" width="100">
          <template #default="{ row }">
            <el-tag :type="payStatusType(row.pay_status)" size="small">{{ payStatusText(row.pay_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="share_status" label="分账状态" width="100">
          <template #default="{ row }">
            <el-tag :type="shareStatusType(row.share_status)" size="small">{{ shareStatusText(row.share_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.source === 'api' ? 'success' : 'info'">{{ sourceText(row.source) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.pay_status === 'pending_pay' || row.pay_status === 'pending_confirm'" link type="success" size="small" @click.stop="confirmPayment(row)">确认收款</el-button>
            <el-button v-if="row.pay_status === 'pending_pay'" link type="primary" size="small" @click.stop="copyPayLink(row)">复制链接</el-button>
            <el-button link type="primary" size="small" @click.stop="showDetail(row)">详情</el-button>
            <el-button link type="warning" size="small" @click.stop="reshareOrder(row)" :disabled="row.share_status !== 'done'">重新分账</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="loadData" @current-change="loadData" style="margin-top: 16px; justify-content: flex-end" />
    </el-card>

    <!-- 新建订单弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建订单" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="订单金额" required>
          <el-input-number v-model="createForm.total_amount" :min="0.01" :precision="2" :step="10" style="width: 200px" />
          <span style="margin-left: 8px; color: #909399">元</span>
        </el-form-item>
        <el-form-item label="外部订单号">
          <el-input v-model="createForm.out_order_no" placeholder="业务系统订单号（可选）" />
        </el-form-item>
        <el-form-item label="商品/业务">
          <el-input v-model="createForm.product_name" placeholder="商品名称或业务描述" />
        </el-form-item>
        <el-form-item label="付款人">
          <el-input v-model="createForm.payer_name" placeholder="付款人姓名/昵称" />
        </el-form-item>
        <el-form-item label="业务分类">
          <el-input v-model="createForm.category" placeholder="用于匹配分账规则（可选）" />
        </el-form-item>
        <el-form-item label="分账规则">
          <el-select v-model="createForm.share_rule_id" placeholder="不选则自动匹配" clearable style="width: 100%">
            <el-option v-for="rule in ruleOptions" :key="rule.id" :label="rule.name" :value="rule.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="自动分账">
          <el-switch v-model="createForm.auto_share" />
          <span style="margin-left: 8px; color: #909399; font-size: 12px">创建后自动按规则分账</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 订单详情抽屉 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="500px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_no }}</el-descriptions-item>
          <el-descriptions-item label="外部订单号">{{ currentOrder.out_order_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="商品/业务">{{ currentOrder.product_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="付款人">{{ currentOrder.payer_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="订单金额"><span class="money-text text-primary">¥{{ Number(currentOrder.total_amount).toFixed(2) }}</span></el-descriptions-item>
          <el-descriptions-item label="平台抽成"><span class="text-warning">¥{{ Number(currentOrder.platform_fee || 0).toFixed(2) }}</span></el-descriptions-item>
          <el-descriptions-item label="可分账金额">¥{{ Number(currentOrder.shareable_amount || 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="分账状态">
            <el-tag :type="shareStatusType(currentOrder.share_status)" size="small">{{ shareStatusText(currentOrder.share_status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源">{{ sourceText(currentOrder.source) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ currentOrder.remark || '-' }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 12px">分账明细</h4>
        <el-table :data="currentOrder.share_records || []" size="small" border>
          <el-table-column prop="shareholder_name" label="分账方" />
          <el-table-column prop="level" label="层级" width="60" align="center" />
          <el-table-column prop="share_rate" label="比例" width="80" align="right">
            <template #default="{ row }">{{ (Number(row.share_rate) * 100).toFixed(1) }}%</template>
          </el-table-column>
          <el-table-column prop="share_amount" label="金额" width="100" align="right">
            <template #default="{ row }">¥{{ Number(row.share_amount).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'settled' ? 'success' : row.status === 'settling' ? 'warning' : 'info'">
                {{ row.status === 'settled' ? '已结算' : row.status === 'settling' ? '结算中' : '待结算' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download } from '@element-plus/icons-vue'
import { getOrders, createOrder, getOrder, reshareOrder as apiReshare, getOrderStats } from '@/api/orders'
import { getShareRules } from '@/api/shareRules'
import dayjs from 'dayjs'

const loading = ref(false)
const creating = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const totalAmount = ref('0.00')
const dateRange = ref<string[]>([])
const ruleOptions = ref<any[]>([])

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  category: '',
  share_status: '',
  pay_status: '',
  start_date: '',
  end_date: ''
})

const createDialogVisible = ref(false)
const detailVisible = ref(false)
const currentOrder = ref<any>(null)

const createForm = reactive({
  total_amount: 0,
  out_order_no: '',
  product_name: '',
  payer_name: '',
  category: '',
  share_rule_id: null as number | null,
  remark: '',
  auto_share: true
})

async function loadData() {
  loading.value = true
  try {
    const params = { ...query }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getOrders(params)
    tableData.value = res.items
    total.value = res.total
    const stats = await getOrderStats()
    totalAmount.value = Number(stats.total_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  const res = await getShareRules({ page_size: 100, status: 'active' })
  ruleOptions.value = res.items
}

function resetQuery() {
  query.keyword = ''
  query.category = ''
  query.share_status = ''
  query.pay_status = ''
  dateRange.value = []
  query.page = 1
  loadData()
}

function showCreateDialog() {
  Object.assign(createForm, {
    total_amount: 0, out_order_no: '', product_name: '', payer_name: '',
    category: '', share_rule_id: null, remark: '', auto_share: true
  })
  createDialogVisible.value = true
}

async function submitCreate() {
  if (!createForm.total_amount || createForm.total_amount <= 0) {
    ElMessage.warning('请输入订单金额')
    return
  }
  creating.value = true
  try {
    await createOrder(createForm)
    ElMessage.success('订单创建成功')
    createDialogVisible.value = false
    loadData()
  } finally {
    creating.value = false
  }
}

async function showDetail(row: any) {
  currentOrder.value = await getOrder(row.id)
  detailVisible.value = true
}

async function reshareOrder(row: any) {
  try {
    await ElMessageBox.confirm('确定要重新分账吗？原分账明细将被撤销并重新计算。', '确认', { type: 'warning' })
    await apiReshare(row.id)
    ElMessage.success('重新分账完成')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

function exportData() {
  ElMessage.info('导出功能开发中')
}

function shareStatusType(status: string) {
  return { done: 'success', pending: 'warning', skipped: 'info' }[status] || 'info'
}
function shareStatusText(status: string) {
  return { done: '已分账', pending: '待分账', skipped: '已跳过' }[status] || status
}
function payStatusType(status: string) {
  return { paid: 'success', pending_pay: 'warning', pending_confirm: 'warning', expired: 'info', refunded: 'danger' }[status] || 'info'
}
function payStatusText(status: string) {
  return { paid: '已支付', pending_pay: '待支付', pending_confirm: '待确认', expired: '已过期', refunded: '已退款' }[status] || status
}
function sourceText(source: string) {
  return { manual: '手动', api: 'API', import: '导入' }[source] || source
}

async function confirmPayment(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认已收到订单 ${row.order_no} 的 ¥${Number(row.total_amount).toFixed(2)} 吗？确认后将自动分账。`,
      '确认收款',
      { type: 'warning', confirmButtonText: '确认收款', cancelButtonText: '取消' }
    )
    const res: any = await fetch(`/api/v1/orders/${row.id}/confirm-payment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('sf_token')}`
      },
      body: JSON.stringify({ auto_share: true })
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('确认收款成功，已自动分账')
      loadData()
    } else {
      ElMessage.error(data.detail || '操作失败')
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

function copyPayLink(row: any) {
  const payUrl = `${window.location.origin}/pay/${row.order_no}`
  navigator.clipboard.writeText(payUrl).then(() => {
    ElMessage.success('支付链接已复制')
  }).catch(() => {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = payUrl
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('支付链接已复制')
  })
}
function formatDate(date: string) {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
}

onMounted(() => {
  loadData()
  loadRules()
})
</script>

<style scoped lang="scss">
.search-card {
  margin-bottom: 16px;
  :deep(.el-card__body) { padding: 16px; }
}
.table-toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  .stats-mini { display: flex; gap: 8px; }
}
.order-detail {
  :deep(.el-descriptions__label) { width: 100px; }
}
</style>
