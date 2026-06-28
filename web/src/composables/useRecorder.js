import { ref, readonly } from 'vue'

/**
 * Voice recording composable using MediaRecorder API
 */
export function useRecorder() {
  const recording = ref(false)
  const error = ref(null)

  let mediaRecorder = null
  let audioChunks = []

  /**
   * Check if recording is supported
   */
  function isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
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
      mediaRecorder = new MediaRecorder(stream)
      audioChunks = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.push(e.data)
        }
      }

      recording.value = true
      mediaRecorder.start()

      return new Promise((resolve) => {
        mediaRecorder.onstop = () => {
          const blob = new Blob(audioChunks, { type: 'audio/webm' })
          blob.name = 'recording.webm'
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
        const blob = new Blob(audioChunks, { type: 'audio/webm' })
        blob.name = 'recording.webm'
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
    isSupported,
    startRecording,
    stopRecording,
    toggleRecording
  }
}
