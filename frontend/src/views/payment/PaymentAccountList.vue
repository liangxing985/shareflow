<template>
  <div class="page-container">
    <div class="table-toolbar">
      <el-button type="primary" :icon="Plus" @click="showDialog()">添加收款账户</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="account_name" label="账户名称" width="180" />
        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.platform === 'wechat' ? 'success' : row.platform === 'alipay' ? 'primary' : 'info'">
              {{ platformText(row.platform) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="account_no" label="账号" width="180" />
        <el-table-column prop="bank_name" label="银行" width="150" />
        <el-table-column prop="is_default" label="默认" width="80" align="center">
          <template #default="{ row }"><el-tag v-if="row.is_default" type="success" size="small">默认</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }"><el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at ? row.created_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteAccount(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑收款账户' : '添加收款账户'" width="550px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="平台" required>
          <el-radio-group v-model="form.platform">
            <el-radio value="wechat">微信</el-radio>
            <el-radio value="alipay">支付宝</el-radio>
            <el-radio value="bank">银行卡</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="账户名称" required>
          <el-input v-model="form.account_name" placeholder="如：微信-张三" />
        </el-form-item>
        <el-form-item label="账号">
          <el-input v-model="form.account_no" placeholder="微信号/支付宝账号" />
        </el-form-item>
        <el-form-item label="收款码URL" v-if="form.platform !== 'bank'">
          <el-input v-model="form.qr_code_url" placeholder="收款码图片地址" />
        </el-form-item>
        <template v-if="form.platform === 'bank'">
          <el-form-item label="开户银行">
            <el-input v-model="form.bank_name" />
          </el-form-item>
          <el-form-item label="银行卡号">
            <el-input v-model="form.bank_card_no" />
          </el-form-item>
        </template>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getPaymentAccounts, createPaymentAccount, updatePaymentAccount, deletePaymentAccount } from '@/api/paymentAccounts'

const loading = ref(false)
const saving = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const editId = ref<number | null>(null)

const form = reactive({
  platform: 'wechat', account_name: '', account_no: '', qr_code_url: '',
  bank_name: '', bank_card_no: '', is_default: false, remark: ''
})

function platformText(platform: string) {
  return { wechat: '微信', alipay: '支付宝', bank: '银行卡' }[platform as 'wechat'|'alipay'|'bank'] || platform
}

async function loadData() {
  loading.value = true
  try {
    const res = await getPaymentAccounts({ page_size: 100 })
    tableData.value = res.items
  } finally {
    loading.value = false
  }
}

function showDialog(row?: any) {
  if (row) {
    editId.value = row.id
    Object.assign(form, { platform: row.platform, account_name: row.account_name, account_no: row.account_no, qr_code_url: row.qr_code_url, bank_name: row.bank_name, bank_card_no: row.bank_card_no, is_default: row.is_default, remark: row.remark })
  } else {
    editId.value = null
    Object.assign(form, { platform: 'wechat', account_name: '', account_no: '', qr_code_url: '', bank_name: '', bank_card_no: '', is_default: false, remark: '' })
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.account_name) { ElMessage.warning('请输入账户名称'); return }
  saving.value = true
  try {
    if (editId.value) {
      await updatePaymentAccount(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createPaymentAccount(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function deleteAccount(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除账户"${row.account_name}"吗？`, '确认', { type: 'warning' })
    await deletePaymentAccount(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败') }
}

onMounted(loadData)
</script>
