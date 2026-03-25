import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Fan, Bell, LogOut, Activity } from 'lucide-react';
import { api } from '../services/api';

export default function Layout({ children, onLogout, user }) {
  const initials = user?.email ? user.email.substring(0, 2).toUpperCase() : 'WS';
  const [activeCount, setActiveCount] = useState(0);
  const location = useLocation();

  useEffect(() => {
    api.getAlertStats().then(res => setActiveCount(Number(res.data?.active_alerts || 0))).catch(() => {});
  }, []);

  const tabs = [
    { path: '/', label: 'Dashboard' },
    { path: '/turbines', label: 'Türbinler' },
    { path: '/alerts', label: 'Alarmlar' },
  ];

  return (
    <div className="app-layout">
      {/* Top Nav */}
      <header className="topbar">
        <div className="topbar-logo">
          <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
            <rect x="14.5" y="14" width="3" height="14" rx="1.5" fill="#2563eb" opacity="0.9"/>
            <g className="spinning" style={{'--spd': '4s'}}>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.9" transform="rotate(0,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.6" transform="rotate(120,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.6" transform="rotate(240,16,13)"/>
            </g>
            <circle cx="16" cy="13" r="2.5" fill="#2563eb"/>
            <circle cx="16" cy="13" r="1.2" fill="white"/>
          </svg>
          <div>
            <div className="topbar-logo-text">WIND <span>SENTINEL</span></div>
            <div className="topbar-logo-sub">Erken Arıza Tespit Sistemi</div>
          </div>
        </div>

        <div className="topbar-center">
          {tabs.map(t => (
            <NavLink key={t.path} to={t.path} end={t.path === '/'} className={() => `topbar-tab ${location.pathname === t.path || (t.path !== '/' && location.pathname.startsWith(t.path)) ? 'active' : ''}`}>
              {t.label}
            </NavLink>
          ))}
        </div>

        <div className="topbar-right">
          <div className="status-pill">
            <span className="pulse-dot"></span>
            CANLI
          </div>
          <button className="topbar-btn" title="Bildirimler">
            <Bell size={16} />
            {activeCount > 0 && <span className="dot"></span>}
          </button>
          <div className="topbar-avatar" onClick={onLogout} title="Çıkış Yap">
            {initials}
          </div>
        </div>
      </header>

      <div className="main-wrapper">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-label">İzleme</div>
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><LayoutDashboard size={15} /> Kontrol Paneli</span>
          </NavLink>
          <NavLink to="/turbines" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><Fan size={15} /> Türbinler</span>
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><AlertTriangle size={15} /> Alarmlar</span>
            {activeCount > 0 && <span className="sidebar-badge">{activeCount}</span>}
          </NavLink>

          <div className="sidebar-divider"></div>
          <div className="sidebar-label">Sistem</div>
          <NavLink to="/alerts" className="sidebar-link">
            <span className="sidebar-link-left"><Activity size={15} /> Sistem Durumu</span>
          </NavLink>

          <div style={{ marginTop: 'auto' }}>
            <div className="sidebar-divider"></div>
            <button onClick={onLogout} className="sidebar-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', color: 'var(--muted)' }}>
              <span className="sidebar-link-left"><LogOut size={15} /> Çıkış Yap</span>
            </button>
          </div>
        </aside>

        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
