<template>
  <div class="page-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="姓名/联系方式" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.shareholder_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="合伙人" value="partner" />
            <el-option label="供应商" value="supplier" />
            <el-option label="推广员" value="promoter" />
            <el-option label="员工" value="employee" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="table-toolbar">
      <el-button type="primary" :icon="Plus" @click="showDialog()">新建分账方</el-button>
      <div class="stats-mini">
        <el-tag>共 {{ total }} 人</el-tag>
        <el-tag type="warning">待结算 ¥{{ totalPending }}</el-tag>
      </div>
    </div>

    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="name" label="姓名/名称" width="140" />
        <el-table-column prop="shareholder_type" label="类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ typeText(row.shareholder_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="contact" label="联系方式" width="130" />
        <el-table-column label="收款信息" min-width="200">
          <template #default="{ row }">
            <div v-if="row.preferred_payment === 'wechat'" class="pay-info">
              <el-icon color="#07c160"><ChatDotRound /></el-icon>
              <span>{{ row.wechat_account || '-' }} ({{ row.wechat_real_name || '-' }})</span>
            </div>
            <div v-else-if="row.preferred_payment === 'alipay'" class="pay-info">
              <el-icon color="#1677ff"><Wallet /></el-icon>
              <span>{{ row.alipay_account || '-' }} ({{ row.alipay_real_name || '-' }})</span>
            </div>
            <div v-else class="pay-info">
              <el-icon><CreditCard /></el-icon>
              <span>{{ row.bank_name }} {{ row.bank_card_no }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="default_rate" label="默认比例" width="90" align="right">
          <template #default="{ row }">{{ row.default_rate ? (Number(row.default_rate) * 100).toFixed(1) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="current_balance" label="待结算余额" width="120" align="right">
          <template #default="{ row }"><span class="money-text text-warning">¥{{ Number(row.current_balance || 0).toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="total_receivable" label="累计应收" width="120" align="right">
          <template #default="{ row }">¥{{ Number(row.total_receivable || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_blacklisted ? 'danger' : row.status === 'active' ? 'success' : 'info'">
              {{ row.is_blacklisted ? '黑名单' : row.status === 'active' ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="toggleBlacklist(row)">{{ row.is_blacklisted ? '移出黑名单' : '加入黑名单' }}</el-button>
            <el-button link type="info" size="small" @click="viewRecords(row)">分账记录</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total" layout="total, prev, pager, next, jumper" @current-change="loadData" style="margin-top: 16px; justify-content: flex-end" />
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑分账方' : '新建分账方'" width="650px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="姓名/名称" required>
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型">
              <el-select v-model="form.shareholder_type" style="width: 100%">
                <el-option label="合伙人" value="partner" />
                <el-option label="供应商" value="supplier" />
                <el-option label="推广员" value="promoter" />
                <el-option label="员工" value="employee" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系方式">
              <el-input v-model="form.contact" placeholder="手机/微信" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="首选结算方式">
          <el-radio-group v-model="form.preferred_payment">
            <el-radio value="wechat">微信</el-radio>
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="bank">银行卡</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="16" v-if="form.preferred_payment === 'wechat'">
          <el-col :span="12">
            <el-form-item label="微信账号">
              <el-input v-model="form.wechat_account" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="微信实名">
              <el-input v-model="form.wechat_real_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" v-if="form.preferred_payment === 'alipay'">
          <el-col :span="12">
            <el-form-item label="支付宝账号">
              <el-input v-model="form.alipay_account" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="支付宝实名">
              <el-input v-model="form.alipay_real_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" v-if="form.preferred_payment === 'bank'">
          <el-col :span="8">
            <el-form-item label="开户银行">
              <el-input v-model="form.bank_name" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="银行卡号">
              <el-input v-model="form.bank_card_no" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="开户名">
              <el-input v-model="form.bank_account_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="默认分账比例">
              <el-input-number v-model="form.default_rate" :min="0" :max="1" :step="0.05" :precision="4" style="width: 100%" />
              <span style="font-size: 12px; color: #909399">0-1之间，如0.6表示60%</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="正常" value="active" />
                <el-option label="停用" value="inactive" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分账记录抽屉 -->
    <el-drawer v-model="recordsVisible" title="分账记录" size="600px">
      <el-table :data="recordList" v-loading="recordsLoading" size="small">
        <el-table-column prop="order_no" label="订单号" width="180" show-overflow-tooltip />
        <el-table-column prop="share_amount" label="金额" width="100" align="right">
          <template #default="{ row }">¥{{ Number(row.share_amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="level" label="层级" width="60" align="center" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'settled' ? 'success' : row.status === 'settling' ? 'warning' : 'info'">
              {{ row.status === 'settled' ? '已结算' : row.status === 'settling' ? '结算中' : '待结算' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ row.created_at ? row.created_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, ChatDotRound, Wallet, CreditCard } from '@element-plus/icons-vue'
import { getShareholdersWithBalance, createShareholder, updateShareholder, toggleBlacklist as apiToggleBlacklist, getShareholderRecords } from '@/api/shareholders'

const loading = ref(false)
const saving = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const totalPending = ref('0.00')
const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const recordsVisible = ref(false)
const recordsLoading = ref(false)
const recordList = ref<any[]>([])

const query = reactive({ page: 1, page_size: 20, keyword: '', shareholder_type: '' })

const form = reactive({
  name: '', contact: '', email: '', shareholder_type: 'partner',
  wechat_account: '', wechat_real_name: '', alipay_account: '', alipay_real_name: '',
  bank_name: '', bank_card_no: '', bank_account_name: '', preferred_payment: 'wechat',
  default_rate: null as number | null, status: 'active', remark: ''
})

async function loadData() {
  loading.value = true
  try {
    const res = await getShareholdersWithBalance(query)
    tableData.value = res.items
    total.value = res.total
    totalPending.value = res.items.reduce((sum, item) => sum + Number(item.current_balance || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.shareholder_type = ''
  query.page = 1
  loadData()
}

function showDialog(row?: any) {
  if (row) {
    editId.value = row.id
    Object.assign(form, {
      name: row.name, contact: row.contact, email: row.email, shareholder_type: row.shareholder_type,
      wechat_account: row.wechat_account, wechat_real_name: row.wechat_real_name,
      alipay_account: row.alipay_account, alipay_real_name: row.alipay_real_name,
      bank_name: row.bank_name, bank_card_no: row.bank_card_no, bank_account_name: row.bank_account_name,
      preferred_payment: row.preferred_payment, default_rate: row.default_rate, status: row.status, remark: row.remark
    })
  } else {
    editId.value = null
    Object.assign(form, {
      name: '', contact: '', email: '', shareholder_type: 'partner',
      wechat_account: '', wechat_real_name: '', alipay_account: '', alipay_real_name: '',
      bank_name: '', bank_card_no: '', bank_account_name: '', preferred_payment: 'wechat',
      default_rate: null, status: 'active', remark: ''
    })
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.name) { ElMessage.warning('请输入姓名'); return }
  saving.value = true
  try {
    if (editId.value) {
      await updateShareholder(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createShareholder(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function toggleBlacklist(row: any) {
  await apiToggleBlacklist(row.id)
  ElMessage.success(row.is_blacklisted ? '已移出黑名单' : '已加入黑名单')
  loadData()
}

async function viewRecords(row: any) {
  recordsVisible.value = true
  recordsLoading.value = true
  try {
    const res = await getShareholderRecords(row.id, { page_size: 50 })
    recordList.value = res.items
  } finally {
    recordsLoading.value = false
  }
}

function typeText(type: string) {
  return { partner: '合伙人', supplier: '供应商', promoter: '推广员', employee: '员工', other: '其他' }[type] || type
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.search-card { margin-bottom: 16px; :deep(.el-card__body) { padding: 16px; } }
.table-toolbar { margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; .stats-mini { display: flex; gap: 8px; } }
.pay-info { display: flex; align-items: center; gap: 6px; font-size: 13px; }
</style>
