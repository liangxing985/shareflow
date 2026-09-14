<template>
  <div class="page-container">
    <div class="table-toolbar">
      <el-button type="primary" :icon="Plus" @click="showDialog()">添加用户</el-button>
    </div>
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="roleType(row.role)">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }"><el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '正常' : '禁用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">{{ row.last_login_at ? row.last_login_at.substring(0, 16).replace('T', ' ') : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteUser(row)" :disabled="row.id === currentUserId">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑用户' : '添加用户'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!editId" />
        </el-form-item>
        <el-form-item label="密码" :required="!editId">
          <el-input v-model="form.password" type="password" :placeholder="editId ? '不修改请留空' : '请输入密码'" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.full_name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="运营主管" value="manager" />
            <el-option label="财务" value="finance" />
            <el-option label="运营" value="operator" />
            <el-option label="只读" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
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
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser as apiDeleteUser } from '@/api/users'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.userInfo?.id)

const loading = ref(false)
const saving = ref(false)
const tableData = ref<any[]>([])
const dialogVisible = ref(false)
const editId = ref<number | null>(null)

const form = reactive({ username: '', password: '', full_name: '', email: '', phone: '', role: 'operator', status: 'active' })

async function loadData() {
  loading.value = true
  try {
    const res = await getUsers({ page_size: 100 })
    tableData.value = res.items
  } finally {
    loading.value = false
  }
}

function showDialog(row?: any) {
  if (row) {
    editId.value = row.id
    Object.assign(form, { username: row.username, password: '', full_name: row.full_name, email: row.email, phone: row.phone, role: row.role, status: row.status })
  } else {
    editId.value = null
    Object.assign(form, { username: '', password: '', full_name: '', email: '', phone: '', role: 'operator', status: 'active' })
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.username) { ElMessage.warning('请输入用户名'); return }
  if (!editId.value && !form.password) { ElMessage.warning('请输入密码'); return }
  saving.value = true
  try {
    if (editId.value) {
      const data: any = { ...form }
      if (!data.password) delete data.password
      await updateUser(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createUser(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    saving.value = false
  }
}

async function deleteUser(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除用户"${row.username}"吗？`, '确认', { type: 'warning' })
    await apiDeleteUser(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败') }
}

function roleType(role: string) {
  return { admin: 'danger', manager: 'warning', finance: 'success', operator: '', viewer: 'info' }[role] || ''
}
function roleText(role: string) {
  return { admin: '管理员', manager: '运营主管', finance: '财务', operator: '运营', viewer: '只读' }[role] || role
}

onMounted(loadData)
</script>
