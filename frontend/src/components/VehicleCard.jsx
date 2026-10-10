import { Link } from 'react-router-dom'
import { friendlyDate } from '../api'

export default function VehicleCard({ vehicle }) {
  return <article className="vehicle-card"><div className="card-top"><span className="vehicle-icon">↗</span><span className="eyebrow">{vehicle.year} MODEL</span></div>
    <h2>{vehicle.make} {vehicle.model}</h2><p className="muted">{vehicle.registration_number}</p>
    <div className="mileage"><strong>{Number(vehicle.current_mileage).toLocaleString()}</strong><span>km current mileage</span></div>
    <div className="card-stats"><div><span>Last service</span><b>{friendlyDate(vehicle.last_service_date)}</b></div><div><span>Next service</span><b>{friendlyDate(vehicle.next_service_date)}</b></div></div>
    <div className="card-bottom"><span>{vehicle.maintenance_count} service{vehicle.maintenance_count === 1 ? '' : 's'} logged</span><Link className="arrow-link" to={`/vehicles/${vehicle.id}`}>View details <span>→</span></Link></div>
  </article>
}
