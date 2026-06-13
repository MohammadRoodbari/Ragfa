import { useState, useRef, useCallback } from 'react'
import { ingestFile, ingestText, fetchJobStatus } from '../lib/api'

const POLL_MS = 1500
const TERMINAL = new Set(['SUCCESS', 'FAILURE'])

/**
 * useIngest — manages the list of ingested documents.
 *
 * Each doc: { id, name, ext, state, progress, taskId, error }
 */
export function useIngest() {
  const [docs, setDocs] = useState([])
  const timers = useRef({})

  const updateDoc = useCallback((id, patch) => {
    setDocs(prev => prev.map(d => (d.id === id ? { ...d, ...patch } : d)))
  }, [])

  const startPolling = useCallback(
    (docId, taskId) => {
      if (timers.current[docId]) return
      timers.current[docId] = setInterval(async () => {
        try {
          const data = await fetchJobStatus(taskId)
          if (!data) {
            clearInterval(timers.current[docId])
            delete timers.current[docId]
            return
          }
          const patch = { state: data.state, progress: data.progress ?? 0 }
          if (data.state === 'FAILURE') {
            patch.error = (data.errors ?? []).join(', ') || data.error || 'Unknown error'
          }
          updateDoc(docId, patch)
          if (TERMINAL.has(data.state)) {
            clearInterval(timers.current[docId])
            delete timers.current[docId]
          }
        } catch {
          // transient network error — keep polling
        }
      }, POLL_MS)
    },
    [updateDoc]
  )

  const addFile = useCallback(
    async file => {
      const ext = file.name.split('.').pop().toLowerCase()
      if (!['pdf', 'docx'].includes(ext)) {
        throw new Error('Only PDF and DOCX files are supported.')
      }
      const docId = Date.now()
      const doc = { id: docId, name: file.name, ext, state: 'PENDING', progress: 0, taskId: null, error: null }
      setDocs(prev => [doc, ...prev])
      try {
        const { task_id } = await ingestFile(file)
        updateDoc(docId, { taskId: task_id, state: 'STARTED' })
        startPolling(docId, task_id)
        return task_id
      } catch (err) {
        updateDoc(docId, { state: 'FAILURE', error: err.message })
        throw err
      }
    },
    [updateDoc, startPolling]
  )

  const addText = useCallback(
    async ({ text, source }) => {
      const docId = Date.now()
      const name = source || `text-${docId}`
      const doc = { id: docId, name, ext: 'txt', state: 'PENDING', progress: 0, taskId: null, error: null }
      setDocs(prev => [doc, ...prev])
      try {
        const { task_id } = await ingestText({ text, source: name })
        updateDoc(docId, { taskId: task_id, state: 'STARTED' })
        startPolling(docId, task_id)
        return task_id
      } catch (err) {
        updateDoc(docId, { state: 'FAILURE', error: err.message })
        throw err
      }
    },
    [updateDoc, startPolling]
  )

  return { docs, addFile, addText }
}
