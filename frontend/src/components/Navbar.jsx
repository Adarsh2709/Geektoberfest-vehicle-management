import { Link } from 'react-router-dom'

export default function Navbar({ user, onLogout }) {
  return <header className="topbar"><Link className="brand" to="/"> <span className="brand-mark">V</span><span>Vehicle <b>Index</b></span></Link>
    <div className="nav-right">{user ? <><span className="welcome">Welcome, {user.username}</span><button className="text-button" onClick={onLogout}>Log out</button></> : <><Link to="/login">Log in</Link><Link className="nav-cta" to="/register">Create account</Link></>}</div>
  </header>
}
