import React, { useEffect, useRef } from 'react'

const SUGGESTED = [
  { icon: 'ti-list-details',   text: 'Summarize the main topics covered in the uploaded documents' },
  { icon: 'ti-bulb',           text: 'What are the key conclusions or findings?' },
  { icon: 'ti-calendar-event', text: 'List the most important dates and events mentioned' },
  { icon: 'ti-code',           text: 'What technical concepts are explained?' },
]

function SourceChip({ source }) {
  const name  = source.filename ?? source.source ?? 'chunk'
  const score = source.score != null ? Math.round(source.score * 100) : null
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 10px',
      border: '1px solid var(--border2)', borderRadius: 20, fontSize: 11,
      color: 'var(--text2)', background: 'var(--bg2)', marginRight: 5, marginTop: 4,
      transition: 'border-color .15s, color .15s' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text2)' }}>
      <i className="ti ti-file-text" aria-hidden="true" style={{ fontSize: 12, color: 'var(--accent2)' }} />
      <span>{name}</span>
      {score != null && (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#9A3412',
          background: 'rgba(234,88,12,0.1)', padding: '0 5px', borderRadius: 4 }}>
          {score}%
        </span>
      )}
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 5,
      maxWidth: 760, alignSelf: isUser ? 'flex-end' : 'flex-start',
      alignItems: isUser ? 'flex-end' : 'flex-start' }}>

      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text3)',
        padding: '0 4px', display: 'flex', alignItems: 'center', gap: 5 }}>
        {!isUser && (
          <span style={{ width: 15, height: 15, borderRadius: 4,
            background: 'linear-gradient(135deg, #F97316, #EA580C)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 1px 4px rgba(234,88,12,0.3)' }}>
            <i className="ti ti-brain" aria-hidden="true" style={{ fontSize: 9, color: '#fff' }} />
          </span>
        )}
        {isUser ? 'you' : 'ragfa'}
      </div>

      <div style={{
        padding: '11px 15px',
        borderRadius: 14,
        borderBottomRightRadius: isUser ? 4 : 14,
        borderBottomLeftRadius:  isUser ? 14 : 4,
        fontSize: 13.5, lineHeight: 1.7, maxWidth: 640,
        background: isUser
          ? 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)'
          : 'var(--bg2)',
        border: isUser ? 'none' : '1px solid var(--border)',
        color: isUser ? '#fff' : 'var(--text)',
        boxShadow: isUser
          ? '0 2px 12px rgba(234,88,12,0.25)'
          : '0 1px 3px rgba(120,60,20,0.06)',
      }}>
        {isUser
          ? msg.content.split('\n').map((line, i, arr) =>
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>)
          : msg.content
        }
        {msg.streaming && (
          <span style={{ animation: 'blink .7s step-end infinite',
            color: 'var(--accent2)', marginLeft: 2 }}>▌</span>
        )}
      </div>

      {msg.sources?.length > 0 && (
        <div style={{ paddingLeft: 4, display: 'flex', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--text3)', marginRight: 6,
            fontFamily: 'var(--font-mono)' }}>sources:</span>
          {msg.sources.map((s, i) => <SourceChip key={i} source={s} />)}
        </div>
      )}
    </div>
  )
}

export default function ChatArea({ messages, onSuggest }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '28px 28px 12px',
      display: 'flex', flexDirection: 'column', gap: 18,
      background: 'var(--bg)' }}>

      {messages.length === 0 ? (
        <div style={{ margin: 'auto', maxWidth: 500, textAlign: 'center',
          display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px 0' }}>

          <div style={{ width: 68, height: 68, borderRadius: 20,
            background: 'linear-gradient(135deg, rgba(249,115,22,0.15), rgba(234,88,12,0.08))',
            border: '2px solid rgba(234,88,12,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 20, animation: 'orangePulse 3s ease-in-out infinite',
            boxShadow: '0 4px 20px rgba(234,88,12,0.12)' }}>
            <i className="ti ti-message-chatbot" aria-hidden="true"
              style={{ fontSize: 32, color: 'var(--accent)' }} />
          </div>

          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700,
            marginBottom: 10, lineHeight: 1.15, color: 'var(--text)' }}>
            Ask your documents
            <span style={{ display: 'block', color: 'var(--accent)' }}>anything</span>
          </h2>

          <p style={{ color: 'var(--text2)', fontSize: 13.5, lineHeight: 1.7, maxWidth: 380 }}>
            Upload PDFs or DOCX files on the left, then ask questions below.
            Chunks are indexed in Elasticsearch and answered by the LLM with full source attribution.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8,
            marginTop: 24, width: '100%' }}>
            {SUGGESTED.map(({ icon, text }) => (
              <button key={text} onClick={() => onSuggest(text)}
                style={{ padding: '11px 13px', border: '1px solid var(--border)',
                  borderRadius: 'var(--r)', fontSize: 12, color: 'var(--text2)',
                  cursor: 'pointer', background: 'var(--bg2)',
                  fontFamily: 'var(--font-body)', transition: 'all .15s',
                  textAlign: 'left', display: 'flex', alignItems: 'flex-start',
                  gap: 8, lineHeight: 1.4,
                  boxShadow: '0 1px 3px rgba(120,60,20,0.05)' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = '#9A3412'; e.currentTarget.style.background = 'var(--accent-dim)'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(234,88,12,0.1)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text2)'; e.currentTarget.style.background = 'var(--bg2)'; e.currentTarget.style.boxShadow = '0 1px 3px rgba(120,60,20,0.05)' }}>
                <i className={`ti ${icon}`} aria-hidden="true"
                  style={{ fontSize: 16, color: 'var(--accent)', flexShrink: 0, marginTop: 1 }} />
                {text}
              </button>
            ))}
          </div>
        </div>
      ) : (
        messages.map(msg => <Message key={msg.id} msg={msg} />)
      )}

      <div ref={bottomRef} />
    </div>
  )
}