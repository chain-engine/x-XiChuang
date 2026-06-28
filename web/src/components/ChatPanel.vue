<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import MessageList from './MessageList.vue'
import InputArea from './InputArea.vue'
import { useChat } from '@/composables/useChat.js'
import { getProviders } from '@/services/api.js'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  },
  messages: {
    type: Array,
    default: () => []
  },
  summary: {
    type: String,
    default: ''
  },
  modelProvider: {
    type: String,
    default: 'tongyi'
  }
})

const emit = defineEmits(['update:messages', 'update:summary', 'update:modelProvider', 'append-chat-result'])

// 模型提供商相关
const providers = ref([])
const currentProvider = ref(props.modelProvider)
const selectorRef = ref(null)
const dropdownOpen = ref(false)
const sessionIdRef = ref(props.sessionId)
const { messages: chatMessages, thinkingForCurrentSession, summary, send, loadHistory } = useChat(sessionIdRef, currentProvider, {
  onReplyForOtherSession: ({ sessionId: sid, answer, summary: sum, error }) => {
    emit('append-chat-result', { sessionId: sid, answer, summary: sum, error })
  }
})

function normalizeMessages(messages = []) {
  return messages.map(m => ({
    role: m?.role || '',
    content: m?.content || ''
  }))
}

function isSameMessages(a = [], b = []) {
  const na = normalizeMessages(a)
  const nb = normalizeMessages(b)
  if (na.length !== nb.length) return false
  for (let i = 0; i < na.length; i += 1) {
    if (na[i].role !== nb[i].role || na[i].content !== nb[i].content) {
      return false
    }
  }
  return true
}

// 监听会话变化（含「空会话」：必须 loadHistory([])，否则会残留上一会话消息）
watch(() => props.sessionId, () => {
  sessionIdRef.value = props.sessionId
  const next = props.messages || []
  if (!isSameMessages(next, chatMessages.value)) {
    loadHistory(next)
  }
}, { immediate: true })

// 监听外部消息变化（用于父组件异步拉取详情后回填等）
watch(
  () => props.messages,
  (newMessages) => {
    const next = newMessages || []
    if (!isSameMessages(next, chatMessages.value)) {
      loadHistory(next)
    }
  },
  { deep: true }
)

// 监听本地消息变化并同步到父组件
watch(chatMessages, (newMessages) => {
  if (!isSameMessages(newMessages, props.messages)) {
    emit('update:messages', { conversationId: props.sessionId, messages: newMessages })
  }
}, { deep: true })

// 仅在后端返回非空摘要时写库；切换会话时 loadHistory 会清空本地 summary，避免误把空串同步进 DB
watch(summary, (newSummary) => {
  if (newSummary) {
    emit('update:summary', { conversationId: props.sessionId, summary: newSummary })
  }
})

// 与数据库/父组件同步：切换会话时用该会话的 model_provider，不要被服务端 default 覆盖成 DeepSeek
watch(
  () => props.modelProvider,
  (v) => {
    const next = v && typeof v === 'string' && v.trim() ? v.trim() : 'tongyi'
    if (next !== currentProvider.value) {
      currentProvider.value = next
    }
  },
  { immediate: true }
)

// 初始化时仅拉取提供商列表；当前选中模型以 props（数据库）为准
onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  try {
    const response = await getProviders()
    providers.value = response.providers
  } catch (err) {
    console.error('Failed to load providers:', err)
    providers.value = [
      { name: 'tongyi', display_name: '千问', available: true },
      { name: 'deepseek', display_name: 'DeepSeek', available: false },
      { name: 'glm', display_name: 'GLM', available: false },
      { name: 'doubao', display_name: '豆包', available: false },
      { name: 'kimi', display_name: 'Kimi', available: false },
    ]
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})

const providerDescriptions = {
  tongyi: 'Qwen 系列模型，支持文本和多模态任务。',
  deepseek: 'DeepSeek 通用大模型，适合代码与推理场景。',
  glm: 'GLM 系列模型，支持中文与复杂任务处理。',
  doubao: '豆包模型，适用于多种对话和内容生成任务。',
  kimi: 'Kimi 长文本模型，适合超长上下文问答。'
}

const providerTitleMap = {
  tongyi: 'Qwen3.5-Plus',
  deepseek: 'DeepSeek-Chat',
  glm: 'GLM-4',
  doubao: 'Doubao-Pro',
  kimi: 'Kimi-K2'
}

