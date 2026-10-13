import { useState } from 'react'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'

export default function VehicleForm({ initial = {}, vehicleId, onSaved }) {
  const [form, setForm] = useState({
    make: '',
    model: '',
    year: new Date().getFullYear(),
    registration_number: '',
    current_mileage: 0,
    next_service_date: '',
    next_service_mileage: '',
    ...initial,
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()
  function change(event) { setForm({ ...form, [event.target.name]: event.target.value }) }
  async function submit(event) {
    event.preventDefault(); setError(''); setSaving(true)
    try {
      const path = vehicleId ? `/vehicles/${vehicleId}` : '/vehicles'
      await api(path, {
        method: vehicleId ? 'PUT' : 'POST',
        body: JSON.stringify({
          ...form,
          year: Number(form.year),
          current_mileage: Number(form.current_mileage || 0),
          next_service_date: form.next_service_date || null,
          next_service_mileage: form.next_service_mileage === '' || form.next_service_mileage == null ? null : Number(form.next_service_mileage),
        }),
      })
      if (onSaved) await onSaved()
      else navigate(vehicleId ? `/vehicles/${vehicleId}` : '/')
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }
  return <form className="form-card" onSubmit={submit}>
    {error && <p className="error-banner">{error}</p>}
    <label>Make<input required maxLength="100" name="make" value={form.make} onChange={change} placeholder="e.g. Honda" /></label>
    <label>Model<input required maxLength="100" name="model" value={form.model} onChange={change} placeholder="e.g. City" /></label>
    <div className="form-row"><label>Year<input required type="number" min="1886" max="2100" name="year" value={form.year} onChange={change} /></label><label>Current mileage (km)<input required type="number" min="0" name="current_mileage" value={form.current_mileage} onChange={change} /></label></div>
    <label>Registration number<input required maxLength="30" name="registration_number" value={form.registration_number} onChange={change} placeholder="e.g. KA01AB1234" /></label>
    <div className="form-row">
      <label>Next service date threshold <span className="optional">(optional)</span><input type="date" name="next_service_date" value={form.next_service_date || ''} onChange={change} /></label>
      <label>Next service mileage threshold <span className="optional">(optional, km)</span><input type="number" min="0" name="next_service_mileage" value={form.next_service_mileage ?? ''} onChange={change} placeholder="e.g. 10000" /></label>
    </div>
    <div className="form-actions"><button type="button" className="button secondary" onClick={() => navigate(-1)}>Cancel</button><button className="button primary" disabled={saving}>{saving ? 'Saving…' : vehicleId ? 'Save changes' : 'Add vehicle'}</button></div>
  </form>
}
