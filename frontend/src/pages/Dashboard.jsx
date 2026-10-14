import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import VehicleCard from '../components/VehicleCard'

export default function Dashboard() {
  const [vehicles, setVehicles] = useState([])
  const [registrationSearch, setRegistrationSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const query = registrationSearch.trim()
    const path = query ? `/vehicles?registration_number=${encodeURIComponent(query)}` : '/vehicles'
    setLoading(true)
    api(path)
      .then(setVehicles)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [registrationSearch])

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

      <div className="vehicle-search">
        <label htmlFor="registration-search">Search by registration number</label>
        <input
          id="registration-search"
          type="search"
          value={registrationSearch}
          onChange={event => setRegistrationSearch(event.target.value)}
          placeholder="e.g. KA01AB1234"
          aria-describedby="registration-search-hint"
        />
        <p id="registration-search-hint">Matches are case-insensitive; spaces at the beginning or end are ignored.</p>
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
      ) : registrationSearch.trim() ? (
        <div className="empty-garage" data-testid="search-empty-state" role="status">
          <h2>No vehicles found</h2>
          <p>No registration numbers match “{registrationSearch.trim()}”. Try a different search.</p>
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
