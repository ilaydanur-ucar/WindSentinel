import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Fan, LogOut, Bell, Settings, Search } from 'lucide-react';

export default function Layout({ children, onLogout, user }) {
  const initials = user?.email ? user.email.substring(0, 2).toUpperCase() : 'WS';

  return (
    <div className="app-layout">
      {/* Top Bar */}
      <header className="topbar">
        <div className="topbar-logo">
          <img src="/favicon.svg" alt="WindSentinel" />
          <div className="topbar-logo-text">
            <h1>WIND Sentinel</h1>
            <span>Erken Ariza Tespit Sistemi</span>
          </div>
        </div>

        <div className="topbar-search">
          <Search size={16} className="topbar-search-icon" />
          <input type="text" placeholder="Turbin ara..." />
        </div>

        <div className="topbar-actions">
          <button className="topbar-btn">
            <Bell size={18} />
            <span className="dot"></span>
          </button>
          <button className="topbar-btn">
            <Settings size={18} />
          </button>
          <div className="topbar-avatar" onClick={onLogout} title="Cikis Yap">
            {initials}
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={18} /> Kontrol Paneli
          </NavLink>
          <NavLink to="/turbines" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <Fan size={18} /> Turbinler
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <AlertTriangle size={18} /> Alarmlar
          </NavLink>
        </nav>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
