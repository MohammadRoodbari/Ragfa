import React, { useRef, useState } from 'react'

const EXT_META = {
  pdf:  { icon: 'ti-file-type-pdf',  bg: 'rgba(234,88,12,0.10)',  color: '#EA580C', border: 'rgba(234,88,12,0.25)' },
  docx: { icon: 'ti-file-type-docx', bg: 'rgba(37,99,235,0.10)',  color: '#2563EB', border: 'rgba(37,99,235,0.25)' },
  txt:  { icon: 'ti-file-text',      bg: 'rgba(22,163,74,0.10)',  color: '#16A34A', border: 'rgba(22,163,74,0.25)' },
}

const STATE_PILL = {
  PENDING: { bg: 'rgba(217,119,6,0.12)',  color: '#92400E', label: 'pending' },
  STARTED: { bg: 'rgba(234,88,12,0.12)',  color: '#9A3412', label: 'indexing' },
  SUCCESS: { bg: 'rgba(22,163,74,0.12)',  color: '#14532D', label: 'ready' },
  FAILURE: { bg: 'rgba(220,38,38,0.12)',  color: '#7F1D1D', label: 'failed' },
}

function DocItem({ doc }) {
  const meta = EXT_META[doc.ext] ?? EXT_META.txt
  const pill = STATE_PILL[doc.state] ?? STATE_PILL.PENDING
  const showBar = doc.state === 'PENDING' || doc.state === 'STARTED'

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '9px 10px',
      borderRadius: 'var(--r)', marginBottom: 3, border: '1px solid transparent',
      transition: 'background .15s, border-color .15s', cursor: 'default' }}
      onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.borderColor = 'var(--border)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent' }}>
      <div style={{ width: 34, height: 34, borderRadius: 'var(--r)', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: meta.bg, color: meta.color, fontSize: 17,
        border: `1px solid ${meta.border}` }}>
        <i className={`ti ${meta.icon}`} aria-hidden="true" />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
          title={doc.name}>{doc.name}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, padding: '1px 7px',
            borderRadius: 20, background: pill.bg, color: pill.color, fontWeight: 500 }}>
            {pill.label}
          </span>
          {doc.state === 'STARTED' && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text3)' }}>
              {doc.progress}%
            </span>
          )}
        </div>
        {showBar && (
          <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginTop: 6, overflow: 'hidden' }}>
            <div style={{ height: '100%', borderRadius: 2, width: `${doc.progress}%`,
              transition: 'width .4s',
              background: 'linear-gradient(90deg, #F97316, #EA580C)' }} />
          </div>
        )}
        {doc.error && (
          <div style={{ fontSize: 10, color: 'var(--danger)', marginTop: 3,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            title={doc.error}>{doc.error}</div>
        )}
      </div>
    </div>
  )
}

