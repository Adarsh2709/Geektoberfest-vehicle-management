import { friendlyDate } from '../api'

export default function MaintenanceTable({ records, onEdit, onDelete }) {
  if (!records.length) return <div className="empty-history"><span>◷</span><h3>No service records yet</h3><p>Add the first service to start this vehicle’s history.</p></div>
  return <div className="table-wrap"><table><thead><tr><th>Date</th><th>Service</th><th>Mileage</th><th>Cost</th><th>Next service</th><th></th></tr></thead><tbody>{records.map(record => <tr key={record.id}><td>{friendlyDate(record.service_date)}</td><td><b>{record.service_type}</b>{record.description && <small>{record.description}</small>}</td><td>{Number(record.mileage).toLocaleString()} km</td><td>₹{Number(record.cost).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td><td>{friendlyDate(record.next_service_date)}</td><td className="row-actions"><button onClick={() => onEdit(record)}>Edit</button><button className="danger-link" onClick={() => onDelete(record)}>Delete</button></td></tr>)}</tbody></table></div>
}
