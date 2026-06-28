const BASE_URL = '/api/chat'
const CONVERSATIONS_URL = '/api/conversations'

/**
 * 发送带文件的聊天消息
 * @param {FormData} formData - 表单数据，包含 session_id, query, file, media_type 等
 * @returns {Promise<{answer: string, session_id: string, summary?: string}>}
 */
export async function sendMessage(formData) {
  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 发送纯文本消息
 * @param {Object} params - 请求参数
 * @param {string} params.session_id - 会话ID
 * @param {string} params.query - 用户问题
 * @param {string} [params.provider] - 模型提供商
 * @returns {Promise<{answer: string, session_id: string, summary?: string}>}
 */
export async function sendTextMessage({ session_id, query, provider }) {
  const res = await fetch(`${BASE_URL}/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ session_id, query, provider })
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 流式发送聊天消息
 * @param {Object} params - 请求参数
 * @param {string} params.session_id - 会话ID
 * @param {string} params.query - 用户问题
 * @param {string} [params.provider] - 模型提供商
 * @param {Function} onChunk - 每次收到片段时的回调 (chunk: string) => void
 * @param {Function} [onDone] - 完成时的回调 (fullAnswer: string) => void
 * @param {Function} [onError] - 错误时的回调 (error: string) => void
 * @returns {Promise<string>} 完整的回答
 */
export async function sendMessageStream({ session_id, query, provider }, { onChunk, onDone, onError }) {
  const res = await fetch(`${BASE_URL}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ session_id, query, provider })
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let fullAnswer = ''
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.content) {
            fullAnswer += data.content
            onChunk?.(data.content)
          }
          if (data.done) {
            onDone?.(data.full_answer || fullAnswer)
          }
          if (data.error) {
            onError?.(data.error)
            throw new Error(data.error)
          }
        } catch (e) {
          if (e.message !== data?.error) {
            console.error('Parse SSE error:', e)
          }
        }
      }
    }
  }

  return fullAnswer
}

/**
 * 获取可用的模型提供商列表
 * @returns {Promise<{providers: Array<{name: string, display_name: string, available: boolean}>, default: string}>}
 */
export async function getProviders() {
  const res = await fetch(`${BASE_URL}/providers`)

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

// ============ 会话相关 API ============

/**
 * 获取所有会话列表
 * @returns {Promise<Array<{id: string, title: string, summary?: string, model_provider: string, created_at?: string, updated_at?: string}>>}
 */
export async function getConversations() {
  const res = await fetch(CONVERSATIONS_URL)

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 创建新会话
 * @param {Object} data - 会话数据
 * @param {string} [data.id] - 会话ID
 * @param {string} [data.title] - 会话标题
 * @param {string} [data.model_provider] - 模型提供商
 * @returns {Promise<{id: string, title: string, model_provider: string}>}
 */
export async function createConversation(data = {}) {
  const res = await fetch(CONVERSATIONS_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 获取会话详情（包含消息）
 * @param {string} conversationId - 会话ID
 * @returns {Promise<{id: string, title: string, messages: Array<{role: string, content: string}>}>}
 */
export async function getConversation(conversationId) {
  const res = await fetch(`${CONVERSATIONS_URL}/${conversationId}`)

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 更新会话信息
 * @param {string} conversationId - 会话ID
 * @param {Object} data - 更新数据
 * @returns {Promise<{id: string, title: string}>}
 */
export async function updateConversation(conversationId, data) {
  const res = await fetch(`${CONVERSATIONS_URL}/${conversationId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 删除会话
 * @param {string} conversationId - 会话ID
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function deleteConversation(conversationId) {
  const res = await fetch(`${CONVERSATIONS_URL}/${conversationId}`, {
    method: 'DELETE'
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}

/**
 * 保存会话消息
 * @param {string} conversationId - 会话ID
 * @param {Array<{role: string, content: string}>} messages - 消息列表
 * @returns {Promise<{id: string, title: string, messages: Array}>}
 */
export async function saveMessages(conversationId, messages) {
  const res = await fetch(`${CONVERSATIONS_URL}/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ messages })
  })

  if (!res.ok) {
    const error = await res.text()
    throw new Error(error || 'Request failed')
  }

  return res.json()
}
