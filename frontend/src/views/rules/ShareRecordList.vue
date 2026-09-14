<template>
  <div class="page-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="订单号/分账方" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="待结算" value="pending" />
            <el-option label="结算中" value="settling" />
            <el-option label="已结算" value="settled" />
          </el-select>
        </el-form-item>
        <el-form-item label="层级">
          <el-select v-model="query.level" placeholder="全部" clearable style="width: 100px">
            <el-option label="一级" :value="1" />
            <el-option label="二级" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">总分账金额</div><div class="value money-text">¥{{ stats.total_amount || 0 }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">待结算金额</div><div class="value money-text text-warning">¥{{ stats.pending_amount || 0 }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">已结算金额</div><div class="value money-text text-success">¥{{ stats.settled_amount || 0 }}</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-mini"><div class="label">分账笔数</div><div class="value">{{ stats.total_records || 0 }}</div></div></el-card></el-col>
    </el-row>

    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="order_no" label="订单号" width="200" show-overflow-tooltip />
        <el-table-column prop="shareholder_name" label="分账方" width="140" />
        <el-table-column prop="level" label="层级" width="70" align="center">
          <template #default="{ row }"><el-tag size="small" :type="row.level > 1 ? 'warning' : ''">L{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="order_amount" label="订单金额" width="100" align="right">
          <template #default="{ row }">¥{{ Number(row.order_amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="platform_fee" label="平台抽成" width="100" align="right">
          <template #default="{ row }"><span class="text-warning">¥{{ Number(row.platform_fee || 0).toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="share_rate" label="比例" width="80" align="right">
          <template #default="{ row }">{{ row.share_rate ? (Number(row.share_rate) * 100).toFixed(1) + '%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="share_amount" label="应分金额" width="100" align="right">
          <template #default="{ row }"><span class="money-text">¥{{ Number(row.share_amount).toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="actual_amount" label="实际金额" width="100" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-warning': row.is_adjusted }">¥{{ Number(row.actual_amount || row.share_amount).toFixed(2) }}</span>
            <el-tag v-if="row.is_adjusted" size="small" type="warning" style="margin-left: 4px">调</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'settled' ? 'success' : row.status === 'settling' ? 'warning' : 'info'">
              {{ row.status === 'settled' ? '已结算' : row.status === 'settling' ? '结算中' : '待结算' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at ? row.created_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" size="small" @click="adjustRecord(row)" :disabled="row.status !== 'pending'">调整</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total" layout="total, prev, pager, next" @current-change="loadData" style="margin-top: 16px; justify-content: flex-end" />
    </el-card>

    <!-- 调整弹窗 -->
    <el-dialog v-model="adjustVisible" title="调整分账金额" width="450px">
      <el-form label-width="100px">
        <el-form-item label="分账方">{{ currentRecord?.shareholder_name }}</el-form-item>
        <el-form-item label="原金额">¥{{ Number(currentRecord?.share_amount || 0).toFixed(2) }}</el-form-item>
        <el-form-item label="调整后金额" required>
          <el-input-number v-model="adjustAmount" :min="0" :precision="2" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="调整原因" required>
          <el-input v-model="adjustReason" type="textarea" :rows="2" placeholder="请说明调整原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAdjust">确认调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getShareRecords, adjustRecord as apiAdjustRecord, getShareRecordsStats } from '@/api/shareRecords'

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const stats = ref<any>({})
const adjustVisible = ref(false)
const currentRecord = ref<any>(null)
const adjustAmount = ref(0)
const adjustReason = ref('')

const query = reactive({ page: 1, page_size: 20, keyword: '', status: '', level: null as number | null })

async function loadData() {
  loading.value = true
  try {
    const res = await getShareRecords(query)
    tableData.value = res.items
    total.value = res.total
    const s = await getShareRecordsStats()
    stats.value = {
      total_amount: Number(s.total_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      pending_amount: Number(s.pending_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      settled_amount: Number(s.settled_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      total_records: s.total_records
    }
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''; query.status = ''; query.level = null; query.page = 1; loadData()
}

function adjustRecord(row: any) {
  currentRecord.value = row
  adjustAmount.value = Number(row.actual_amount || row.share_amount)
  adjustReason.value = ''
  adjustVisible.value = true
}

async function submitAdjust() {
  if (!adjustReason.value) { ElMessage.warning('请输入调整原因'); return }
  await apiAdjustRecord(currentRecord.value.id, adjustAmount.value, adjustReason.value)
  ElMessage.success('调整成功')
  adjustVisible.value = false
  loadData()
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.search-card { margin-bottom: 16px; :deep(.el-card__body) { padding: 16px; } }
.stat-mini { text-align: center; .label { font-size: 13px; color: #909399; margin-bottom: 8px; } .value { font-size: 22px; font-weight: 600; color: #303133; } }
</style>
