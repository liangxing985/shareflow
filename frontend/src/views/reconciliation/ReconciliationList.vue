<template>
  <div class="page-container">
    <div class="table-toolbar">
      <el-button type="primary" :icon="Upload" @click="showUploadDialog">上传对账单</el-button>
      <el-alert title="上传微信/支付宝对账单后，系统将统计系统订单并标记差异。微信/支付宝对账单格式需根据实际导出格式定制解析。" type="info" :closable="false" show-icon style="flex: 1; margin-left: 16px" />
    </div>

    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="recon_no" label="对账批次号" width="200" />
        <el-table-column prop="platform" label="平台" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.platform === 'wechat' ? 'success' : 'primary'">
              {{ row.platform === 'wechat' ? '微信' : '支付宝' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recon_date" label="对账日期" width="120" />
        <el-table-column prop="system_orders" label="系统订单" width="100" align="right" />
        <el-table-column prop="system_amount" label="系统金额" width="120" align="right">
          <template #default="{ row }">¥{{ Number(row.system_amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="channel_orders" label="渠道订单" width="100" align="right" />
        <el-table-column prop="channel_amount" label="渠道金额" width="120" align="right">
          <template #default="{ row }">¥{{ Number(row.channel_amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="diff_orders" label="差异笔数" width="90" align="right">
          <template #default="{ row }"><span :class="{ 'text-danger': row.diff_orders > 0 }">{{ row.diff_orders }}</span></template>
        </el-table-column>
        <el-table-column prop="diff_amount" label="差异金额" width="110" align="right">
          <template #default="{ row }"><span :class="{ 'text-danger': row.diff_amount > 0 }">¥{{ Number(row.diff_amount).toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'has_diff' ? 'warning' : 'info'">
              {{ { completed: '已完成', has_diff: '有差异', processing: '处理中', failed: '失败' }[row.status as 'completed' | 'has_diff' | 'processing' | 'failed'] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="对账单文件" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at ? row.created_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="uploadDialogVisible" title="上传对账单" width="450px">
      <el-form label-width="100px">
        <el-form-item label="平台" required>
          <el-radio-group v-model="uploadForm.platform">
            <el-radio value="wechat">微信</el-radio>
            <el-radio value="alipay">支付宝</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="对账日期" required>
          <el-date-picker v-model="uploadForm.recon_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="对账单文件" required>
          <el-upload :auto-upload="false" :limit="1" :on-change="handleFileChange" accept=".csv,.xlsx,.xls">
            <el-button :icon="Upload">选择文件</el-button>
            <template #tip><div class="el-upload__tip">支持 CSV/Excel 格式</div></template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">上传并对账</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { getReconciliations, uploadStatement } from '@/api/reconciliations'

const loading = ref(false)
const uploading = ref(false)
const tableData = ref<any[]>([])
const uploadDialogVisible = ref(false)
const uploadFile = ref<File | null>(null)

const uploadForm = reactive({ platform: 'wechat', recon_date: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await getReconciliations({ page_size: 50 })
    tableData.value = res.items
  } finally {
    loading.value = false
  }
}

function showUploadDialog() {
  uploadForm.platform = 'wechat'
  uploadForm.recon_date = new Date().toISOString().slice(0, 10)
  uploadFile.value = null
  uploadDialogVisible.value = true
}

function handleFileChange(file: any) {
  uploadFile.value = file.raw
}

async function submitUpload() {
  if (!uploadForm.recon_date) { ElMessage.warning('请选择对账日期'); return }
  if (!uploadFile.value) { ElMessage.warning('请选择对账单文件'); return }
  uploading.value = true
  try {
    const res = await uploadStatement(uploadForm.platform, uploadForm.recon_date, uploadFile.value)
    ElMessage.success(res.message || '上传成功')
    uploadDialogVisible.value = false
    loadData()
  } finally {
    uploading.value = false
  }
}

onMounted(loadData)
</script>
