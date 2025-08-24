import React, { useState } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [candidateId, setCandidateId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])

  const upload = async (e) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API}/api/upload`, { method: 'POST', body: fd })
      const data = await res.json()
      setCandidateId(data.candidate_id)
    } finally {
      setLoading(false)
    }
  }

  const evaluate = async () => {
    if (!candidateId) return
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('candidate_id', candidateId)
      const res = await fetch(`${API}/api/evaluate`, { method: 'POST', body: fd })
      const data = await res.json()
      setResult(data)
      setHistory(h => [data, ...h])
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async () => {
    const res = await fetch(`${API}/api/results`)
    const data = await res.json()
    setHistory(data)
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">RAG Resume Shortlister</h1>

      <form onSubmit={upload} className="bg-white rounded-2xl shadow p-4 mb-6">
        <label className="block text-sm font-medium mb-2">Upload Resume (PDF)</label>
        <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} className="mb-3" />
        <div className="flex gap-3">
          <button type="submit" className="px-4 py-2 rounded-xl bg-blue-600 text-white disabled:opacity-50" disabled={loading}>
            {loading ? 'Uploading...' : 'Upload'}
          </button>
          <button type="button" className="px-4 py-2 rounded-xl bg-emerald-600 text-white disabled:opacity-50" disabled={!candidateId || loading} onClick={evaluate}>
            {loading ? 'Evaluating...' : 'Evaluate'}
          </button>
        </div>
        {candidateId && <p className="text-sm mt-2">Candidate ID: <code>{candidateId}</code></p>}
      </form>

      {result && (
        <div className="bg-white rounded-2xl shadow p-4 mb-6">
          <h2 className="text-xl font-semibold mb-3">Evaluation Result</h2>
          <div className="mb-2">Overall Score: <span className="font-bold">{result.overall_percent}%</span></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="py-2 pr-3">Requisite</th>
                  <th className="py-2 pr-3">Score %</th>
                  <th className="py-2 pr-3">Comments</th>
                  <th className="py-2">Alternate Considerations</th>
                </tr>
              </thead>
              <tbody>
                {result.per_criterion?.map((row, idx) => (
                  <tr key={idx} className="border-b align-top">
                    <td className="py-2 pr-3 font-medium">{row.criterion}</td>
                    <td className="py-2 pr-3">{row.score_percent}</td>
                    <td className="py-2 pr-3">{row.rationale}</td>
                    <td className="py-2">
                      {Array.isArray(row.alternate_considerations) ? row.alternate_considerations.join('; ') : row.alternate_considerations}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3">
            <h3 className="font-semibold">Summary</h3>
            <p>Strengths: {result.summary?.strengths?.join(', ') || '-'}</p>
            <p>Gaps: {result.summary?.gaps?.join(', ') || '-'}</p>
            <p>Overall: {result.summary?.overall_comment}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Past Results</h2>
          <button className="px-3 py-1 rounded-lg bg-gray-900 text-white" onClick={fetchHistory}>Refresh</button>
        </div>
        <ul className="mt-3 space-y-2">
          {history.map((h, i) => (
            <li key={i} className="p-2 border rounded-lg">
              {h.id ? (
                <div className="flex items-center justify-between">
                  <span>Result #{h.id}</span>
                  <span className="font-medium">Score: {h.overall_score}</span>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <span>Candidate {h.candidate_id}</span>
                  <span className="font-medium">Score: {h.overall_percent}</span>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
