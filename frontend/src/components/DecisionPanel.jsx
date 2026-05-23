const DECISION_CONFIG = {
  approve: { cls: 'decision-approve', badge: 'badge-green',  icon: '✓', label: 'Auto-Approved' },
  review:  { cls: 'decision-review',  badge: 'badge-yellow', icon: '⚠', label: 'Flagged for Review' },
  amend:   { cls: 'decision-amend',   badge: 'badge-red',    icon: '✕', label: 'Amendment Required' },
}

export default function DecisionPanel({ decision }) {
  if (!decision) {
    return (
      <div className="card">
        <div className="card-title">Decision</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '32px 0' }}>
          Waiting for routing decision…
        </div>
      </div>
    )
  }

  const cfg = DECISION_CONFIG[decision.decision] ?? DECISION_CONFIG.review

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span className="card-title" style={{ marginBottom: 0 }}>Decision</span>
        <span className={`badge ${cfg.badge}`}>{cfg.icon} {cfg.label}</span>
      </div>

      <div className={`decision-box ${cfg.cls}`}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '.5px' }}>
          Agent Reasoning
        </div>
        <div className="reasoning-text">{decision.reasoning}</div>
      </div>

      {decision.draft_message && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
            Draft Message
          </div>
          <div className="draft-box">{decision.draft_message}</div>
          <button
            className="btn btn-ghost"
            style={{ marginTop: 10, fontSize: 12, padding: '7px 14px' }}
            onClick={() => navigator.clipboard.writeText(decision.draft_message)}
          >
            Copy to clipboard
          </button>
        </div>
      )}
    </div>
  )
}
