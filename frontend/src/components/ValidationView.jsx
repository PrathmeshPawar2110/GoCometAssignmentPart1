const FIELD_LABELS = {
  consignee_name:    'Consignee Name',
  hs_code:           'HS Code',
  port_of_loading:   'Port of Loading',
  port_of_discharge: 'Port of Discharge',
  incoterms:         'Incoterms',
  description_goods: 'Description of Goods',
  gross_weight:      'Gross Weight',
  invoice_number:    'Invoice Number',
}

function VerdictBadge({ status }) {
  const map = {
    match:     ['badge-green',  '✓ match'],
    mismatch:  ['badge-red',    '✕ mismatch'],
    uncertain: ['badge-orange', '? uncertain'],
  }
  const [cls, label] = map[status] ?? ['badge-grey', status]
  return <span className={`badge ${cls}`}>{label}</span>
}

function Summary({ mismatch_count, uncertain_count }) {
  const total = mismatch_count + uncertain_count
  if (total === 0) {
    return <span className="badge badge-green">All fields passed</span>
  }
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {mismatch_count > 0 && <span className="badge badge-red">{mismatch_count} mismatch{mismatch_count > 1 ? 'es' : ''}</span>}
      {uncertain_count > 0 && <span className="badge badge-orange">{uncertain_count} uncertain</span>}
    </div>
  )
}

export default function ValidationView({ validation }) {
  if (!validation) {
    return (
      <div className="card">
        <div className="card-title">Validation Results</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '32px 0' }}>
          Waiting for validation…
        </div>
      </div>
    )
  }

  const verdicts = validation.verdicts ?? {}
  const rows = Object.keys(FIELD_LABELS).map(key => ({
    key,
    label: FIELD_LABELS[key],
    verdict: verdicts[key],
  }))

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span className="card-title" style={{ marginBottom: 0 }}>Validation Results</span>
        <Summary
          mismatch_count={validation.mismatch_count}
          uncertain_count={validation.uncertain_count}
        />
      </div>

      <table className="field-table">
        <thead>
          <tr>
            <th style={{ width: '34%' }}>Field</th>
            <th style={{ width: '22%' }}>Status</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ key, label, verdict }) => {
            if (!verdict) return null
            return (
              <tr key={key}>
                <td><span className="field-name">{label}</span></td>
                <td><VerdictBadge status={verdict.status} /></td>
                <td>
                  {verdict.status === 'mismatch' ? (
                    <div style={{ fontSize: 11 }}>
                      <div><span style={{ color: 'var(--text-muted)' }}>found:</span> <span style={{ color: 'var(--red)', fontFamily: 'JetBrains Mono, monospace' }}>{verdict.found ?? '—'}</span></div>
                      <div><span style={{ color: 'var(--text-muted)' }}>expected:</span> <span style={{ color: 'var(--green)', fontFamily: 'JetBrains Mono, monospace' }}>{verdict.expected ?? '—'}</span></div>
                    </div>
                  ) : verdict.status === 'uncertain' ? (
                    <span style={{ fontSize: 11, color: 'var(--orange)' }}>{verdict.reason}</span>
                  ) : (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{verdict.reason}</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
