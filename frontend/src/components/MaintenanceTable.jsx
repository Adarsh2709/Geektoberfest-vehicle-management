import { useState } from 'react'
import { downloadReceipt, formatCost, friendlyDate } from '../api'

export default function MaintenanceTable({ records, onEdit, onDelete, isFiltered, onResetFilters }) {
  const [downloadError, setDownloadError] = useState('')
  async function handleDownload(record) {
    setDownloadError('')
    try {
      await downloadReceipt(record.id, record.receipt_original_name)
    } catch (err) { setDownloadError(err.message) }
  }
  if (!records.length) {
    if (isFiltered) {
      return (
        <div className="empty-history" role="status">
          <span>⌕</span>
          <h3>No records in selected period</h3>
          <p>No service records match your chosen date range or filter criteria.</p>
          {onResetFilters && (
            <button className="button secondary" style={{ marginTop: '0.75rem' }} onClick={onResetFilters}>
              Reset filters
            </button>
          )}
        </div>
      )
    }
    return <div className="empty-history"><span>◷</span><h3>No service records yet</h3><p>Add the first service to start this vehicle’s history.</p></div>
  }
  return <div className="table-wrap">{downloadError && <p className="error-banner">{downloadError}</p>}<table><thead><tr><th>Date</th><th>Service</th><th>Mileage</th><th>Cost</th><th>Next service</th><th>Receipt</th><th></th></tr></thead><tbody>{records.map(record => <tr key={record.id}><td>{friendlyDate(record.service_date)}</td><td><b>{record.service_type}</b>{record.description && <small>{record.description}</small>}</td><td>{Number(record.mileage).toLocaleString()} km</td><td>{formatCost(record.cost)}</td><td>{friendlyDate(record.next_service_date)}</td><td>{record.receipt_original_name ? <button className="receipt-link" onClick={() => handleDownload(record)}>View receipt</button> : '—'}</td><td className="row-actions"><button onClick={() => onEdit(record)}>Edit</button><button className="danger-link" onClick={() => onDelete(record)}>Delete</button></td></tr>)}</tbody></table></div>
}
