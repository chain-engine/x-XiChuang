import { ref, readonly, computed } from 'vue'
import { sendMessage, sendMessageStream } from '@/services/api.js'

/**
 * 聊天逻辑组合式函数
 * @param {import('vue').Ref<string>} sessionId - 当前选中的会话 id
 * @param {import('vue').Ref<string>} [provider]
 * @param {{ onReplyForOtherSession?: (p: { sessionId: string, answer?: string, summary?: string, error?: string }) => void }} [callbacks] - 当请求发出后用户切换了会话时，用此回调把结果写回「发起请求」的会话
 */
export function useChat(sessionId, provider = ref('tongyi'), callbacks = {}) {
  const { onReplyForOtherSession } = callbacks
  const messages = ref([])
  /** 各会话在途请求数（切换会话后，非当前会话的请求不应显示「正在思考」） */
  const inFlightBySession = ref(new Map())
  const error = ref(null)
  const summary = ref('')

  function changeInFlight(sessionIdKey, delta) {
    const m = new Map(inFlightBySession.value)
    const next = (m.get(sessionIdKey) || 0) + delta
    if (next <= 0) m.delete(sessionIdKey)
    else m.set(sessionIdKey, next)
    inFlightBySession.value = m
  }

  /** 仅当前选中会话有待完成请求时为 true（用于「正在思考」与禁用输入） */
  const thinkingForCurrentSession = computed(() => {
    const sid = sessionId.value
    return (inFlightBySession.value.get(sid) || 0) > 0
  })

  /**
   * 加载历史消息
   * @param {Array} historyMessages - 历史消息数组
   */
  function loadHistory(historyMessages) {
    if (historyMessages && historyMessages.length > 0) {
      messages.value = [...historyMessages]
    } else {
      messages.value = []
    }
    // 切换会话时避免沿用上一会话的摘要/错误态
    summary.value = ''
    error.value = null
  }

  /**
   * 发送消息（支持流式返回）
   * @param {Object} options - 发送选项
   * @param {string} options.text - 文本消息
   * @param {File|Blob} [options.file] - 上传的文件
   * @param {string} [options.mediaType] - 媒体类型
   */
  async function send({ text, file, mediaType }) {
    const requestSessionId = sessionId.value

    // 添加用户消息
    let displayContent = text
    if (file && !text) {
      displayContent = '[文件消息]'
    } else if (file && text) {
      displayContent = text
    }

    if (displayContent) {
      messages.value.push({ role: 'user', content: displayContent })
    }

    changeInFlight(requestSessionId, 1)
    error.value = null

    try {
      // 如果有文件，使用非流式上传接口
      if (file) {
        const formData = new FormData()
        formData.append('session_id', requestSessionId)
        formData.append('query', text || '')
        formData.append('use_direct_multimodal', 'true')
        formData.append('file', file, file.name || 'recording.webm')
        formData.append('media_type', mediaType || 'auto')
        if (provider.value) {
          formData.append('provider', provider.value)
        }

        const response = await sendMessage(formData)

        if (sessionId.value !== requestSessionId) {
          onReplyForOtherSession?.({
            sessionId: requestSessionId,
            answer: response.answer,
            summary: response.summary || undefined
          })
        } else {
          messages.value.push({ role: 'assistant', content: response.answer })
          if (response.summary) {
            summary.value = response.summary
          }
        }
        return response
      }

      // 无文件，使用流式接口
      // 先添加一个空的 assistant 消息用于流式更新（标记为 streaming）
      const assistantIndex = messages.value.length
      messages.value.push({ role: 'assistant', content: '', streaming: true })

      console.log('Starting stream with provider:', provider.value)

      const fullAnswer = await sendMessageStream(
        {
          session_id: requestSessionId,
          query: text || '',
          provider: provider.value
        },
        {
          onChunk: (chunk) => {
            // 流式更新当前会话的消息
            if (sessionId.value === requestSessionId) {
              messages.value[assistantIndex].content += chunk
            }
          },
          onDone: (answer) => {
            // 流式完成，移除 streaming 标记
            if (sessionId.value === requestSessionId && messages.value[assistantIndex]) {
              messages.value[assistantIndex].streaming = false
            }
            if (sessionId.value !== requestSessionId) {
              onReplyForOtherSession?.({
                sessionId: requestSessionId,
                answer: answer
              })
            }
          },
          onError: (err) => {
            console.error('Stream error:', err)
            if (sessionId.value === requestSessionId) {
              messages.value[assistantIndex].streaming = false
              messages.value[assistantIndex].content = `❌ ${err}`
            }
          }
        }
      )

      return { answer: fullAnswer, session_id: requestSessionId }

    } catch (err) {
      console.error('Chat error:', err)
      error.value = err.message || '请求失败，请重试'
      const errText = `❌ ${error.value}`
      if (sessionId.value !== requestSessionId) {
        onReplyForOtherSession?.({
          sessionId: requestSessionId,
          error: errText
        })
      } else {
        // 更新最后一条消息为错误
        const lastMsg = messages.value[messages.value.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = errText
        } else {
          messages.value.push({ role: 'assistant', content: errText })
        }
      }
      throw err
    } finally {
      changeInFlight(requestSessionId, -1)
    }
  }

  /**
   * 清空所有消息
   */
  function clearMessages() {
    messages.value = []
    summary.value = ''
    error.value = null
  }

  return {
    messages: readonly(messages),
    /** @deprecated 请用 thinkingForCurrentSession；保留兼容：任意会话有在途请求时为 true */
    loading: computed(() => inFlightBySession.value.size > 0),
    thinkingForCurrentSession,
    error: readonly(error),
    summary: readonly(summary),
    send,
    clearMessages,
    loadHistory
  }
}
