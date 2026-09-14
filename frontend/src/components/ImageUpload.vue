<template>
  <div class="image-upload">
    <el-upload
      :action="uploadUrl"
      :headers="headers"
      :show-file-list="false"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      accept="image/*"
      class="image-uploader"
    >
      <div v-if="modelValue" class="image-preview">
        <img :src="modelValue" alt="预览" class="preview-img" />
        <div class="image-mask">
          <el-icon><Edit /></el-icon>
          <span>点击更换</span>
        </div>
      </div>
      <div v-else class="image-placeholder">
        <el-icon :size="32" color="#c0c4cc"><Plus /></el-icon>
        <p>点击上传图片</p>
        <p class="hint">支持 jpg/png/gif，最大10MB</p>
      </div>
    </el-upload>
    <div v-if="modelValue" class="image-actions">
      <el-button link type="danger" size="small" @click="handleRemove">
        <el-icon><Delete /></el-icon> 移除
      </el-button>
      <el-button link type="primary" size="small" @click="previewVisible = true">
        <el-icon><ZoomIn /></el-icon> 查看大图
      </el-button>
    </div>
    <el-image-viewer
      v-if="previewVisible && modelValue"
      :url-list="[modelValue]"
      @close="previewVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, ZoomIn } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

const props = defineProps<{
  modelValue: string
  maxSize?: number // MB
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const userStore = useUserStore()
const previewVisible = ref(false)

const uploadUrl = computed(() => '/api/v1/uploads/image')

const headers = computed(() => ({
  Authorization: `Bearer ${userStore.token}`
}))

function beforeUpload(file: File) {
  const maxSize = props.maxSize || 10
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (file.size / 1024 / 1024 > maxSize) {
    ElMessage.error(`图片大小不能超过 ${maxSize}MB`)
    return false
  }
  return true
}

function handleSuccess(response: any) {
  if (response.url) {
    emit('update:modelValue', response.url)
    ElMessage.success('上传成功')
  } else {
    ElMessage.error('上传失败')
  }
}

function handleError() {
  ElMessage.error('上传失败，请检查网络或登录状态')
}

function handleRemove() {
  emit('update:modelValue', '')
}
</script>

<style scoped lang="scss">
.image-upload {
  width: 100%;
}

.image-uploader {
  width: 100%;
}

.image-preview {
  position: relative;
  width: 200px;
  height: 200px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;

  .preview-img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .image-mask {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    opacity: 0;
    transition: opacity 0.3s;
    gap: 8px;

    .el-icon {
      font-size: 24px;
    }
  }

  &:hover .image-mask {
    opacity: 1;
  }
}

.image-placeholder {
  width: 200px;
  height: 200px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.3s;

  &:hover {
    border-color: #409eff;
  }

  p {
    margin: 8px 0 0;
    font-size: 14px;
    color: #606266;
  }

  .hint {
    font-size: 12px;
    color: #c0c4cc;
    margin-top: 4px;
  }
}

.image-actions {
  margin-top: 8px;
  display: flex;
  gap: 16px;
}
</style>
