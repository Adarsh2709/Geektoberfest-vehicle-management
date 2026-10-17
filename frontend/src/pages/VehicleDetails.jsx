import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, downloadMaintenanceCsv, formatCost, friendlyDate } from '../api'
import { SERVICE_TYPES } from '../serviceTypes'
import MaintenanceForm from '../components/MaintenanceForm'
import MaintenanceTable from '../components/MaintenanceTable'
import VehicleForm from '../components/VehicleForm'

export default function VehicleDetails() {
  const { id } = useParams(); const navigate = useNavigate()
  const [vehicle, setVehicle] = useState(null); const [records, setRecords] = useState([]); const [error, setError] = useState('')
  const [filter, setFilter] = useState(''); const [startDate, setStartDate] = useState(''); const [endDate, setEndDate] = useState(''); const [sort, setSort] = useState('desc')
  const [summary, setSummary] = useState(null)
  const [formMode, setFormMode] = useState('')
  const [editingRecord, setEditingRecord] = useState(null)
  const [page, setPage] = useState(1)
  const limit = 10

  async function loadRecords() {
    if (startDate && endDate && startDate > endDate) {
      setError('Start date cannot be after end date')
      setRecords([])
      return
    }
    setError('')
    const params = new URLSearchParams({ sort, page, limit })
    if (filter) params.set('service_type', filter)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const result = await api(`/vehicles/${id}/maintenance?${params}`)
    setRecords(result)
  }

  async function loadSummary() {
    if (startDate && endDate && startDate > endDate) {
      setSummary(null)
      return
    }
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
  async function deleteRecord(record) { if (!window.confirm(`Delete the ${record.service_type} record?`)) return; try { await api(`/maintenance/${record.id}`, { method: 'DELETE' }); await loadRecords(); await loadSummary(); setVehicle(await api(`/vehicles/${id}`)) } catch (err) { setError(err.message) } }
  async function exportCsv() { try { await downloadMaintenanceCsv(id) } catch (err) { setError(err.message) } }
  function resetAllFilters() { setStartDate(''); setEndDate(''); setFilter(''); setError('') }
  if (!vehicle && !error) return <div className="loading">Loading vehicle…</div>
  if (error && !vehicle) return <><Link className="back-link" to="/">← Back to garage</Link><p className="error-banner">{error}</p></>
  return <div className="vehicle-details"><Link className="back-link" to="/">← Back to garage</Link>{error && <p className="error-banner">{error}</p>}
    <section className="detail-hero"><div className="detail-title"><span className="vehicle-icon large">↗</span><div><span className="eyebrow">{vehicle.year} MODEL · {vehicle.registration_number}</span><h1>{vehicle.make} {vehicle.model}</h1><p>{Number(vehicle.current_mileage).toLocaleString()} km on the road</p></div></div><div className="detail-actions"><button className="button secondary" onClick={() => setFormMode(formMode === 'vehicle' ? '' : 'vehicle')}>Edit vehicle</button><button className="button danger" onClick={deleteVehicle}>Delete</button></div></section>
    {formMode === 'vehicle' && <section className="inline-editor"><div className="section-heading"><div><h2>Edit vehicle details</h2></div><button className="text-button" onClick={() => setFormMode('')}>Close</button></div><VehicleForm vehicleId={id} initial={vehicle} onSaved={async () => { setVehicle(await api(`/vehicles/${id}`)); setFormMode('') }} /></section>}
    <section className="maintenance-section">
      <div className="section-heading history-heading">
        <div>
          <span className="eyebrow">KEEP A GOOD RECORD</span>
          <h2>
            Service history{" "}
            <span className="count-pill">
              {vehicle.maintenance_count}
            </span>
          </h2>
          <p>Every check-up, repair, and little bit of care.</p>
        </div>

        <div className="detail-actions">
          <button
            className="button secondary"
            onClick={exportCsv}
          >
            Export CSV
          </button>
          <button
            className="button primary"
            onClick={() => {
              setEditingRecord(null);
              setFormMode(
                formMode === "maintenance" ? "" : "maintenance"
              );
            }}
          >
            ＋ Add service
          </button>
        </div>
      </div>

      <div className="filters">
        <label>
          Service type
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All services</option>
            {SERVICE_TYPES.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </select>
        </label>

        <label>
          From
          <input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setPage(1);
            }}
          />
        </label>

        <label>
          To
          <input
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setPage(1);
            }}
          />
        </label>

        <label>
          Order
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
            <option value="cost_desc">Cost: High to Low</option>
            <option value="cost_asc">Cost: Low to High</option>
          </select>
        </label>

        {(startDate || endDate || filter) && (
          <button
            type="button"
            className="button secondary"
            style={{
              fontSize: "0.85rem",
              padding: "0.35rem 0.6rem",
            }}
            onClick={resetAllFilters}
          >
            Reset
          </button>
        )}

        <span>
          {records.length} record
          {records.length === 1 ? "" : "s"}
        </span>
      </div>

      <p className="spending-summary" data-testid="spending-summary">Total spent in selected period: <strong>{summary ? formatCost(summary.total_cost) : '—'}</strong>{summary && <span> · {summary.record_count} service{summary.record_count === 1 ? '' : 's'}</span>}</p>
      {formMode === 'maintenance' && <div className="inline-editor"><div className="section-heading"><div><h2>{editingRecord ? 'Edit service' : 'Add a service'}</h2></div></div><MaintenanceForm vehicleId={id} record={editingRecord} onCancel={() => setFormMode('')} onSaved={async () => { await loadRecords(); await loadSummary(); setFormMode(''); setEditingRecord(null); const latest = await api(`/vehicles/${id}`); setVehicle(latest) }} /></div>}
      <MaintenanceTable records={records} isFiltered={Boolean(startDate || endDate || filter)} onResetFilters={resetAllFilters} onEdit={record => { setEditingRecord(record); setFormMode('maintenance') }} onDelete={deleteRecord} />
      <div className="pagination-controls" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1.5rem' }}>
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn">Previous</button>
        <span>Page {page}</span>
        <button disabled={records.length < limit} onClick={() => setPage(p => p + 1)} className="btn">Next</button>
      </div>
    </section><p className="last-service-note">Last recorded service: {friendlyDate(vehicle.last_service_date)}</p>
  </div>
}
