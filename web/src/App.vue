<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatPanel from './components/ChatPanel.vue'
import {
  getConversations,
  createConversation,
  getConversation,
  updateConversation,
  deleteConversation as apiDeleteConversation,
  saveMessages
} from './services/api.js'

// 状态
const conversations = ref([])
const activeId = ref(null)
const modelProvider = ref('tongyi')
const loading = ref(false)
const useDatabase = ref(true) // 是否使用数据库存储

// 计算属性
const activeConversation = computed(() => {
  return conversations.value.find(c => c.id === activeId.value) || null
})

/** 当前会话在数据库中保存的模型（与下拉框一致）；无记录时默认千问 */
const activeModelProvider = computed(() => {
  const c = activeConversation.value
  if (!c) return 'tongyi'
  return c.model_provider || 'tongyi'
})

// 从 localStorage 加载（作为后备）
function loadFromLocalStorage() {
  const saved = localStorage.getItem('chat-conversations')
  if (saved) {
    try {
      return JSON.parse(saved)
    } catch {
      return []
    }
  }
  return []
}

// 保存到 localStorage（作为后备）
function saveToLocalStorage(convs) {
  localStorage.setItem('chat-conversations', JSON.stringify(convs))
}

// 初始化
onMounted(async () => {
  // 新建会话时默认模型（仍可用 localStorage 作为偏好）
  const savedProvider = localStorage.getItem('model-provider')
  if (savedProvider) {
    modelProvider.value = savedProvider
  }

  // 尝试从数据库加载
  try {
    const data = await getConversations()
    conversations.value = data.map(c => ({
      ...c,
      messages: [] // 列表不包含消息，需要时加载
    }))
    useDatabase.value = true
  } catch (err) {
    console.warn('Failed to load from database, using localStorage:', err)
    // 后备使用 localStorage
    conversations.value = loadFromLocalStorage()
    useDatabase.value = false
  }

  if (conversations.value.length === 0) {
    await createNewConversation()
  } else {
    // 与点击侧边栏一致：拉取首条会话详情（含消息），避免首屏 messages 一直为空
    await selectConversation(conversations.value[0].id)
  }
})

// 创建新对话
async function createNewConversation() {
  const id = crypto.randomUUID()

  const defaultProvider = modelProvider.value || 'tongyi'
  if (useDatabase.value) {
    try {
      await createConversation({ id, model_provider: defaultProvider })
    } catch (err) {
      console.error('Failed to create conversation:', err)
    }
  }

  const newConv = {
    id,
    title: '新对话',
    messages: [],
    model_provider: defaultProvider,
    createdAt: Date.now()
  }
  conversations.value.unshift(newConv)
  activeId.value = newConv.id

  if (!useDatabase.value) {
    saveToLocalStorage(conversations.value)
  }
}

// 选择对话
async function selectConversation(id) {
  activeId.value = id

  // 从数据库加载消息
  if (useDatabase.value) {
    const conv = conversations.value.find(c => c.id === id)
    if (conv && (!conv.messages || conv.messages.length === 0)) {
      try {
        const data = await getConversation(id)
        conv.messages = data.messages || []
        conv.title = data.title
        conv.summary = data.summary
        if (data.model_provider) {
          conv.model_provider = data.model_provider
        }
      } catch (err) {
        console.error('Failed to load conversation:', err)
      }
    }
  }
}

// 解析「带会话 id」的 payload（避免切换会话后仍用 activeId 写错对话）
function parseMessagesPayload(payload) {
  if (payload && typeof payload === 'object' && 'conversationId' in payload && 'messages' in payload) {
    return { conversationId: payload.conversationId, messages: payload.messages }
  }
  return { conversationId: activeId.value, messages: payload }
}

function parseSummaryPayload(payload) {
  if (payload && typeof payload === 'object' && 'conversationId' in payload && 'summary' in payload) {
    return { conversationId: payload.conversationId, summary: payload.summary }
  }
  return { conversationId: activeId.value, summary: payload }
}

