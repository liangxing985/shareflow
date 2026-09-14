<template>
  <div class="page-container">
    <div class="table-toolbar">
      <el-button type="primary" :icon="Plus" @click="showDialog()">新建分账规则</el-button>
      <el-alert title="分账规则按优先级匹配：指定规则 > 按分类 > 全局默认。一级分账比例合计不能超过100%。" type="info" :closable="false" show-icon style="flex: 1; margin-left: 16px" />
    </div>

    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="name" label="规则名称" width="180" />
        <el-table-column prop="scope_type" label="适用范围" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.scope_type === 'global' ? 'success' : row.scope_type === 'category' ? 'warning' : 'info'">
              {{ { global: '全局', category: '按分类', specific: '指定' }[row.scope_type as 'global' | 'category' | 'specific'] || row.scope_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scope_value" label="范围值" width="120" />
        <el-table-column prop="platform_fee_rate" label="平台抽成" width="100" align="right">
          <template #default="{ row }">{{ (Number(row.platform_fee_rate) * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="分账方" min-width="250">
          <template #default="{ row }">
            <div class="shareholders-list">
              <el-tag v-for="(d, i) in row.share_details" :key="i" size="small" :type="d.level > 1 ? 'warning' : ''" style="margin: 2px">
                {{ getShareholderName(d.shareholder_id) }} {{ (Number(d.rate) * 100).toFixed(0) }}%
                <el-tag v-if="d.level > 1" size="small" type="warning" style="margin-left: 4px">L{{ d.level }}</el-tag>
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="is_default" label="默认" width="70" align="center">
          <template #default="{ row }"><el-tag v-if="row.is_default" type="success" size="small">默认</el-tag></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }"><el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="setDefault(row)" :disabled="row.is_default">设为默认</el-button>
            <el-button link type="danger" size="small" @click="deleteRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑分账规则' : '新建分账规则'" width="700px" top="5vh">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-form-item label="规则名称" required>
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="999" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="适用范围">
              <el-select v-model="form.scope_type" style="width: 100%" @change="form.scope_value = ''">
                <el-option label="全局" value="global" />
                <el-option label="按业务分类" value="category" />
                <el-option label="指定订单" value="specific" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="form.scope_type !== 'global'">
            <el-form-item label="范围值">
              <el-input v-model="form.scope_value" :placeholder="form.scope_type === 'category' ? '分类名称' : '订单号'" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="平台抽成比例">
              <el-input-number v-model="form.platform_fee_rate" :min="0" :max="1" :step="0.05" :precision="4" style="width: 100%" />
              <span style="font-size: 12px; color: #909399">{{ (Number(form.platform_fee_rate) * 100).toFixed(1) }}%</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用多级分账">
              <el-switch v-model="form.enable_multi_level" />
              <span style="margin-left: 8px; font-size: 12px; color: #909399">二级分账基于一级金额计算</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">分账明细配置</el-divider>
        <div class="share-details-config">
          <div v-for="(detail, index) in form.share_details" :key="index" class="detail-row">
            <el-select v-model="detail.shareholder_id" placeholder="选择分账方" style="width: 180px" filterable>
              <el-option v-for="sh in shareholderOptions" :key="sh.id" :label="sh.name" :value="sh.id" />
            </el-select>
            <el-input-number v-model="detail.rate" :min="0" :max="1" :step="0.05" :precision="4" placeholder="比例" style="width: 130px" />
            <span style="width: 50px; color: #909399">{{ (Number(detail.rate) * 100).toFixed(1) }}%</span>
            <el-select v-model="detail.level" placeholder="层级" style="width: 90px">
              <el-option label="一级" :value="1" />
              <el-option v-if="form.enable_multi_level" label="二级" :value="2" />
            </el-select>
            <el-select v-if="detail.level > 1" v-model="detail.parent_id" placeholder="上级分账方" style="width: 150px" filterable>
              <el-option v-for="d in form.share_details.filter((x, i) => i < index && x.level === 1)" :key="d.shareholder_id" :label="getShareholderName(d.shareholder_id)" :value="d.shareholder_id" />
            </el-select>
            <el-button link type="danger" @click="removeDetail(index)"><Delete /></el-button>
          </div>
          <el-button type="primary" plain :icon="Plus" @click="addDetail" size="small">添加分账方</el-button>
          <div class="rate-summary">
            一级分账比例合计: <b :class="{ 'text-danger': level1Rate > 1.0001 }">{{ (level1Rate * 100).toFixed(1) }}%</b>
            <span v-if="level1Rate > 1.0001" class="text-danger">（超过100%，请调整）</span>
          </div>
        </div>

        <el-form-item label="设为默认" style="margin-top: 16px">
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { getShareRules, createShareRule, updateShareRule, deleteShareRule, setDefaultRule } from '@/api/shareRules'
import { getShareholders } from '@/api/shareholders'

const loading = ref(false)
const saving = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const shareholderOptions = ref<any[]>([])

const form = reactive({
  name: '', scope_type: 'global', scope_value: '', platform_fee_rate: 0.1,
  share_details: [] as any[], enable_multi_level: false, max_levels: 2,
  is_default: false, priority: 0, remark: ''
})

const level1Rate = computed(() => form.share_details.filter(d => d.level === 1).reduce((sum, d) => sum + Number(d.rate || 0), 0))

function getShareholderName(id: number) {
  return shareholderOptions.value.find(s => s.id === id)?.name || `未知(${id})`
}

async function loadData() {
  loading.value = true
  try {
    const res = await getShareRules({ page_size: 100 })
    tableData.value = res.items
  } finally {
    loading.value = false
  }
}

async function loadShareholders() {
  const res = await getShareholders({ page_size: 100, status: 'active' })
  shareholderOptions.value = res.items
}

function showDialog(row?: any) {
  if (row) {
    editId.value = row.id
    Object.assign(form, {
      name: row.name, scope_type: row.scope_type, scope_value: row.scope_value,
      platform_fee_rate: Number(row.platform_fee_rate), share_details: JSON.parse(JSON.stringify(row.share_details || [])),
      enable_multi_level: row.enable_multi_level, max_levels: row.max_levels,
      is_default: row.is_default, priority: row.priority, remark: row.remark
    })
  } else {
    editId.value = null
    Object.assign(form, {
      name: '', scope_type: 'global', scope_value: '', platform_fee_rate: 0.1,
      share_details: [], enable_multi_level: false, max_levels: 2,
      is_default: false, priority: 0, remark: ''
    })
  }
  dialogVisible.value = true
}

function addDetail() {
  form.share_details.push({ shareholder_id: null, rate: 0, level: 1, parent_id: null })
}
function removeDetail(index: number) {
  form.share_details.splice(index, 1)
}

async function submit() {
  if (!form.name) { ElMessage.warning('请输入规则名称'); return }
  if (form.share_details.length === 0) { ElMessage.warning('请至少添加一个分账方'); return }
  if (form.share_details.some(d => !d.shareholder_id)) { ElMessage.warning('请选择所有分账方'); return }
  if (level1Rate.value > 1.0001) { ElMessage.warning('一级分账比例合计不能超过100%'); return }

  saving.value = true
  try {
    const data = { ...form, share_details: form.share_details.map(d => ({ shareholder_id: d.shareholder_id, rate: d.rate, level: d.level, parent_id: d.parent_id || null })) }
    if (editId.value) {
      await updateShareRule(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createShareRule(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function setDefault(row: any) {
  await setDefaultRule(row.id)
  ElMessage.success('已设为默认规则')
  loadData()
}

async function deleteRule(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除规则"${row.name}"吗？`, '确认', { type: 'warning' })
    await deleteShareRule(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(() => { loadData(); loadShareholders() })
</script>

<style scoped lang="scss">
.table-toolbar { margin-bottom: 16px; display: flex; align-items: center; }
.shareholders-list { display: flex; flex-wrap: wrap; }
.share-details-config { background: #f5f7fa; padding: 16px; border-radius: 8px; }
.detail-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.rate-summary { margin-top: 12px; font-size: 14px; color: #606266; }
</style>
