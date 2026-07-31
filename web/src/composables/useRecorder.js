import { ref, readonly } from 'vue'

/**
 * Voice recording composable using MediaRecorder API
 *
 * 浏览器格式兼容策略：
 * 1. 优先尝试 audio/webm;codecs=opus（Chrome / Firefox / Edge）
 * 2. 不支持则尝试 audio/mp4（Safari 14.1+）
 * 3. 再不支持则尝试 audio/ogg
 * 4. 最后兜底默认（由浏览器自动选择）
 *
 * 输出 Blob 的 MIME type 会随所选 mime 一致，文件后缀也按相同规则命名。
 */

const PREFERRED_MIMES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
  'audio/ogg;codecs=opus',
  'audio/ogg',
]

function pickSupportedMime() {
  if (typeof MediaRecorder === 'undefined') return ''
  for (const m of PREFERRED_MIMES) {
    try {
      if (MediaRecorder.isTypeSupported(m)) return m
    } catch (_e) {
      // ignore
    }
  }
  return ''
}

function extFromMime(mime) {
  if (!mime) return 'webm'
  if (mime.includes('webm')) return 'webm'
  if (mime.includes('mp4')) return 'm4a'
  if (mime.includes('ogg')) return 'ogg'
  if (mime.includes('wav')) return 'wav'
  return 'webm'
}

/**
 * Voice recording composable
 */
export function useRecorder() {
  const recording = ref(false)
  const error = ref(null)
  const mimeType = ref('')

  let mediaRecorder = null
  let audioChunks = []

  /**
   * Check if recording is supported
   */
  function isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && typeof MediaRecorder !== 'undefined')
  }

  /**
   * Start recording
   */
  async function startRecording() {
    if (!isSupported()) {
      error.value = '当前浏览器不支持录音功能'
      throw new Error(error.value)
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chosen = pickSupportedMime()
      mimeType.value = chosen

      mediaRecorder = chosen ? new MediaRecorder(stream, { mimeType: chosen }) : new MediaRecorder(stream)
      audioChunks = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunks.push(e.data)
        }
      }

      recording.value = true
      mediaRecorder.start()

      return new Promise((resolve) => {
        mediaRecorder.onstop = () => {
          const finalMime = mediaRecorder.mimeType || chosen || 'audio/webm'
          const blob = new Blob(audioChunks, { type: finalMime })
          blob.name = `recording.${extFromMime(finalMime)}`
          recording.value = false

          // Stop all tracks to release microphone
          stream.getTracks().forEach(track => track.stop())

          resolve(blob)
        }
      })
    } catch (err) {
      error.value = '无法访问麦克风，请检查权限设置'
      recording.value = false
      throw err
    }
  }

  /**
   * Stop recording and get the audio blob
   * @returns {Promise<Blob>}
   */
  function stopRecording() {
    return new Promise((resolve, reject) => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        reject(new Error('录音未开始'))
        return
      }

      mediaRecorder.onstop = () => {
        const finalMime = mediaRecorder.mimeType || mimeType.value || 'audio/webm'
        const blob = new Blob(audioChunks, { type: finalMime })
        blob.name = `recording.${extFromMime(finalMime)}`
        recording.value = false

        // Stop all tracks
        if (mediaRecorder.stream) {
          mediaRecorder.stream.getTracks().forEach(track => track.stop())
        }

        resolve(blob)
      }

      mediaRecorder.onerror = (err) => {
        error.value = '录音过程中发生错误'
        recording.value = false
        reject(err)
      }

      mediaRecorder.stop()
    })
  }

  /**
   * Toggle recording state
   * @returns {Promise<Blob|null>} Returns blob when stopping, null when starting
   */
  async function toggleRecording() {
    if (recording.value) {
      return stopRecording()
    } else {
      await startRecording()
      return null
    }
  }

  return {
    recording: readonly(recording),
    error: readonly(error),
    mimeType: readonly(mimeType),
    isSupported,
    startRecording,
    stopRecording,
    toggleRecording
  }
}