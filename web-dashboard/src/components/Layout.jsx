import { NavLink } from 'react-router-dom';
import { Wind, LayoutDashboard, AlertTriangle, Fan, LogOut, User } from 'lucide-react';

export default function Layout({ children, onLogout, user }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Wind size={24} color="var(--cyan)" />
          Wind<span>Sentinel</span>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} /> Dashboard
          </NavLink>
          <NavLink to="/turbines" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <Fan size={18} /> Turbines
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <AlertTriangle size={18} /> Alerts
          </NavLink>
        </nav>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
          <div className="flex items-center gap-2" style={{ marginBottom: '0.75rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--blue-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={16} color="var(--blue)" />
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{user?.email?.split('@')[0]}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{user?.email}</div>
            </div>
          </div>
          <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'center' }} onClick={onLogout}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
