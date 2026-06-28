<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import assistantAvatar from '../assets/images/assistant.jpg'
import aiAssistantLogo from '../assets/images/ai-assistant.svg'

// 配置 marked 使用自定义渲染器
const renderer = {
  code(code, language) {
    let highlighted
    if (language && hljs.getLanguage(language)) {
      try {
        highlighted = hljs.highlight(code, { language }).value
      } catch {
        highlighted = hljs.highlightAuto(code).value
      }
    } else {
      highlighted = hljs.highlightAuto(code).value
    }
    return `<pre><code class="hljs">${highlighted}</code></pre>`
  }
}

marked.use({ renderer })

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const renderedContent = computed(() => {
  const content = props.message.content || ''
  if (!content) return ''
  const html = marked.parse(content, { breaks: true, gfm: true })
  return DOMPurify.sanitize(html)
})

// 流式刚开始会先 push 一条 content 为空的 assistant；
// 此时 message-text 会渲染出边框/内边距，像“空框”，所以 content 为空时不渲染 message-text。
const showMessageText = computed(() => {
  const content = props.message.content ?? ''
  return content.toString().length > 0
})
</script>

<template>
  <div :class="['message-item', message.role]">
    <div class="message-avatar">
      <img
        v-if="message.role === 'user'"
        :src="assistantAvatar"
        alt="avatar"
        class="avatar-img"
      />
      <img
        v-else
        :src="aiAssistantLogo"
        alt=""
        class="avatar-img"
      />
    </div>
    <div class="message-content">
      <div class="message-role">{{ message.role === 'user' ? '你' : 'AI 助手' }}</div>
      <div v-if="showMessageText" class="message-text" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<style scoped>
.message-item {
  display: flex;
  gap: var(--spacing-md);
  max-width: 85%;
}

.message-item.user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-item.assistant {
  margin-left: 0;
  flex-direction: row;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
  background: var(--bg-assistant-message);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.message-item.user .message-avatar {
  background: var(--color-primary);
  border: 1px solid rgba(34, 197, 94, 0.35);
  box-shadow: var(--glow-primary);
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.message-role {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.message-item.user .message-role {
  text-align: right;
}

.message-item.assistant .message-role {
  text-align: left;
}

.message-text {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: 0;
  line-height: 1.6;
  word-break: break-word;
}

.message-item.assistant .message-text {
  background: var(--bg-assistant-card);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  border-bottom-left-radius: 0;
}

.message-item.user .message-text {
  background: var(--bg-user-message);
  color: var(--text-light);
  border: 1px solid transparent;
  border-bottom-right-radius: 0;
  box-shadow: var(--shadow-sm), var(--glow-primary);
}

/* Markdown 样式 */
.message-text :deep(h1) { font-size: 1.5em; font-weight: 600; margin: 0.5em 0 0.3em; }
.message-text :deep(h2) { font-size: 1.3em; font-weight: 600; margin: 0.5em 0 0.3em; }
.message-text :deep(h3) { font-size: 1.15em; font-weight: 600; margin: 0.5em 0 0.3em; }
.message-text :deep(h4) { font-size: 1em; font-weight: 600; margin: 0.5em 0 0.3em; }

.message-text :deep(p) { margin: 0.4em 0; }

.message-text :deep(ul), .message-text :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.5em;
}

.message-text :deep(li) { margin: 0.2em 0; }

/* 行内代码 */
.message-text :deep(code) {
  background: rgba(0, 0, 0, 0.1);
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}

/* 代码块 */
.message-text :deep(pre) {
  margin: 0.8em 0;
  padding: 1em;
  background: #1e1e1e;
  border-radius: 8px;
  overflow-x: auto;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
  font-size: 0.9em;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre;
}

/* 代码高亮 */
.message-text :deep(.hljs-keyword) { color: #569cd6; }
.message-text :deep(.hljs-string) { color: #ce9178; }
.message-text :deep(.hljs-number) { color: #b5cea8; }
.message-text :deep(.hljs-comment) { color: #6a9955; }
.message-text :deep(.hljs-function) { color: #dcdcaa; }
.message-text :deep(.hljs-class) { color: #4ec9b0; }
.message-text :deep(.hljs-variable) { color: #9cdcfe; }

.message-text :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.3em 0.8em;
  border-left: 3px solid var(--color-primary);
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-secondary);
}

.message-text :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
  width: 100%;
}

.message-text :deep(th), .message-text :deep(td) {
  border: 1px solid var(--border-subtle);
  padding: 0.4em 0.6em;
  text-align: left;
}

.message-text :deep(th) {
  background: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

.message-text :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

/* 用户消息的代码块样式 */
.message-item.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}

.message-item.user .message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.2);
}
</style>
