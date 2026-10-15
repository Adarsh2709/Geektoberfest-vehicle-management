import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import VehicleCard from '../components/VehicleCard'

export default function Dashboard() {
  const [vehicles, setVehicles] = useState([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const query = search ? `?search=${encodeURIComponent(search)}` : ''
    api(`/vehicles${query}`)
      .then(setVehicles)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [search])

  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">YOUR GARAGE</span>
          <h1>Good to see you.</h1>
          <p>Everything your vehicles need, in one place.</p>
        </div>
        <Link className="button primary" to="/vehicles/new">
          <span aria-hidden="true">＋</span> Add a vehicle
        </Link>
      </section>

      <section className="section-heading">
        <div>
          <h2>
            My vehicles <span className="count-pill">{vehicles.length}</span>
          </h2>
          <p>A little care goes a long way.</p>
        </div>
      </section>

      <div className="search-container" style={{ marginBottom: '1.5rem' }}>
        <input
          type="text"
          placeholder="Search by registration number..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="search-input"
          style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #ccc' }}
        />
      </div>

      {error && <p className="error-banner">{error}</p>}

      {loading ? (
        <div className="loading">Loading your vehicles…</div>
      ) : vehicles.length ? (
        <div className="vehicle-grid" data-testid="vehicle-grid">
          {vehicles.map(vehicle => (
            <VehicleCard key={vehicle.id} vehicle={vehicle} />
          ))}
        </div>
      ) : search ? (
        <div className="empty-garage" data-testid="empty-search-state" role="status">
          <span className="empty-art" aria-hidden="true">⌁</span>
          <h2>No vehicles found</h2>
          <p>No vehicles match your search registration number "{search}".</p>
        </div>
      ) : (
        <div className="empty-garage" data-testid="empty-state" role="status">
          <span className="empty-art" aria-hidden="true">⌁</span>
          <h2>A good garage starts here.</h2>
          <p>Add your first vehicle and keep all its care in one easy place.</p>
          <Link className="button primary" to="/vehicles/new">
            ＋ Add your first vehicle
          </Link>
        </div>
      )}
    </>
  )
}