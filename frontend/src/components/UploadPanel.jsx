import { useState, useRef } from 'react'

const DOC_TYPES = [
  { value: 'BoL', label: 'Bill of Lading' },
  { value: 'CommercialInvoice', label: 'Commercial Invoice' },
  { value: 'PackingList', label: 'Packing List' },
  { value: 'CertificateOfOrigin', label: 'Certificate of Origin' },
]

const CUSTOMERS = [
  { value: 'ACME_001', label: 'Acme Imports Pvt Ltd (ACME_001)' },
  { value: 'TEXTILES_002', label: 'Sunrise Textiles Pvt Ltd (TEXTILES_002)' },
  { value: 'ELECPARTS_003', label: 'TechParts Global India Pvt Ltd (ELECPARTS_003)' },
]

export default function UploadPanel({ onSubmit, isRunning }) {
  const [file, setFile] = useState(null)
  const [docType, setDocType] = useState('BoL')
  const [customerId, setCustomerId] = useState('ACME_001')
  const [dragover, setDragover] = useState(false)
  const inputRef = useRef(null)

  function pickFile(f) {
    if (!f) return
    const ok = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp']
    if (!ok.includes(f.type) && !f.name.match(/\.(pdf|jpg|jpeg|png|webp)$/i)) return
    setFile(f)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragover(false)
    pickFile(e.dataTransfer.files[0])
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file || isRunning) return
    await onSubmit({ file, customerId, docType })
  }

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-title">Upload Document</div>
      <form onSubmit={handleSubmit}>
        <div
          className={`dropzone${dragover ? ' dragover' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragover(true) }}
          onDragLeave={() => setDragover(false)}
          onDrop={handleDrop}
          style={{ marginBottom: 20 }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            style={{ display: 'none' }}
            onChange={e => pickFile(e.target.files[0])}
          />
          <div className="dropzone-icon">📄</div>
          {file
            ? <div className="file-selected">✓ {file.name} ({(file.size / 1024).toFixed(1)} KB)</div>
            : <>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Drop a trade document here</div>
                <div className="dropzone-hint">PDF, JPG, PNG, or WEBP · Click to browse</div>
              </>
          }
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Customer</label>
            <select value={customerId} onChange={e => setCustomerId(e.target.value)} style={{ width: '100%' }}>
              {CUSTOMERS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Document Type</label>
            <select value={docType} onChange={e => setDocType(e.target.value)} style={{ width: '100%' }}>
              {DOC_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={!file || isRunning}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {isRunning
            ? <><span className="spinner" /> Processing…</>
            : '▶  Run Pipeline'}
        </button>
      </form>
    </div>
  )
}
