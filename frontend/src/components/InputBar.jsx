import React, { useRef } from 'react'

export default function InputBar({ onSend, onClear, loading, sessionId, streamMode, onToggleStream }) {
  const textareaRef = useRef(null)

  const autoResize = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const submit = () => {
    const val = textareaRef.current?.value?.trim()
    if (!val || loading) return
    textareaRef.current.value = ''
    textareaRef.current.style.height = 'auto'
    onSend(val)
  }

  return (
    <div style={{ padding: '14px 24px 16px', borderTop: '1px solid var(--border)',
      flexShrink: 0, background: 'var(--bg2)' }}>

      {/* Input wrapper */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10,
        background: 'var(--bg)', border: '1.5px solid var(--border2)',
        borderRadius: 'var(--r3)', padding: '10px 12px 10px 16px',
        transition: 'border-color .2s, box-shadow .2s',
        boxShadow: '0 1px 4px rgba(120,60,20,0.06)' }}
        onFocusCapture={e => {
          e.currentTarget.style.borderColor = 'var(--accent)'
          e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-glow)'
        }}
        onBlurCapture={e => {
          e.currentTarget.style.borderColor = 'var(--border2)'
          e.currentTarget.style.boxShadow = '0 1px 4px rgba(120,60,20,0.06)'
        }}>

        <textarea ref={textareaRef} rows={1}
          placeholder="Ask a question about your documents…"
          onKeyDown={handleKey} onInput={autoResize} disabled={loading}
          style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--text)', fontFamily: 'var(--font-body)', fontSize: 14,
            resize: 'none', maxHeight: 120, lineHeight: 1.6,
            cursor: loading ? 'not-allowed' : 'text' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0 }}>
          {/* Clear */}
          <button onClick={onClear} title="Clear conversation"
            style={{ width: 34, height: 34, borderRadius: 'var(--r)',
              border: '1px solid var(--border)', background: 'transparent',
              color: 'var(--text3)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, transition: 'all .15s' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--danger)'; e.currentTarget.style.color = 'var(--danger)'; e.currentTarget.style.background = 'rgba(220,38,38,0.06)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text3)'; e.currentTarget.style.background = 'transparent' }}>
            <i className="ti ti-eraser" aria-hidden="true" />
          </button>

          {/* Send */}
          <button onClick={submit} disabled={loading} title="Send (Enter)"
            style={{ width: 34, height: 34, borderRadius: 'var(--r)', border: 'none',
              background: loading ? 'var(--border)' : 'linear-gradient(135deg, #F97316, #EA580C)',
              color: loading ? 'var(--text3)' : '#fff',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, transition: 'all .15s',
              boxShadow: loading ? 'none' : '0 2px 8px rgba(234,88,12,0.35)' }}
            onMouseEnter={e => { if (!loading) e.currentTarget.style.opacity = '.85' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}>
            <i className={`ti ${loading ? 'ti-loader spinning' : 'ti-send'}`} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Meta row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 9 }}>

        {/* Session badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 9px',
          background: 'var(--bg3)', borderRadius: 20, border: '1px solid var(--border)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
            background: 'var(--accent)', boxShadow: '0 0 0 2px rgba(234,88,12,0.2)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text3)' }}>
            {sessionId}
          </span>
        </div>

        {/* Stream toggle */}
        <div onClick={onToggleStream} title="Toggle streaming mode"
          style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
            userSelect: 'none', padding: '3px 9px', borderRadius: 20,
            border: '1px solid var(--border)',
            background: streamMode ? 'var(--accent-dim)' : 'transparent',
            transition: 'all .2s' }}>
          <div style={{ width: 26, height: 14, borderRadius: 7, position: 'relative',
            background: streamMode ? 'var(--accent)' : 'var(--border2)',
            transition: 'background .2s', flexShrink: 0,
            boxShadow: streamMode ? '0 1px 4px rgba(234,88,12,0.3)' : 'none' }}>
            <div style={{ position: 'absolute', width: 10, height: 10, borderRadius: '50%',
              background: '#fff', top: 2, left: streamMode ? 14 : 2, transition: 'left .2s' }} />
          </div>
          <span style={{ fontSize: 11,
            color: streamMode ? '#9A3412' : 'var(--text3)', fontWeight: streamMode ? 500 : 400 }}>
            stream
          </span>
        </div>

        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>
          ↵ send · shift+↵ newline
        </span>
      </div>
    </div>
  )
}