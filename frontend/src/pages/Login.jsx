import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function Login({ onSubmit }) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event) { event.preventDefault(); setError(''); setBusy(true); try { await onSubmit(email, password) } catch (err) { setError(err.message) } finally { setBusy(false) } }
  return <section className="auth-layout"><div className="auth-aside"><span className="eyebrow">A LITTLE MORE PEACE OF MIND</span><h1>Your vehicle’s story, all in one place.</h1><p>Keep track of every service, every rupee, and the next time your vehicle needs a little care.</p><div className="aside-note"><span>✳</span> Good care starts with a good record.</div></div><div className="auth-card"><span className="eyebrow">WELCOME BACK</span><h2>Log in to your garage</h2><p className="muted">Pick up right where you left off.</p>{error && <p className="error-banner">{error}</p>}<form onSubmit={submit}><label>Email<input required type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label><label>Password<input required type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} /></label><button className="button primary full" disabled={busy}>{busy ? 'Logging in…' : 'Log in'} <span>→</span></button></form><p className="auth-switch">New around here? <Link to="/register">Create an account</Link></p></div></section>
}
