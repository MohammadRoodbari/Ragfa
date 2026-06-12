import { useState, useRef, useCallback } from 'react'
import { queryBlocking, queryStream } from '../lib/api'

/**
 * Generate a compact random session ID: "sess_<10 hex chars>"
 * Enough entropy for UI purposes; backend can override with its own ID if desired.
 */
function newSessionId() {
  const hex = Array.from(crypto.getRandomValues(new Uint8Array(5)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
  return `sess_${hex}`
}

export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => newSessionId())
  const [streamMode, setStreamMode] = useState(false)
  const abortRef = useRef(null)

  const addMessage = useCallback((msg) => {
    const full = { id: Date.now() + Math.random(), sources: [], ...msg }
    setMessages(prev => [...prev, full])
    return full.id
  }, [])

  const patchMessage = useCallback((id, patch) => {
    setMessages(prev => prev.map(m => (m.id === id ? { ...m, ...patch } : m)))
  }, [])

  const send = useCallback(
    async (question) => {
      if (!question.trim() || loading) return
      addMessage({ role: 'user', content: question })
      setLoading(true)

      if (streamMode) {
        const assistantId = addMessage({ role: 'assistant', content: '', streaming: true })
        try {
          const res = await queryStream({ question, sessionId })
          const sid = res.headers.get('X-Session-Id')
          if (sid) setSessionId(sid)

          const reader = res.body.getReader()
          const dec = new TextDecoder()
          let buf = ''
          let text = ''

          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buf += dec.decode(value, { stream: true })
            const lines = buf.split('\n')
            buf = lines.pop()
            for (const line of lines) {
              if (!line.startsWith('data:')) continue
              const tok = line.slice(5).trim()
              if (tok === '[DONE]' || tok === '[ERROR]') break
              text += tok
              patchMessage(assistantId, { content: text })
            }
          }
          patchMessage(assistantId, { streaming: false })
        } catch (err) {
          patchMessage(assistantId, { content: `Error: ${err.message}`, streaming: false, error: true })
        }
      } else {
        const assistantId = addMessage({ role: 'assistant', content: '', streaming: true })
        try {
          const data = await queryBlocking({ question, sessionId })
          if (data.session_id) setSessionId(data.session_id)
          patchMessage(assistantId, {
            content: data.answer ?? '',
            sources: data.sources ?? [],
            streaming: false,
          })
        } catch (err) {
          patchMessage(assistantId, { content: `Error: ${err.message}`, streaming: false, error: true })
        }
      }

      setLoading(false)
    },
    [loading, streamMode, sessionId, addMessage, patchMessage]
  )

  const clear = useCallback(() => {
    setMessages([])
    setSessionId(newSessionId())
  }, [])

  const toggleStreamMode = useCallback(() => setStreamMode(v => !v), [])

  return { messages, loading, sessionId, streamMode, send, clear, toggleStreamMode }
}