function TextIngestModal({ onClose, onSubmit }) {
  const [source, setSource] = useState('')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const handleSubmit = async () => {
    if (!text.trim()) { setErr('Text content is required.'); return }
    setBusy(true); setErr('')
    try {
      await onSubmit({ text: text.trim(), source: source.trim() || undefined })
      onClose()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  const inputStyle = {
    width: '100%', background: 'var(--bg3)', border: '1px solid var(--border2)',
    borderRadius: 'var(--r)', padding: '8px 10px', color: 'var(--text)',
    fontFamily: 'var(--font-body)', fontSize: 13, outline: 'none', transition: 'border-color .15s'
  }

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(100,50,20,0.3)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div className="fade-in"
        style={{ background: 'var(--bg2)', border: '1px solid var(--border2)',
          borderRadius: 'var(--r3)', padding: 26, width: 460, maxWidth: '90vw',
          boxShadow: '0 16px 48px rgba(120,60,20,0.15)' }}>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 22 }}>
          <div style={{ width: 38, height: 38, borderRadius: 'var(--r)',
            background: 'var(--accent-dim)', border: '1px solid rgba(234,88,12,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--accent)', fontSize: 20 }}>
            <i className="ti ti-file-text" aria-hidden="true" />
          </div>
          <div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 600,
              color: 'var(--text)' }}>Ingest raw text</h3>
            <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>
              Text will be chunked and indexed in Elasticsearch
            </p>
          </div>
        </div>

        <label style={{ fontSize: 12, color: 'var(--text2)', display: 'block', marginBottom: 6, fontWeight: 500 }}>
          Source name <span style={{ color: 'var(--text3)', fontWeight: 400 }}>(optional)</span>
        </label>
        <input type="text" value={source} onChange={e => setSource(e.target.value)}
          placeholder="e.g. meeting-notes-jun-2025" style={{ ...inputStyle, marginBottom: 14 }}
          onFocus={e => e.target.style.borderColor = 'var(--accent)'}
          onBlur={e => e.target.style.borderColor = 'var(--border2)'} />

        <label style={{ fontSize: 12, color: 'var(--text2)', display: 'block', marginBottom: 6, fontWeight: 500 }}>
          Text content
        </label>
        <textarea value={text} onChange={e => { setText(e.target.value); setErr('') }}
          placeholder="Paste your text here…" rows={6}
          style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5,
            borderColor: err ? 'var(--danger)' : 'var(--border2)' }}
          onFocus={e => { if (!err) e.target.style.borderColor = 'var(--accent)' }}
          onBlur={e => { if (!err) e.target.style.borderColor = 'var(--border2)' }} />

        {err && (
          <div style={{ fontSize: 12, color: 'var(--danger)', marginTop: 6,
            display: 'flex', alignItems: 'center', gap: 5 }}>
            <i className="ti ti-alert-circle" aria-hidden="true" style={{ fontSize: 13 }} />
            {err}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
          <button onClick={onClose}
            style={{ padding: '8px 16px', border: '1px solid var(--border2)', borderRadius: 'var(--r)',
              background: 'transparent', color: 'var(--text2)', fontFamily: 'var(--font-body)',
              fontSize: 13, cursor: 'pointer', transition: 'all .15s' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text2)' }}>
            Cancel
          </button>
          <button onClick={handleSubmit} disabled={busy}
            style={{ padding: '8px 20px', border: 'none', borderRadius: 'var(--r)',
              background: busy ? 'var(--border)' : 'linear-gradient(135deg, #F97316, #EA580C)',
              color: busy ? 'var(--text3)' : '#fff',
              fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500,
              cursor: busy ? 'not-allowed' : 'pointer', transition: 'opacity .15s',
              display: 'flex', alignItems: 'center', gap: 6,
              boxShadow: busy ? 'none' : '0 2px 8px rgba(234,88,12,0.3)' }}>
            {busy && <i className="ti ti-loader spinning" aria-hidden="true" />}
            {busy ? 'Ingesting…' : 'Ingest'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Sidebar({ docs, onAddFile, onAddText }) {
  const fileRef = useRef(null)
  const [drag, setDrag] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [uploadErr, setUploadErr] = useState('')

  const handleFile = async (file) => {
    setUploadErr('')
    try { await onAddFile(file) }
    catch (e) { setUploadErr(e.message) }
  }

  const handleDrop = (e) => {
    e.preventDefault(); setDrag(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const successCount = docs.filter(d => d.state === 'SUCCESS').length

  return (
    <div style={{ width: 288, flexShrink: 0,
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      background: 'var(--sidebar-bg)' }}>

      {/* Header */}
      <div style={{ padding: '16px 16px 14px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 11, fontWeight: 700,
            color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Documents
          </span>
          {docs.length > 0 && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#92400E',
              padding: '2px 8px', background: 'rgba(234,88,12,0.08)',
              borderRadius: 20, border: '1px solid rgba(234,88,12,0.2)' }}>
              {successCount}/{docs.length} ready
            </span>
          )}
        </div>

        {/* Drop zone */}
        <div onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={handleDrop}
          style={{ border: `2px dashed ${drag ? 'var(--accent)' : 'var(--border2)'}`,
            borderRadius: 'var(--r2)', padding: '18px 12px', textAlign: 'center',
            cursor: 'pointer', transition: 'all .2s',
            background: drag ? 'var(--accent-dim)' : 'var(--bg2)' }}>
          <div style={{ width: 40, height: 40, borderRadius: '50%', margin: '0 auto 9px',
            background: drag ? 'var(--accent-dim)' : 'var(--bg3)',
            border: `1px solid ${drag ? 'rgba(234,88,12,0.4)' : 'var(--border2)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all .2s' }}>
            <i className="ti ti-cloud-upload" aria-hidden="true"
              style={{ fontSize: 20, color: drag ? 'var(--accent)' : 'var(--text3)' }} />
          </div>
          <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.5 }}>
            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Click to upload</span>
            {' '}or drag & drop
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>PDF or DOCX</div>
          </div>
        </div>
        <input ref={fileRef} type="file" accept=".pdf,.docx" style={{ display: 'none' }}
          onChange={e => { const f = e.target.files[0]; if (f) handleFile(f); e.target.value = '' }} />

        {uploadErr && (
          <div style={{ fontSize: 11, color: 'var(--danger)', marginTop: 8,
            padding: '6px 10px', background: 'rgba(220,38,38,0.06)',
            border: '1px solid rgba(220,38,38,0.2)', borderRadius: 'var(--r)',
            display: 'flex', alignItems: 'center', gap: 5 }}>
            <i className="ti ti-alert-circle" aria-hidden="true" style={{ fontSize: 13 }} />
            {uploadErr}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '12px 0',
          color: 'var(--text3)', fontSize: 11 }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          or
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        </div>

        <button onClick={() => setModalOpen(true)}
          style={{ width: '100%', padding: '8px', border: '1px solid var(--border2)',
            borderRadius: 'var(--r)', background: 'var(--bg2)', color: 'var(--text2)',
            fontFamily: 'var(--font-body)', fontSize: 12, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            transition: 'all .15s' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.background = 'var(--accent-dim)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text2)'; e.currentTarget.style.background = 'var(--bg2)' }}>
          <i className="ti ti-text-plus" aria-hidden="true" />
          Ingest raw text
        </button>
      </div>

      {/* Document list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 8px' }}>
        {docs.length === 0 ? (
          <div style={{ padding: '32px 16px', textAlign: 'center',
            color: 'var(--text3)', fontSize: 12, lineHeight: 1.7 }}>
            <div style={{ width: 50, height: 50, borderRadius: '50%',
              background: 'var(--bg3)', border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 12px' }}>
              <i className="ti ti-files" aria-hidden="true" style={{ fontSize: 22, color: 'var(--border2)' }} />
            </div>
            No documents yet.<br />
            <span style={{ color: 'var(--accent2)', fontWeight: 500 }}>Upload</span> a PDF or DOCX to begin.
          </div>
        ) : (
          docs.map(doc => <DocItem key={doc.id} doc={doc} />)
        )}
      </div>

      {modalOpen && <TextIngestModal onClose={() => setModalOpen(false)} onSubmit={onAddText} />}
    </div>
  )
}