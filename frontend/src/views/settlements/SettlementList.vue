<template>
  <div class="page-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="结算单号/分账方" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待转账" value="pending" />
            <el-option label="已转账待确认" value="transferred" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="结算方式">
          <el-select v-model="query.payment_method" placeholder="全部" clearable style="width: 100px">
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="银行卡" value="bank" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">待转账</div><div class="value money-text text-warning">{{ stats.pending_count || 0 }} 笔 / ¥{{ stats.pending_amount || '0.00' }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">已确认结算</div><div class="value money-text text-success">{{ stats.confirmed_count || 0 }} 笔 / ¥{{ stats.confirmed_amount || '0.00' }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">结算总金额</div><div class="value money-text">¥{{ stats.total_amount || '0.00' }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">结算笔数</div><div class="value">{{ stats.total_settlements || 0 }}</div></div></el-card></el-col>
    </el-row>

    <div class="table-toolbar">
      <div>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog">创建结算单</el-button>
        <el-button type="success" :icon="Grid" @click="batchCreate">批量生成转账清单</el-button>
        <el-button type="warning" :icon="Download" @click="handleExport">导出现金转账清单</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe @row-click="showDetail">
        <el-table-column prop="settlement_no" label="结算单号" width="200" show-overflow-tooltip />
        <el-table-column prop="shareholder_name" label="分账方" width="120" />
        <el-table-column prop="total_records" label="笔数" width="70" align="center" />
        <el-table-column prop="total_amount" label="结算金额" width="120" align="right">
          <template #default="{ row }"><span class="money-text">¥{{ Number(row.total_amount).toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="actual_amount" label="实际转账" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.actual_amount" class="text-success">¥{{ Number(row.actual_amount).toFixed(2) }}</span>
            <span v-else class="text-info">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="方式" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.payment_method === 'wechat' ? 'success' : row.payment_method === 'alipay' ? 'primary' : 'info'">
              {{ { wechat: '微信', alipay: '支付宝', bank: '银行卡' }[row.payment_method as 'wechat' | 'alipay' | 'bank'] || row.payment_method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at ? row.created_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="showDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'pending'" link type="success" size="small" @click.stop="showTransferDialog(row)">登记转账</el-button>
            <el-button v-if="row.status === 'transferred'" link type="warning" size="small" @click.stop="confirmSettlement(row)">确认结算</el-button>
            <el-button v-if="row.status === 'pending' || row.status === 'transferred'" link type="danger" size="small" @click.stop="cancelSettlement(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total" layout="total, prev, pager, next" @current-change="loadData" style="margin-top: 16px; justify-content: flex-end" />
    </el-card>

    <!-- 创建结算单弹窗 -->
    <el-dialog v-model="createDialogVisible" title="创建结算单" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="分账方" required>
          <el-select v-model="createForm.shareholder_id" placeholder="选择分账方" filterable style="width: 100%">
            <el-option v-for="sh in shareholderOptions" :key="sh.id" :label="`${sh.name} (待结算: ¥${Number(sh.current_balance || 0).toFixed(2)})`" :value="sh.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="结算方式">
          <el-radio-group v-model="createForm.payment_method">
            <el-radio value="wechat">微信</el-radio>
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="bank">银行卡</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert title="将结算该分账方所有待结算的分账明细，生成转账清单后请手动转账并登记。" type="info" :closable="false" />
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建结算单</el-button>
      </template>
    </el-dialog>

    <!-- 登记转账弹窗 -->
    <el-dialog v-model="transferDialogVisible" title="登记已转账" width="500px">
      <el-form :model="transferForm" label-width="100px">
        <el-form-item label="结算单号">{{ currentSettlement?.settlement_no }}</el-form-item>
        <el-form-item label="分账方">{{ currentSettlement?.shareholder_name }}</el-form-item>
        <el-form-item label="应转金额"><span class="money-text text-primary">¥{{ Number(currentSettlement?.total_amount || 0).toFixed(2) }}</span></el-form-item>
        <el-form-item label="实际转账金额">
          <el-input-number v-model="transferForm.actual_amount" :min="0" :precision="2" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="交易号">
          <el-input v-model="transferForm.transaction_no" placeholder="微信/支付宝交易号（可选）" />
        </el-form-item>
        <el-form-item label="手续费">
          <el-input-number v-model="transferForm.fee_amount" :min="0" :precision="2" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="transferForm.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="转账凭证">
          <ImageUpload v-model="transferForm.transfer_voucher_url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transferDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="transferring" @click="submitTransfer">确认已转账</el-button>
      </template>
    </el-dialog>

    <!-- 结算详情抽屉 -->
    <el-drawer v-model="detailVisible" title="结算单详情" size="550px">
      <div v-if="currentSettlement" class="settlement-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="结算单号">{{ currentSettlement.settlement_no }}</el-descriptions-item>
          <el-descriptions-item label="分账方">{{ currentSettlement.shareholder_name }}</el-descriptions-item>
          <el-descriptions-item label="分账笔数">{{ currentSettlement.total_records }}</el-descriptions-item>
          <el-descriptions-item label="结算金额"><span class="money-text text-primary">¥{{ Number(currentSettlement.total_amount).toFixed(2) }}</span></el-descriptions-item>
          <el-descriptions-item label="实际转账">{{ currentSettlement.actual_amount ? '¥' + Number(currentSettlement.actual_amount).toFixed(2) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="结算方式">{{ paymentMethodText(currentSettlement.payment_method) }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="statusType(currentSettlement.status)" size="small">{{ statusText(currentSettlement.status) }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="交易号">{{ currentSettlement.transaction_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentSettlement.created_at ? currentSettlement.created_at.substring(0, 19).replace('T', ' ') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="转账时间">{{ currentSettlement.transferred_at ? currentSettlement.transferred_at.substring(0, 19).replace('T', ' ') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ currentSettlement.confirmed_at ? currentSettlement.confirmed_at.substring(0, 19).replace('T', ' ') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ currentSettlement.remark || '-' }}</el-descriptions-item>
          <el-descriptions-item label="转账凭证" v-if="currentSettlement.transfer_voucher_url">
            <el-image :src="currentSettlement.transfer_voucher_url" :preview-src-list="[currentSettlement.transfer_voucher_url]" fit="contain" style="width: 150px; height: 150px; border: 1px solid #eee; border-radius: 4px;" />
          </el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 12px">分账明细（{{ currentSettlement.share_records?.length || 0 }}笔）</h4>
        <el-table :data="currentSettlement.share_records || []" size="small" border>
          <el-table-column prop="order_no" label="订单号" show-overflow-tooltip />
          <el-table-column prop="share_amount" label="金额" width="100" align="right">
            <template #default="{ row }">¥{{ Number(row.share_amount).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="level" label="层级" width="60" align="center" />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Grid, Download } from '@element-plus/icons-vue'
import { getSettlements, createSettlement, batchCreateSettlements, markTransferred, confirmSettlement as apiConfirm, cancelSettlement as apiCancel, exportTransferList as apiExport, getSettlementStats } from '@/api/settlements'
import { getShareholdersWithBalance } from '@/api/shareholders'
import ImageUpload from '@/components/ImageUpload.vue'

const loading = ref(false)
const creating = ref(false)
const transferring = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const stats = ref<any>({})
const shareholderOptions = ref<any[]>([])

const query = reactive({ page: 1, page_size: 20, keyword: '', status: '', payment_method: '' })

const createDialogVisible = ref(false)
const transferDialogVisible = ref(false)
const detailVisible = ref(false)
const currentSettlement = ref<any>(null)

const createForm = reactive({ shareholder_id: null as number | null, payment_method: 'wechat', remark: '' })
const transferForm = reactive({ actual_amount: 0, transaction_no: '', fee_amount: 0, remark: '', transfer_voucher_url: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await getSettlements(query)
    tableData.value = res.items
    total.value = res.total
    const s = await getSettlementStats()
    stats.value = {
      pending_count: s.pending_count,
      pending_amount: Number(s.pending_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      confirmed_count: s.confirmed_count,
      confirmed_amount: Number(s.confirmed_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      total_amount: Number(s.total_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      total_settlements: s.total_settlements
    }
  } finally {
    loading.value = false
  }
}

async function loadShareholders() {
  const res = await getShareholdersWithBalance({ page_size: 100 })
  shareholderOptions.value = res.items.filter((s: any) => Number(s.current_balance || 0) > 0)
}

function resetQuery() {
  query.keyword = ''; query.status = ''; query.payment_method = ''; query.page = 1; loadData()
}

function showCreateDialog() {
  createForm.shareholder_id = null
  createForm.payment_method = 'wechat'
  createForm.remark = ''
  loadShareholders()
  createDialogVisible.value = true
}

async function submitCreate() {
  if (!createForm.shareholder_id) { ElMessage.warning('请选择分账方'); return }
  creating.value = true
  try {
    await createSettlement(createForm)
    ElMessage.success('结算单创建成功，请手动转账后登记')
    createDialogVisible.value = false
    loadData()
  } finally {
    creating.value = false
  }
}

async function batchCreate() {
  try {
    await ElMessageBox.confirm('将为所有有待结算余额的分账方批量生成结算单（转账清单），确定继续吗？', '批量生成', { type: 'info' })
    const res = await batchCreateSettlements({ payment_method: 'wechat' })
    ElMessage.success(`已生成 ${res.created_count} 个结算单`)
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

function showTransferDialog(row: any) {
  currentSettlement.value = row
  transferForm.actual_amount = Number(row.total_amount)
  transferForm.transaction_no = ''
  transferForm.fee_amount = 0
  transferForm.remark = ''
  transferForm.transfer_voucher_url = ''
  transferDialogVisible.value = true
}

async function submitTransfer() {
  transferring.value = true
  try {
    await markTransferred(currentSettlement.value.id, transferForm)
    ElMessage.success('转账登记成功，待确认结算')
    transferDialogVisible.value = false
    loadData()
  } finally {
    transferring.value = false
  }
}

async function confirmSettlement(row: any) {
  try {
    await ElMessageBox.confirm(`确认结算单"${row.settlement_no}"已完成？确认后分账明细将标记为已结算。`, '确认结算', { type: 'warning' })
    await apiConfirm(row.id)
    ElMessage.success('结算已确认')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function cancelSettlement(row: any) {
  try {
    await ElMessageBox.confirm(`确定取消结算单"${row.settlement_no}"吗？分账明细将回退到待结算状态。`, '取消结算', { type: 'warning' })
    await apiCancel(row.id)
    ElMessage.success('已取消')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function showDetail(row: any) {
  // 从列表中找详情，API没有单独的详情端点
  currentSettlement.value = row
  detailVisible.value = true
}

async function handleExport() {
  try {
    const blob = await apiExport('pending')
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `转账清单_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

function paymentMethodText(method: string) {
  return { wechat: '微信', alipay: '支付宝', bank: '银行卡' }[method as 'wechat'|'alipay'|'bank'] || method
}

function statusType(status: string) {
  return { pending: 'warning', transferred: 'primary', confirmed: 'success', cancelled: 'info' }[status] || 'info'
}
function statusText(status: string) {
  return { pending: '待转账', transferred: '已转账待确认', confirmed: '已确认', cancelled: '已取消' }[status] || status
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.search-card { margin-bottom: 16px; :deep(.el-card__body) { padding: 16px; } }
.table-toolbar { margin-bottom: 16px; }
.stat-mini { text-align: center; .label { font-size: 13px; color: #909399; margin-bottom: 8px; } .value { font-size: 18px; font-weight: 600; color: #303133; } }
</style>