// 更新对话消息（始终写入 payload 指定的会话，而不是当前选中的会话）
async function updateMessages(payload) {
  const { conversationId, messages } = parseMessagesPayload(payload)
  const conv = conversations.value.find(c => c.id === conversationId)
  if (conv) {
    conv.messages = [...messages]
    // 根据第一条用户消息更新标题
    if (conv.title === '新对话' && messages.length > 0) {
      const firstUserMsg = messages.find(m => m.role === 'user')
      if (firstUserMsg) {
        conv.title = firstUserMsg.content.slice(0, 20) + (firstUserMsg.content.length > 20 ? '...' : '')
      }
    }

    // 保存到数据库
    if (useDatabase.value) {
      try {
        await saveMessages(conversationId, messages)
      } catch (err) {
        console.error('Failed to save messages:', err)
      }
    } else {
      saveToLocalStorage(conversations.value)
    }
  }
}

// 等待期间切换会话时：把模型回复追加到「发起请求」的会话
async function appendChatResult({ sessionId, answer, summary: sum, error }) {
  const conv = conversations.value.find(c => c.id === sessionId)
  if (!conv) return
  const content = error != null ? error : answer
  if (content == null) return
  conv.messages = [...(conv.messages || []), { role: 'assistant', content }]
  if (sum) conv.summary = sum

  if (useDatabase.value) {
    try {
      await saveMessages(sessionId, conv.messages)
      if (sum) await updateConversation(sessionId, { summary: sum })
    } catch (err) {
      console.error('Failed to save cross-session reply:', err)
    }
  } else {
    saveToLocalStorage(conversations.value)
  }
}

// 更新对话摘要
async function updateSummary(payload) {
  const { conversationId, summary } = parseSummaryPayload(payload)
  const conv = conversations.value.find(c => c.id === conversationId)
  if (conv) {
    conv.summary = summary

    if (useDatabase.value) {
      try {
        await updateConversation(conversationId, { summary })
      } catch (err) {
        console.error('Failed to update summary:', err)
      }
    } else {
      saveToLocalStorage(conversations.value)
    }
  }
}

// 更新模型提供商：写回当前会话 + 数据库（不再只用全局 localStorage）
async function updateModelProvider(provider) {
  modelProvider.value = provider
  localStorage.setItem('model-provider', provider)

  const conv = activeConversation.value
  if (conv) {
    conv.model_provider = provider
    if (useDatabase.value) {
      try {
        await updateConversation(conv.id, { model_provider: provider })
      } catch (err) {
        console.error('Failed to update model_provider:', err)
      }
    } else {
      saveToLocalStorage(conversations.value)
    }
  }
}

// 删除对话
async function deleteConversation(id) {
  const index = conversations.value.findIndex(c => c.id === id)
  if (index !== -1) {
    conversations.value.splice(index, 1)

    if (useDatabase.value) {
      try {
        await apiDeleteConversation(id)
      } catch (err) {
        console.error('Failed to delete conversation:', err)
      }
    } else {
      saveToLocalStorage(conversations.value)
    }

    // 如果删除的是当前活动对话，选择另一个
    if (activeId.value === id) {
      if (conversations.value.length > 0) {
        await selectConversation(conversations.value[0].id)
      } else {
        await createNewConversation()
      }
    }
  }
}
</script>

<template>
  <div class="app-container">
    <Sidebar
      :conversations="conversations"
      :active-id="activeId"
      @select="selectConversation"
      @new="createNewConversation"
      @delete="deleteConversation"
    />
    <ChatPanel
      v-if="activeConversation"
      :session-id="activeId"
      :messages="activeConversation.messages"
      :summary="activeConversation.summary"
      :model-provider="activeModelProvider"
      @update:messages="updateMessages"
      @update:summary="updateSummary"
      @append-chat-result="appendChatResult"
      @update:model-provider="updateModelProvider"
    />
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100%;
  min-height: 100%;
  background: var(--bg-main);
}
</style>