const panelProviders = computed(() => {
  return providers.value
    .filter((p) => p.available !== false)
    .map((p) => ({
      ...p,
      title: providerTitleMap[p.name] || p.display_name || p.name,
      desc: providerDescriptions[p.name] || `${p.display_name || p.name} 模型能力`
    }))
})

const currentProviderTitle = computed(() => {
  const item = panelProviders.value.find((p) => p.name === currentProvider.value)
  return item?.title || providerTitleMap[currentProvider.value] || currentProvider.value || '模型'
})

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
}

function handleDocumentClick(event) {
  if (!selectorRef.value) return
  if (!selectorRef.value.contains(event.target)) {
    dropdownOpen.value = false
  }
}

function selectProvider(provider) {
  currentProvider.value = provider.name
  emit('update:modelProvider', provider.name)
  dropdownOpen.value = false
}

// 处理发送消息
async function handleSend({ text, file, mediaType }) {
  await send({ text, file, mediaType })
}
</script>

<template>
  <main class="chat-panel">
    <div class="chat-surface">
      <header class="chat-header">
        <div ref="selectorRef" class="model-selector">
          <button class="provider-trigger" type="button" @click="toggleDropdown">
            <svg class="edit-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4Z"></path>
            </svg>
            <span class="provider-trigger-text">{{ currentProviderTitle }}</span>
            <svg class="trigger-chevron" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          <div v-if="dropdownOpen" class="provider-panel">
            <div class="panel-title">模型</div>
            <button
              v-for="p in panelProviders"
              :key="p.name"
              class="provider-option"
              type="button"
              @click="selectProvider(p)"
            >
              <div class="option-main">
                <div class="option-title">{{ p.title }}</div>
                <div class="option-desc">{{ p.desc }}</div>
              </div>
              <svg
                v-if="p.name === currentProvider"
                class="option-check"
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </button>
          </div>
        </div>
      </header>

      <MessageList
        :messages="chatMessages"
        :loading="thinkingForCurrentSession"
      />

      <InputArea
        :disabled="thinkingForCurrentSession"
        @send="handleSend"
      />
    </div>
  </main>
</template>

<style scoped>
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  /* 去掉顶部多余留白，避免“顶部一条空白线” */
  padding: 0 var(--chat-surface-margin) var(--chat-surface-margin) 0;
}

.chat-surface {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-chat);
  /* 去掉聊天框外圈线条 */
  border: none;
  border-radius: 0;
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.chat-header {
  padding: var(--spacing-md) var(--spacing-xl);
  min-height: var(--header-height);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-chat);
  display: flex;
  align-items: center;
}

.model-selector {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.provider-trigger {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 0;
}

.provider-trigger-text {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.trigger-chevron {
  color: var(--text-secondary);
}

.edit-icon {
  color: var(--text-secondary);
}

.provider-panel {
  position: absolute;
  top: calc(100% + 10px);
  left: 38px;
  width: 520px;
  max-width: min(520px, calc(100vw - 40px));
  background: var(--bg-chat);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  padding: 18px 18px 14px;
  z-index: 12;
}

.panel-title {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 10px;
  font-weight: 600;
}

.provider-option {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 10px 8px;
  border-radius: 10px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  cursor: pointer;
}

.provider-option:hover {
  background: var(--bg-elevated-2);
}

.option-title {
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
}

.option-desc {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.35;
}

.option-check {
  margin-top: 6px;
  color: var(--color-primary);
  flex-shrink: 0;
}

.summary-bar {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--bg-assistant-message);
  border-top: 1px solid var(--border-color);
  font-size: 0.875rem;
}

.summary-label {
  color: var(--text-secondary);
  margin-right: var(--spacing-sm);
}

.summary-text {
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .chat-panel {
    padding: 0;
  }

  .chat-surface {
    border-radius: 0;
    border: none;
    box-shadow: none;
  }
}

@media (max-width: 640px) {
  .chat-header {
    padding: var(--spacing-md);
  }

  .provider-trigger-text {
    font-size: 0.95rem;
  }

  .provider-panel {
    left: 0;
    width: min(510px, calc(100vw - 24px));
    padding: 14px;
    border-radius: 12px;
  }

  .panel-title {
    font-size: 0.85rem;
  }

  .option-title {
    font-size: 0.95rem;
  }

  .option-desc {
    font-size: 0.875rem;
  }
}
</style>
