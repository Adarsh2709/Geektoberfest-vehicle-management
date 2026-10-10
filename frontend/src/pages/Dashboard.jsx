import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import VehicleCard from '../components/VehicleCard'

export default function Dashboard() {
  const [vehicles, setVehicles] = useState([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  useEffect(() => { api('/vehicles').then(setVehicles).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  return <><section className="page-heading"><div><span className="eyebrow">YOUR GARAGE</span><h1>Good to see you.</h1><p>Everything your vehicles need, in one place.</p></div><Link className="button primary" to="/vehicles/new"><span>＋</span> Add a vehicle</Link></section>
    <section className="section-heading"><div><h2>My vehicles <span className="count-pill">{vehicles.length}</span></h2><p>A little care goes a long way.</p></div></section>
    {error && <p className="error-banner">{error}</p>}{loading ? <div className="loading">Loading your vehicles…</div> : vehicles.length ? <div className="vehicle-grid">{vehicles.map(vehicle => <VehicleCard key={vehicle.id} vehicle={vehicle} />)}</div> : <div className="empty-garage"><span className="empty-art">⌁</span><h2>A good garage starts here.</h2><p>Add your first vehicle and keep all its care in one easy place.</p><Link className="button primary" to="/vehicles/new">＋ Add your first vehicle</Link></div>}
  </>
}
