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
    ...initial
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

  function validate() {
    const errs = {}
    if (!form.make || !String(form.make).trim()) {
      errs.make = 'Vehicle make is required and cannot be blank.'
    }
    if (!form.model || !String(form.model).trim()) {
      errs.model = 'Vehicle model is required and cannot be blank.'
    }
    const yearNum = Number(form.year)
    if (isNaN(yearNum) || yearNum < 1886 || yearNum > 2100) {
      errs.year = 'Year must be a valid year between 1886 and 2100.'
    }
    const mileageNum = Number(form.current_mileage)
    if (isNaN(mileageNum) || mileageNum < 0) {
      errs.current_mileage = 'Current mileage must be zero or a positive number.'
    }
    if (!form.registration_number || !String(form.registration_number).trim()) {
      errs.registration_number = 'Registration number is required and cannot be blank.'
    }
    return errs
  }

  function change(event) {
    const { name, value } = event.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    const clientErrors = validate()
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors)
      setError('Please correct the invalid fields below.')
      return
    }

    setSaving(true)
    try {
      const path = vehicleId ? `/vehicles/${vehicleId}` : '/vehicles'
      await api(path, {
        method: vehicleId ? 'PUT' : 'POST',
        body: JSON.stringify({
          ...form,
          make: String(form.make).trim(),
          model: String(form.model).trim(),
          registration_number: String(form.registration_number).trim(),
          year: Number(form.year),
          current_mileage: Number(form.current_mileage)
        })
      })
      if (onSaved) await onSaved()
      else navigate(vehicleId ? `/vehicles/${vehicleId}` : '/')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="form-card" onSubmit={submit} noValidate>
      {error && <p className="error-banner">{error}</p>}
      
      <label>
        Make
        <input
          required
          maxLength="100"
          name="make"
          value={form.make}
          onChange={change}
          placeholder="e.g. Honda"
          aria-invalid={Boolean(fieldErrors.make)}
        />
        {fieldErrors.make && (
          <span style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '0.25rem', display: 'block' }}>
            {fieldErrors.make}
          </span>
        )}
      </label>

      <label>
        Model
        <input
          required
          maxLength="100"
          name="model"
          value={form.model}
          onChange={change}
          placeholder="e.g. City"
          aria-invalid={Boolean(fieldErrors.model)}
        />
        {fieldErrors.model && (
          <span style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '0.25rem', display: 'block' }}>
            {fieldErrors.model}
          </span>
        )}
      </label>

      <div className="form-row">
        <label>
          Year
          <input
            required
            type="number"
            min="1886"
            max="2100"
            name="year"
            value={form.year}
            onChange={change}
            aria-invalid={Boolean(fieldErrors.year)}
          />
          {fieldErrors.year && (
            <span style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '0.25rem', display: 'block' }}>
              {fieldErrors.year}
            </span>
          )}
        </label>

        <label>
          Current mileage (km)
          <input
            required
            type="number"
            min="0"
            name="current_mileage"
            value={form.current_mileage}
            onChange={change}
            aria-invalid={Boolean(fieldErrors.current_mileage)}
          />
          {fieldErrors.current_mileage && (
            <span style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '0.25rem', display: 'block' }}>
              {fieldErrors.current_mileage}
            </span>
          )}
        </label>
      </div>

      <label>
        Registration number
        <input
          required
          maxLength="30"
          name="registration_number"
          value={form.registration_number}
          onChange={change}
          placeholder="e.g. KA01AB1234"
          aria-invalid={Boolean(fieldErrors.registration_number)}
        />
        {fieldErrors.registration_number && (
          <span style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '0.25rem', display: 'block' }}>
            {fieldErrors.registration_number}
          </span>
        )}
      </label>

      <div className="form-actions">
        <button type="button" className="button secondary" onClick={() => navigate(-1)}>
          Cancel
        </button>
        <button className="button primary" disabled={saving}>
          {saving ? 'Saving…' : vehicleId ? 'Save changes' : 'Add vehicle'}
        </button>
      </div>
    </form>
  )
}
