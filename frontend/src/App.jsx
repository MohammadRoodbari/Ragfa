import React from 'react'
import TopBar from './components/TopBar'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import InputBar from './components/InputBar'
import { useIngest } from './hooks/useIngest'
import { useChat } from './hooks/useChat'

export default function App() {
  const { docs, addFile, addText } = useIngest()
  const { messages, loading, sessionId, streamMode, send, clear, toggleStreamMode } = useChat()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopBar />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar docs={docs} onAddFile={addFile} onAddText={addText} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <ChatArea messages={messages} onSuggest={send} />
          <InputBar
            onSend={send}
            onClear={clear}
            loading={loading}
            sessionId={sessionId}
            streamMode={streamMode}
            onToggleStream={toggleStreamMode}
          />
        </div>
      </div>
    </div>
  )
}
