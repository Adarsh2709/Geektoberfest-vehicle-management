import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, friendlyDate } from '../api'
import { SERVICE_TYPES } from '../serviceTypes'
import MaintenanceForm from '../components/MaintenanceForm'
import MaintenanceTable from '../components/MaintenanceTable'
import VehicleForm from '../components/VehicleForm'

export default function VehicleDetails() {
  const { id } = useParams(); const navigate = useNavigate()
  const [vehicle, setVehicle] = useState(null); const [records, setRecords] = useState([]); const [error, setError] = useState('')
  const [filter, setFilter] = useState(''); const [startDate, setStartDate] = useState(''); const [endDate, setEndDate] = useState(''); const [sort, setSort] = useState('desc')
  const [summary, setSummary] = useState(null)
  const [page, setPage] = useState(1)
  const limit = 10

  function formatINR(value) { const amount = Number(value ?? 0); return Number.isFinite(amount) ? amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-' }

  async function loadRecords() {
    const params = new URLSearchParams({ sort, page, limit })
    if (filter) params.set('service_type', filter)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const result = await api(`/vehicles/${id}/maintenance?${params}`)
    setRecords(result)
  }

  async function loadSummary() {
    const params = new URLSearchParams()
    if (filter) params.set('service_type', filter)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const query = params.toString() ? `?${params}` : ''
    try { setSummary(await api(`/vehicles/${id}/maintenance/summary${query}`)) } catch { setSummary(null) }
  }

  useEffect(() => { api(`/vehicles/${id}`).then(setVehicle).catch(err => setError(err.message)) }, [id])
  useEffect(() => { loadRecords().catch(err => setError(err.message)); loadSummary() }, [id, filter, startDate, endDate, sort, page])

  async function deleteVehicle() { if (!window.confirm('Delete this vehicle and all its service history?')) return; try { await api(`/vehicles/${id}`, { method: 'DELETE' }); navigate('/') } catch (err) { setError(err.message) } }
  async function deleteRecord(record) { if (!window.confirm(`Delete the ${record.service_type} record?`)) return; try { await api(`/maintenance/${record.id}`, { method: 'DELETE' }); loadRecords(); loadSummary() } catch (err) { setError(err.message) } }

  if (!vehicle && !error) return <div className="loading">Loading vehicle...</div>
  if (error && !vehicle) return <><Link className="back-link" to="/">← Back to garage</Link><p className="error-banner">{error}</p></>

  return (
    <div className="vehicle-details">
      <Link className="back-link" to="/">← Back to garage</Link>
      {error && <p className="error-banner">{error}</p>}
      
      <section className="detail-hero">
        <div className="detail-title">
          <span className="vehicle-icon large">🚗</span>
          <div>
            <span className="eyebrow">{vehicle.year} MODEL</span>
            <h2>{vehicle.make} {vehicle.model}</h2>
          </div>
        </div>
        <button className="text-button danger" onClick={deleteVehicle}>Delete vehicle</button>
      </section>

      <section className="maintenance-section">
        <div className="section-heading">
          <h3>Service history</h3>
          {summary && <span className="summary">Total spent in selected period: <strong>₹{formatINR(summary.total_cost)}</strong> ({summary.record_count} records)</span>}
        </div>

        <div className="filters">
          <label>Service type
            <select value={filter} onChange={e => { setFilter(e.target.value); setPage(1) }}>
              <option value="">All services</option>
              {SERVICE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label>Sort
            <select value={sort} onChange={e => setSort(e.target.value)}>
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
          </label>
        </div>

        <MaintenanceTable records={records} onDelete={deleteRecord} />

        {/* Pagination Controls */}
        <div className="pagination-controls" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1.5rem' }}>
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn">Previous</button>
          <span>Page {page}</span>
          <button disabled={records.length < limit} onClick={() => setPage(p => p + 1)} className="btn">Next</button>
        </div>
      </section>
    </div>
  )
}