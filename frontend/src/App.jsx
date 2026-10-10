import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api, clearToken, token } from './api'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AddVehicle from './pages/AddVehicle'
import VehicleDetails from './pages/VehicleDetails'

export default function App() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(Boolean(token()))
  const navigate = useNavigate()

  useEffect(() => {
    if (!token()) return
    api('/auth/me').then(setUser).catch(() => clearToken()).finally(() => setChecking(false))
  }, [])

  async function signIn(email, password) {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    localStorage.setItem('vmi_token', result.access_token)
    setUser(await api('/auth/me'))
    navigate('/')
  }

  async function signUp(username, email, password) {
    await api('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) })
    await signIn(email, password)
  }

  function signOut() { clearToken(); setUser(null); navigate('/login') }
  if (checking) return <div className="loading">Loading your garage…</div>

  return <>
    <Navbar user={user} onLogout={signOut} />
    <main className="page-shell">
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <Login onSubmit={signIn} />} />
        <Route path="/register" element={user ? <Navigate to="/" /> : <Register onSubmit={signUp} />} />
        <Route path="/" element={user ? <Dashboard /> : <Navigate to="/login" />} />
        <Route path="/vehicles/new" element={user ? <AddVehicle /> : <Navigate to="/login" />} />
        <Route path="/vehicles/:id" element={user ? <VehicleDetails /> : <Navigate to="/login" />} />
        <Route path="*" element={<Navigate to={user ? '/' : '/login'} />} />
      </Routes>
    </main>
  </>
}
