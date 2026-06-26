import { useState, useRef } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function parseApiError(detail) {
  if (!detail) return 'Processing failed'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(', ')
  }
  if (typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return 'Processing failed'
}

function UploadIcon() {
  return (
    <svg className="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 16V4m0 0L8 8m4-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg className="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" strokeLinejoin="round" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
    </svg>
  )
}

function FieldGroup({ title, fields }) {
  const entries = Object.entries(fields).filter(([key]) => !key.endsWith('Numeric'))

  return (
    <div className="field-group">
      <h3 className="field-group-title">{title}</h3>
      <ul className="field-list">
        {entries.map(([key, value]) => {
          const label = key
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, (s) => s.toUpperCase())
          return (
            <li key={key} className="field-item">
              <span className="field-label">{label}</span>
              <p className={`field-value ${value ? '' : 'is-missing'}`}>
                {value ?? 'Not found'}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function DateValidationRow({ label, data }) {
  if (!data?.raw) return null

  return (
    <div className={`date-row ${data.valid ? 'is-valid' : 'is-invalid'}`}>
      <div className="date-row-header">
        <span className="date-label">{label}</span>
        <span className={`date-status ${data.valid ? 'valid' : 'invalid'}`}>
          {data.valid ? 'Valid' : 'Invalid'}
        </span>
      </div>
      <p className="date-raw">{data.raw}</p>
      {data.valid && data.normalized && (
        <p className="date-normalized">Normalized: {data.normalized}</p>
      )}
      {!data.valid && data.error && (
        <p className="date-error">{data.error}</p>
      )}
    </div>
  )
}

function DateRangeValidation({ label, data }) {
  if (!data?.raw) return null

  return (
    <div className={`date-row ${data.valid ? 'is-valid' : 'is-invalid'}`}>
      <div className="date-row-header">
        <span className="date-label">{label}</span>
        <span className={`date-status ${data.valid ? 'valid' : 'invalid'}`}>
          {data.valid ? 'Valid' : 'Invalid'}
        </span>
      </div>
      <p className="date-raw">{data.raw}</p>
      {data.start?.valid && (
        <p className="date-normalized">
          Start: {data.start.normalized}
          {data.end?.valid ? ` · End: ${data.end.normalized}` : ''}
        </p>
      )}
      {!data.valid && data.error && (
        <p className="date-error">{data.error}</p>
      )}
    </div>
  )
}

function App() {
  const [inputMode, setInputMode] = useState('file')
  const [file, setFile] = useState(null)
  const [pastedText, setPastedText] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  const handleFile = (selected) => {
    if (!selected) return
    const ext = selected.name.toLowerCase()
    if (!ext.endsWith('.pdf') && !ext.endsWith('.txt')) {
      setError('Please upload a PDF or TXT FNOL document.')
      return
    }
    setFile(selected)
    setError(null)
    setResult(null)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const canSubmit =
    inputMode === 'file' ? !!file : pastedText.trim().length > 0

  const processDocument = async () => {
    if (!canSubmit) return
    setLoading(true)
    setError(null)

    try {
      let res
      if (inputMode === 'file') {
        const formData = new FormData()
        formData.append('file', file)
        res = await fetch(`${API_URL}/api/process-fnol`, {
          method: 'POST',
          body: formData,
        })
      } else {
        res = await fetch(`${API_URL}/api/process-fnol`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: pastedText.trim() }),
        })
      }

      const data = await res.json()
      if (!res.ok) throw new Error(parseApiError(data.detail))
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (mode) => {
    setInputMode(mode)
    setError(null)
    setResult(null)
  }

  const fileType = file
    ? file.name.toLowerCase().endsWith('.pdf')
      ? 'PDF'
      : 'TXT'
    : null

  return (
    <div className="app">
      <nav className="nav">
        <div className="nav-inner">
          <div className="nav-brand">
            <div className="nav-logo">F</div>
            <span className="nav-title">FNOL Agent</span>
          </div>
          <span className="nav-meta">Claims routing</span>
        </div>
      </nav>

      <header className="hero">
        <h1>Process First Notice of Loss documents</h1>
        <p>
          Upload a PDF or TXT file, or paste FNOL text directly to extract fields,
          validate dates, and route the claim.
        </p>
      </header>

      <main className="main">
        <section className="card upload-section">
          <div className="card-header">
            <h2 className="card-title">Add FNOL document</h2>
            <p className="card-desc">
              Accepts PDF, TXT files, or pasted plain text.
            </p>
          </div>

          <div className="input-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={inputMode === 'file'}
              className={`input-tab ${inputMode === 'file' ? 'active' : ''}`}
              onClick={() => switchMode('file')}
            >
              Upload file
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={inputMode === 'text'}
              className={`input-tab ${inputMode === 'text' ? 'active' : ''}`}
              onClick={() => switchMode('text')}
            >
              Paste text
            </button>
          </div>

          {inputMode === 'file' ? (
            <div
              className={`dropzone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf,.pdf,text/plain,.txt"
                hidden
                onChange={(e) => handleFile(e.target.files[0])}
              />
              {file ? (
                <>
                  <FileIcon />
                  <p className="file-name">{file.name}</p>
                  {fileType && <span className="file-type-badge">{fileType}</span>}
                  <p className="hint">PDF or TXT · click or drop to replace</p>
                </>
              ) : (
                <>
                  <UploadIcon />
                  <p className="dropzone-text">Drag and drop a PDF or TXT file</p>
                  <p className="hint">or click to browse</p>
                </>
              )}
            </div>
          ) : (
            <div className="text-input-wrap">
              <textarea
                className="text-input"
                placeholder={`Paste FNOL text here, e.g.\n\nIncident Date: May 1 2026\nEffective Dates: may1 2024 - May 1 2025\n...`}
                value={pastedText}
                onChange={(e) => {
                  setPastedText(e.target.value)
                  setError(null)
                  setResult(null)
                }}
                rows={12}
              />
              <p className="hint text-input-hint">
                Supports dates like <code>May 1 2026</code>, <code>may1 2026</code>, or <code>03/12/2025</code>
              </p>
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            disabled={!canSubmit || loading}
            onClick={processDocument}
          >
            {loading && <span className="btn-spinner" aria-hidden="true" />}
            {loading ? 'Processing' : 'Analyze FNOL'}
          </button>

          {error && <div className="error-banner" role="alert">{error}</div>}
        </section>

        {result && (
          <section className="results">
            <div className="card route-card">
              <div className="route-header">
                <span className="badge">Recommended route</span>
              </div>
              <h2 className="route-name">{result.recommendedRoute}</h2>
              <p className="reasoning">{result.reasoning}</p>
            </div>

            {result.dateValidation && (
              <div className="card date-validation-card">
                <div className="card-header">
                  <h2 className="card-title">Date validation</h2>
                  <p className="card-desc">
                    Parses text dates like &quot;May 1 2026&quot; and &quot;may1 2026&quot;.
                  </p>
                </div>
                <div className="date-validation-list">
                  <DateValidationRow
                    label="Incident date"
                    data={result.dateValidation.incidentDate}
                  />
                  <DateRangeValidation
                    label="Effective dates"
                    data={result.dateValidation.effectiveDates}
                  />
                </div>
              </div>
            )}

            {result.missingFields.length > 0 && (
              <div className="card missing-card">
                <div className="card-header">
                  <h2 className="card-title">Missing mandatory fields</h2>
                  <p className="card-desc">
                    {result.missingFields.length} field{result.missingFields.length !== 1 ? 's' : ''} require attention.
                  </p>
                </div>
                <ul className="missing-tags">
                  {result.missingFields.map((f) => (
                    <li key={f} className="missing-tag">
                      {f.replace(/([A-Z])/g, ' $1')}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="card extracted-card">
              <div className="card-header">
                <h2 className="card-title">Extracted fields</h2>
                <p className="card-desc">Structured data parsed from the document.</p>
              </div>
              <div className="field-grid">
                <FieldGroup
                  title="Policy"
                  fields={result.extractedFields.policyInformation}
                />
                <FieldGroup
                  title="Incident"
                  fields={result.extractedFields.incidentInformation}
                />
                <FieldGroup
                  title="Parties"
                  fields={result.extractedFields.involvedParties}
                />
                <FieldGroup
                  title="Asset"
                  fields={result.extractedFields.assetDetails}
                />
                <FieldGroup title="Other" fields={result.extractedFields.other} />
              </div>
            </div>

            <details className="card json-card">
              <summary className="json-summary">Raw JSON output</summary>
              <pre className="json-pre">{JSON.stringify(result, null, 2)}</pre>
            </details>
          </section>
        )}
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <ul className="footer-rules">
            <li>Fast-track — damage under $25k</li>
            <li>Manual review — missing fields</li>
            <li>Investigation — fraud keywords</li>
            <li>Specialist — injury claims</li>
          </ul>
        </div>
      </footer>
    </div>
  )
}

export default App
