<script setup>
import { ref, computed } from 'vue'
import { useRecorder } from '@/composables/useRecorder.js'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send'])

const text = ref('')
const fileInputRef = ref(null)
const selectedFile = ref(null)
const mediaType = ref('auto')

const { recording, toggleRecording } = useRecorder()

// 媒体类型选项
const mediaTypeOptions = [
  { value: 'auto', label: '自动' },
  { value: 'text', label: '文本' },
  { value: 'voice', label: '语音' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' }
]

// 是否有待发送的文件
const hasPendingFile = computed(() => selectedFile.value !== null)

// 文件预览信息
const filePreview = computed(() => {
  if (!selectedFile.value) return null
  const file = selectedFile.value
  const sizeKB = (file.size / 1024).toFixed(1)
  return {
    name: file.name.length > 20 ? file.name.slice(0, 20) + '...' : file.name,
    size: sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`
  }
})


function handleSend() {
  const trimmedText = text.value.trim()
  const file = selectedFile.value

  if (!trimmedText && !file) {
    return
  }

  emit('send', {
    text: trimmedText,
    file: file,
    mediaType: file ? mediaType.value : 'text'
  })

  // 清空输入
  text.value = ''
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    // 不立即发送，等待用户输入提示词
  }
}

function clearSelectedFile() {
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function handleRecordClick() {
  try {
    const blob = await toggleRecording()
    if (blob) {
      // 录音完成后，设置为待发送状态
      selectedFile.value = new File([blob], 'recording.webm', { type: 'audio/webm' })
      mediaType.value = 'voice'
    }
  } catch (err) {
    console.error('Recording error:', err)
    alert(err.message || '录音失败')
  }
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="input-area">
    <div class="input-container">
      <!-- 待发送文件预览 -->
      <div v-if="hasPendingFile" class="file-preview">
        <div class="file-info">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
          </svg>
          <span class="file-name">{{ filePreview?.name }}</span>
          <span class="file-size">{{ filePreview?.size }}</span>
        </div>
        <div class="file-actions">
          <select v-model="mediaType" class="media-type-select">
            <option v-for="opt in mediaTypeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
          <button class="clear-btn" @click="clearSelectedFile" title="移除文件">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- 主输入行 -->
      <div class="input-row">
        <label class="file-btn" title="上传文件">
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*,audio/*,video/*"
            @change="handleFileSelect"
            :disabled="disabled"
          />
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
          </svg>
        </label>

        <textarea
          v-model="text"
          :placeholder="hasPendingFile ? '输入提示词后点击发送...' : '输入你的问题... (Enter 发送, Shift+Enter 换行)'"
          rows="1"
          :disabled="disabled"
          @keydown="handleKeydown"
        ></textarea>

        <button
          :class="['record-btn', { active: recording }]"
          type="button"
          @click="handleRecordClick"
          :disabled="disabled"
          title="录音"
        >
          <svg v-if="!recording" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2"></rect>
          </svg>
        </button>

        <button
          class="send-btn"
          type="button"
          @click="handleSend"
          :disabled="disabled || (!text.trim() && !hasPendingFile)"
          title="发送"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.input-area {
  padding: var(--spacing-md) var(--spacing-xl);
  background: var(--bg-chat);
  border-top: 1px solid var(--border-subtle);
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.file-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.file-name {
  font-weight: 500;
}

.file-size {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.media-type-select {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  background: var(--bg-chat);
  color: var(--text-primary);
  cursor: pointer;
}

.clear-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.clear-btn:hover {
  background: var(--color-danger);
  color: var(--text-light);
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-sm);
}

.file-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-chat);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
}

.file-btn:hover {
  border-color: var(--border-focus);
  color: var(--color-primary);
  background: var(--color-primary-muted);
  box-shadow: var(--glow-primary);
}

.file-btn input {
  display: none;
}

textarea {
  flex: 1;
  resize: none;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px var(--spacing-md);
  font-size: 0.9375rem;
  line-height: 1.5;
  max-height: 120px;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--bg-chat);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

textarea:focus {
  outline: none;
  border-color: rgba(34, 197, 94, 0.5);
  box-shadow: var(--glow-primary);
}

textarea::placeholder {
  color: var(--text-secondary);
}

.record-btn,
.send-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-fast);
}

.record-btn {
  background: var(--bg-chat);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.record-btn:hover:not(:disabled) {
  background: rgba(232, 93, 93, 0.08);
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.record-btn.active {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: var(--text-light);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.send-btn {
  border: 1px solid var(--color-primary);
  background: linear-gradient(135deg, rgba(25, 190, 107, 0.95) 0%, rgba(16, 185, 129, 0.92) 100%);
  color: var(--text-light);
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(22, 163, 74, 0.98) 0%, rgba(16, 185, 129, 0.95) 100%);
  border-color: var(--border-focus);
  box-shadow: var(--glow-primary);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .input-area {
    padding: var(--spacing-sm);
  }

  .media-type-select {
    font-size: 0.7rem;
    padding: 2px 6px;
  }
}
</style>
