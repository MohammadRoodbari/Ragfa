import React, { useState, useRef, useEffect } from 'react'
import { useHealth } from '../hooks/useHealth'

function statusColor(s) {
  if (s === 'ok')       return 'var(--success)'
  if (s === 'degraded') return 'var(--warn)'
  if (s === 'offline')  return 'var(--danger)'
  return 'var(--text3)'
}

function DepRow({ label, icon, ok, last }) {
  const color = ok === null ? 'var(--warn)' : ok ? 'var(--success)' : 'var(--danger)'
  const bg    = ok === null ? 'rgba(217,119,6,0.1)' : ok ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '7px 0', borderBottom: last ? 'none' : '1px solid var(--border)' }}>
      <span style={{ fontSize: 12, color: 'var(--text2)', display: 'flex', alignItems: 'center', gap: 7 }}>
        <i className={`ti ${icon}`} aria-hidden="true"
          style={{ color: ok ? 'var(--accent2)' : 'var(--text3)', fontSize: 14 }} />
        {label}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color, background: bg,
        padding: '2px 8px', borderRadius: 20 }}>
        {ok === null ? 'checking' : ok ? 'online' : 'offline'}
      </span>
    </div>
  )
}

export default function TopBar() {
  const { status, elasticsearch, redis, loading, check } = useHealth()
  const [open, setOpen] = useState(false)
  const panelRef = useRef(null)

  useEffect(() => { check() }, []) // eslint-disable-line

  useEffect(() => {
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleToggle = () => { setOpen(v => !v); if (!open) check() }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px', height: 56, flexShrink: 0, position: 'relative', zIndex: 10,
      background: 'var(--bg2)', borderBottom: '1px solid var(--border)',
      boxShadow: '0 1px 3px rgba(234,88,12,0.06)' }}>

      {/* Logo */}
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 19,
        letterSpacing: '-0.5px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: 9,
          background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(234,88,12,0.35)',
          animation: 'orangePulse 3s ease-in-out infinite' }}>
          <i className="ti ti-brain" aria-hidden="true" style={{ color: '#fff', fontSize: 17 }} />
        </div>
        <span style={{ color: 'var(--accent)' }}>RAG</span>
        <span style={{ color: 'var(--text)', marginLeft: -5 }}>fa</span>
      </div>

      {/* Right */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
          padding: '3px 9px', background: 'var(--bg3)', borderRadius: 20,
          border: '1px solid var(--border)' }}>
          v0.1.0
        </span>

        <div ref={panelRef} style={{ position: 'relative' }}>
          <button onClick={handleToggle}
            style={{ display: 'flex', alignItems: 'center', gap: 6,
              fontFamily: 'var(--font-mono)', fontSize: 11, padding: '5px 12px',
              borderRadius: 20, cursor: 'pointer', transition: 'all .15s',
              border: `1px solid ${open ? 'var(--accent)' : 'var(--border2)'}`,
              background: open ? 'var(--accent-dim)' : 'var(--bg3)',
              color: open ? 'var(--accent)' : 'var(--text2)' }}
            onMouseEnter={e => { if (!open) { e.currentTarget.style.borderColor = 'var(--accent2)'; e.currentTarget.style.color = 'var(--accent2)' } }}
            onMouseLeave={e => { if (!open) { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text2)' } }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', display: 'inline-block',
              background: statusColor(status),
              boxShadow: status === 'ok' ? '0 0 0 3px rgba(22,163,74,0.2)' : 'none',
              transition: 'background .3s' }} />
            {loading ? 'checking…' : status}
            <i className={`ti ti-chevron-${open ? 'up' : 'down'}`} aria-hidden="true"
              style={{ fontSize: 11 }} />
          </button>

          {open && (
            <div className="fade-in"
              style={{ position: 'absolute', top: 'calc(100% + 10px)', right: 0,
                background: 'var(--bg2)', border: '1px solid var(--border2)',
                borderRadius: 'var(--r2)', padding: '14px 16px', width: 232,
                boxShadow: '0 8px 24px rgba(120,60,20,0.12)' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)',
                marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
                fontFamily: 'var(--font-display)', letterSpacing: '.5px', textTransform: 'uppercase' }}>
                <i className="ti ti-heartbeat" aria-hidden="true" style={{ fontSize: 13 }} />
                System health
              </div>
              <DepRow label="Elasticsearch" icon="ti-database" ok={loading ? null : elasticsearch} />
              <DepRow label="Redis"         icon="ti-stack"    ok={loading ? null : redis} />
              <DepRow label="API"           icon="ti-activity" ok={loading ? null : status !== 'offline'} last />
              <button onClick={check}
                style={{ width: '100%', marginTop: 12, padding: '7px', borderRadius: 'var(--r)',
                  border: '1px solid var(--border2)', background: 'var(--bg3)',
                  color: 'var(--text2)', fontFamily: 'var(--font-body)', fontSize: 12,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  gap: 6, transition: 'all .15s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.background = 'var(--accent-dim)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text2)'; e.currentTarget.style.background = 'var(--bg3)' }}>
                <i className={`ti ti-refresh ${loading ? 'spinning' : ''}`} aria-hidden="true" />
                Re-check now
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}