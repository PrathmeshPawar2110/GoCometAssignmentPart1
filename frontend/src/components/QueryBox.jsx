import { useState } from 'react'

const EXAMPLE_QUESTIONS = [
  'How many shipments were flagged this week?',
  'How many jobs were auto-approved today?',
  'Show all failed jobs',
  'How many jobs per customer?',
]

export default function QueryBox({ apiBase }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function runQuery(q) {
    const text = q ?? question
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="query-section">
      <div className="card">
        <div className="card-title">Natural Language Query</div>

        <div className="query-input-row">
          <input
            type="text"
            placeholder="Ask anything about your shipments…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runQuery()}
          />
          <button
            className="btn btn-primary"
            onClick={() => runQuery()}
            disabled={loading || !question.trim()}
          >
            {loading ? <span className="spinner" /> : 'Ask'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {EXAMPLE_QUESTIONS.map(q => (
            <button
              key={q}
              className="btn btn-ghost"
              style={{ fontSize: 12, padding: '5px 12px' }}
              onClick={() => { setQuestion(q); runQuery(q) }}
            >
              {q}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ color: 'var(--red)', fontSize: 13, padding: '10px 0' }}>{error}</div>
        )}

        {result && (
          <div>
            <div className="answer-box">{result.answer}</div>
            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--text-muted)', userSelect: 'none' }}>
                SQL used ↓
              </summary>
              <div className="sql-reveal">{result.sql_used}</div>
            </details>
            {result.rows?.length > 0 && (
              <div style={{ marginTop: 12, overflowX: 'auto' }}>
                <table className="field-table">
                  <thead>
                    <tr>
                      {Object.keys(result.rows[0]).map(col => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, 20).map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val, j) => (
                          <td key={j}>
                            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                              {val === null ? <em style={{ color: 'var(--text-muted)' }}>null</em> : String(val)}
                            </span>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
