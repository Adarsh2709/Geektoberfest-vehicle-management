import { useState } from 'react'
import { api } from '../api'

const blank = { service_date: new Date().toISOString().slice(0, 10), mileage: '', service_type: 'Oil Change', description: '', cost: '', next_service_date: '', next_service_mileage: '' }
export default function MaintenanceForm({ vehicleId, record, onSaved, onCancel }) {
  const [form, setForm] = useState(record ? { ...record, mileage: String(record.mileage), cost: String(record.cost), next_service_mileage: record.next_service_mileage ?? '' } : blank)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  function change(event) { setForm({ ...form, [event.target.name]: event.target.value }) }
  async function submit(event) {
    event.preventDefault(); setError(''); setSaving(true)
    const payload = { ...form, mileage: Number(form.mileage), cost: Number(form.cost), next_service_date: form.next_service_date || null, next_service_mileage: form.next_service_mileage === '' ? null : Number(form.next_service_mileage), description: form.description || null }
    try {
      await api(record ? `/maintenance/${record.id}` : `/vehicles/${vehicleId}/maintenance`, { method: record ? 'PUT' : 'POST', body: JSON.stringify(payload) })
      await onSaved()
    } catch (err) { setError(err.message) } finally { setSaving(false) }
  }
  return <form className="maintenance-form" onSubmit={submit}>{error && <p className="error-banner">{error}</p>}
    <div className="form-row"><label>Service date<input required type="date" name="service_date" value={form.service_date} onChange={change} /></label><label>Mileage (km)<input required type="number" min="0" name="mileage" value={form.mileage} onChange={change} /></label></div>
    <div className="form-row"><label>Service type<select name="service_type" value={form.service_type} onChange={change}>{['Oil Change', 'General Service', 'Brake Service', 'Tire Change', 'Battery', 'Other'].map(item => <option key={item}>{item}</option>)}</select></label><label>Cost (₹)<input required type="number" min="0" step="0.01" name="cost" value={form.cost} onChange={change} /></label></div>
    <label>Description <span className="optional">(optional)</span><textarea rows="2" maxLength="2000" name="description" value={form.description || ''} onChange={change} placeholder="What was done?" /></label>
    <div className="form-row"><label>Next service date <span className="optional">(optional)</span><input type="date" name="next_service_date" value={form.next_service_date || ''} onChange={change} /></label><label>Next service mileage <span className="optional">(optional)</span><input type="number" min="0" name="next_service_mileage" value={form.next_service_mileage ?? ''} onChange={change} /></label></div>
    <div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" disabled={saving}>{saving ? 'Saving…' : record ? 'Save changes' : 'Save service'}</button></div>
  </form>
}
