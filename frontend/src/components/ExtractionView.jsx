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

function confColor(conf) {
  if (conf >= 0.85) return 'var(--green)'
  if (conf >= 0.60) return 'var(--yellow)'
  return 'var(--red)'
}

function ConfBar({ confidence }) {
  const pct = Math.round(confidence * 100)
  return (
    <div className="conf-bar-wrap">
      <div className="conf-bar-bg">
        <div
          className="conf-bar-fill"
          style={{ width: `${pct}%`, background: confColor(confidence) }}
        />
      </div>
      <span className="conf-val" style={{ color: confColor(confidence) }}>
        {pct}%
      </span>
    </div>
  )
}

export default function ExtractionView({ extraction }) {
  if (!extraction) {
    return (
      <div className="card">
        <div className="card-title">Extracted Fields</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '32px 0' }}>
          Waiting for extraction…
        </div>
      </div>
    )
  }

  const fields = Object.keys(FIELD_LABELS).map(key => ({
    key,
    label: FIELD_LABELS[key],
    field: extraction[key] ?? { value: null, confidence: 0 },
  }))

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span className="card-title" style={{ marginBottom: 0 }}>Extracted Fields</span>
        <span className="badge badge-blue">{extraction.doc_type}</span>
      </div>

      <table className="field-table">
        <thead>
          <tr>
            <th style={{ width: '38%' }}>Field</th>
            <th style={{ width: '34%' }}>Value</th>
            <th style={{ width: '28%' }}>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {fields.map(({ key, label, field }) => (
            <tr key={key}>
              <td><span className="field-name">{label}</span></td>
              <td>
                {field.value
                  ? <span className="field-value">{field.value}</span>
                  : <span className="null-val">not found</span>}
              </td>
              <td><ConfBar confidence={field.confidence} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--text-muted)' }}>Avg confidence</span>
        <span style={{ color: confColor(extraction.avg_confidence), fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
          {Math.round(extraction.avg_confidence * 100)}%
        </span>
      </div>
    </div>
  )
}
