<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import MessageItem from './MessageItem.vue'
import aiAssistantLogo from '../assets/images/ai-assistant.svg'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const listRef = ref(null)

// 检查最后一条消息是否是正在流式更新的 assistant 消息
const isStreamingLastMessage = computed(() => {
  const msgs = props.messages
  if (msgs.length === 0) return false
  const lastMsg = msgs[msgs.length - 1]
  return lastMsg?.role === 'assistant' && lastMsg?.streaming === true
})

// 如果最后一条已经是“完成态”的 assistant（有内容），则不再显示“正在思考...”
const isCompletedAssistantAtEnd = computed(() => {
  const msgs = props.messages
  if (msgs.length === 0) return false
  const lastMsg = msgs[msgs.length - 1]
  if (lastMsg?.role !== 'assistant') return false
  const content = (lastMsg?.content || '').toString()
  return content.trim().length > 0 && lastMsg?.streaming !== true
})

// 只有当 loading 为 true 且最后一条消息不是正在流式更新时，才显示 "正在思考..."
const showThinking = computed(() => {
  return props.loading && !isStreamingLastMessage.value && !isCompletedAssistantAtEnd.value
})

// Auto-scroll to bottom when new messages arrive or thinking row appears
watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  }
)
</script>

<template>
  <div ref="listRef" class="message-list">
    <div v-if="messages.length === 0" class="empty-chat">
      <div class="empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
          <path d="M2 17l10 5 10-5"></path>
          <path d="M2 12l10 5 10-5"></path>
        </svg>
      </div>
      <h3>我们该从哪里开始？</h3>
      <p>输入您的问题，开始与西窗对话</p>
    </div>

    <div v-else class="messages-container">
      <MessageItem
        v-for="(message, index) in messages"
        :key="index"
        :message="message"
      />
      <!-- 只有在非流式更新时才显示 "正在思考..." -->
      <div v-if="showThinking" class="thinking-message">
        <div class="thinking-avatar">
          <img :src="aiAssistantLogo" alt="" class="thinking-avatar-img" />
        </div>
        <div class="thinking-content">
          <div class="thinking-role">AI 助手</div>
          <div class="thinking-bubble">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span class="loading-text">正在思考...</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  /* 减少顶部 padding，避免空状态/首条消息离 header 顶部太远 */
  padding: var(--spacing-md) var(--spacing-xl);
  background: transparent;
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  max-width: 800px;
  margin: 0 auto;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 30% 30%, rgba(25, 190, 107, 1) 0%, rgba(16, 185, 129, 0.75) 45%, rgba(25, 190, 107, 0.25) 100%);
  border-radius: 50%;
  margin-bottom: var(--spacing-lg);
  color: var(--text-light);
  box-shadow: var(--shadow-card), var(--glow-primary);
}

.empty-chat h3 {
  font-size: 1.5rem;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm);
}

.empty-chat p {
  font-size: 0.875rem;
  margin: 0;
}

/* 对齐 MessageItem 中 assistant 行：左对齐 + 头像 + 角色名 */
.thinking-message {
  display: flex;
  gap: var(--spacing-md);
  max-width: 85%;
  margin-left: 0;
  flex-direction: row;
}

.thinking-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  background: var(--bg-assistant-message);
  overflow: hidden;
}

.thinking-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thinking-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  min-width: 0;
}

.thinking-role {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: left;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: 0;
  border-bottom-left-radius: 0;
  /* 去掉“正在思考...”提示框外观（你截图里的那一圈框） */
  background: transparent;
  border: none;
  box-shadow: none;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.6;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

</style>
