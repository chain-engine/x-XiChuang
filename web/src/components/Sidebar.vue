<script setup>
defineProps({
  conversations: {
    type: Array,
    required: true
  },
  activeId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['select', 'new', 'delete'])

function formatDate(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`

  return date.toLocaleDateString('zh-CN')
}

function handleDelete(e, id) {
  e.stopPropagation()
  if (confirm('确定要删除这个对话吗？')) {
    emit('delete', id)
  }
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="logo">西窗</h1>
      <button class="new-chat-btn" @click="$emit('new')" title="新建对话">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

    <div class="conversation-list">
      <div class="list-header">所有对话</div>

      <div
        v-for="conv in conversations"
        :key="conv.id"
        :class="['conversation-item', { active: conv.id === activeId }]"
        @click="$emit('select', conv.id)"
      >
        <svg class="conv-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <div class="conv-info">
          <span class="conv-title">{{ conv.title }}</span>
          <span class="conv-time">{{ formatDate(conv.createdAt || conv.updated_at) }}</span>
        </div>
        <button class="delete-btn" @click="handleDelete($event, conv.id)" title="删除">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>

      <div v-if="conversations.length === 0" class="empty-state">
        <p>暂无对话</p>
        <p class="hint">点击上方按钮开始新对话</p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100%;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-md);
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-sidebar);
  margin: 0;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: radial-gradient(circle at 30% 30%, rgba(25, 190, 107, 1), rgba(25, 190, 107, 0.18));
  box-shadow: var(--glow-primary);
  flex-shrink: 0;
}

.new-chat-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  color: var(--text-sidebar-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.new-chat-btn:hover {
  background: var(--bg-sidebar-hover);
  border-color: var(--border-focus);
  color: var(--color-primary);
  box-shadow: var(--glow-primary);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.list-header {
  font-size: 0.75rem;
  color: var(--text-sidebar-muted);
  padding: var(--spacing-sm) var(--spacing-md);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.85;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  padding-left: calc(var(--spacing-md) - 3px);
  border-left: 3px solid transparent;
  border-radius: 0;
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
  margin-bottom: 2px;
}

.conversation-item:hover {
  background: var(--bg-sidebar-hover);
}

.conversation-item.active {
  background: var(--bg-sidebar-active);
  border-left-color: transparent;
  box-shadow: none;
}

.conv-icon {
  color: var(--text-sidebar-muted);
  flex-shrink: 0;
}

.conversation-item.active .conv-icon {
  color: var(--color-primary);
}

.conv-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.conv-title {
  color: var(--text-sidebar);
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-item.active .conv-title {
  color: var(--text-sidebar);
  font-weight: 500;
}

.conv-time {
  color: var(--text-sidebar-muted);
  font-size: 0.75rem;
  opacity: 0.9;
}

.delete-btn {
  opacity: 0;
  border: none;
  background: transparent;
  color: var(--text-sidebar-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity var(--transition-fast), color var(--transition-fast);
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.conversation-item.active .delete-btn {
  color: var(--text-sidebar-muted);
}

.delete-btn:hover {
  color: var(--color-danger);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-sidebar-muted);
}

.empty-state .hint {
  font-size: 0.75rem;
  margin-top: var(--spacing-sm);
}

@media (max-width: 768px) {
  .sidebar {
    width: 60px;
  }

  .logo,
  .conv-info,
  .empty-state,
  .list-header {
    display: none;
  }

  .sidebar-header {
    justify-content: center;
    padding: var(--spacing-sm);
  }

  .conversation-item {
    justify-content: center;
    padding: var(--spacing-sm);
  }
}
</style>
