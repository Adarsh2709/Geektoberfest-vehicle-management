import { Link } from 'react-router-dom'
import VehicleForm from '../components/VehicleForm'

export default function AddVehicle() {
  return <><Link className="back-link" to="/">← Back to garage</Link><section className="form-page"><span className="eyebrow">YOUR GARAGE</span><h1>Add a vehicle</h1><p className="muted">Start with the basics. You can update these details anytime.</p><VehicleForm /></section></>
}
