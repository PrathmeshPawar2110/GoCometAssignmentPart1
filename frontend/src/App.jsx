import { useState, useEffect, useRef } from 'react'
import UploadPanel from './components/UploadPanel.jsx'
import ExtractionView from './components/ExtractionView.jsx'
import ValidationView from './components/ValidationView.jsx'
import DecisionPanel from './components/DecisionPanel.jsx'
import QueryBox from './components/QueryBox.jsx'
import PipelineStatus from './components/PipelineStatus.jsx'

const API = 'http://localhost:8000'
const POLL_MS = 2000
const TERMINAL_STATUSES = new Set(['complete', 'failed'])

export default function App() {
  const [jobId, setJobId] = useState(null)
  const [job, setJob] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const intervalRef = useRef(null)

  // ── Polling ──────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return
    if (TERMINAL_STATUSES.has(job?.status)) return

    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${jobId}`)
        if (!res.ok) return
        const data = await res.json()
        setJob(data)
        if (TERMINAL_STATUSES.has(data.status)) {
          clearInterval(intervalRef.current)
        }
      } catch (_) { /* network hiccup — retry next tick */ }
    }, POLL_MS)

    return () => clearInterval(intervalRef.current)
  }, [jobId, job?.status])

  // ── Submit handler ────────────────────────────────────────
  async function handleSubmit({ file, customerId, docType }) {
    setSubmitError(null)
    setJob(null)
    setJobId(null)

    const form = new FormData()
    form.append('file', file)
    form.append('customer_id', customerId)
    form.append('doc_type', docType)

    try {
      const res = await fetch(`${API}/jobs`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const { job_id, status } = await res.json()
      setJob({ job_id, status })
      setJobId(job_id)
    } catch (e) {
      setSubmitError(e.message)
    }
  }

  const isRunning = job && !TERMINAL_STATUSES.has(job.status)

  return (
    <div className="layout">
      <header className="header">
        <div className="header-logo">N</div>
        <div>
          <h1>Nova · Trade Pipeline</h1>
          <span>GoComet — Multi-Agent Document Processing POC</span>
        </div>
      </header>

      <UploadPanel onSubmit={handleSubmit} isRunning={isRunning} />

      {submitError && (
        <div style={{ margin: '16px 0', padding: '12px 16px', background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, color: '#ef4444', fontSize: 13 }}>
          {submitError}
        </div>
      )}

      {job && (
        <>
          <PipelineStatus status={job.status} jobId={job.job_id} />

          {(job.extraction || job.validation || job.decision) && (
            <div className="results-grid">
              <ExtractionView extraction={job.extraction} />
              <ValidationView validation={job.validation} />
              <DecisionPanel decision={job.decision} />
            </div>
          )}
        </>
      )}

      <QueryBox apiBase={API} />
    </div>
  )
}
