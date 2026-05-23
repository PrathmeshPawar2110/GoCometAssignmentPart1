const STEPS = [
  { key: 'pending',    label: 'Queued' },
  { key: 'extracting', label: 'Extract' },
  { key: 'validating', label: 'Validate' },
  { key: 'routing',    label: 'Route' },
  { key: 'complete',   label: 'Done' },
]

const STATUS_ORDER = {
  pending: 0, extracting: 1, validating: 2, routing: 3, complete: 4, failed: 4,
}

export default function PipelineStatus({ status, jobId }) {
  const current = STATUS_ORDER[status] ?? 0
  const failed = status === 'failed'

  return (
    <div className="card" style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span className="card-title" style={{ marginBottom: 0 }}>Pipeline</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-muted)' }}>
          {jobId}
        </span>
      </div>
      <div className="pipeline-bar">
        {STEPS.map((step, i) => {
          const stepIdx = i
          let dotClass = ''
          if (failed && stepIdx === current) {
            dotClass = 'error'
          } else if (stepIdx < current) {
            dotClass = 'done'
          } else if (stepIdx === current) {
            dotClass = status === 'complete' ? 'done' : 'active'
          }
          return (
            <div className="pipeline-step" key={step.key}>
              <div className={`step-dot ${dotClass}`}>
                {dotClass === 'done' ? '✓' : dotClass === 'error' ? '✕' : i + 1}
              </div>
              <span className="step-label">{step.label}</span>
            </div>
          )
        })}
      </div>
      {failed && (
        <div style={{ textAlign: 'center', color: 'var(--red)', fontSize: 13, marginTop: 4 }}>
          Pipeline failed — check backend logs for details.
        </div>
      )}
    </div>
  )
}
