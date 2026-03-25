import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Fan, Bell, LogOut, Activity, X } from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../hooks/useLanguage';

function timeAgo(dateStr, t) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t('justNow');
  if (mins < 60) return `${mins} ${t('minutesAgo')}`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ${t('hoursAgo')}`;
  return `${Math.floor(hours / 24)} ${t('daysAgo')}`;
}

export default function Layout({ children, onLogout, user }) {
  const { lang, setLang, t } = useLanguage();
  const initials = user?.email ? user.email.substring(0, 2).toUpperCase() : 'WS';
  const [activeCount, setActiveCount] = useState(0);
  const [alerts, setAlerts] = useState([]);
  const [showNotif, setShowNotif] = useState(false);
  const location = useLocation();

  useEffect(() => {
    api.getAlertStats().then(res => setActiveCount(Number(res.data?.active_alerts || 0))).catch(() => {});
    api.getAlerts({ limit: 5, sort: 'created_at_desc' }).then(res => setAlerts(res.data || [])).catch(() => {});
  }, []);

  const tabs = [
    { path: '/', label: t('dashboard') },
    { path: '/turbines', label: t('turbines') },
    { path: '/alerts', label: t('alarms') },
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
            <div className="topbar-logo-sub">{t('subtitle')}</div>
          </div>
        </div>

        <div className="topbar-center">
          {tabs.map(tab => (
            <NavLink key={tab.path} to={tab.path} end={tab.path === '/'} className={() => `topbar-tab ${location.pathname === tab.path || (tab.path !== '/' && location.pathname.startsWith(tab.path)) ? 'active' : ''}`}>
              {tab.label}
            </NavLink>
          ))}
        </div>

        <div className="topbar-right">
          <div className="status-pill">
            <span className="pulse-dot"></span>
            {t('live')} · {activeCount > 0 ? `${activeCount} ${t('alarm')}` : 'OK'}
          </div>

          {/* Dil Butonu */}
          <button
            className="topbar-btn"
            onClick={() => setLang(lang === 'tr' ? 'en' : 'tr')}
            title={lang === 'tr' ? 'Switch to English' : 'Türkçeye geç'}
            style={{ fontSize: '13px', fontWeight: 700, width: 'auto', padding: '0 8px', gap: '4px' }}
          >
            {lang === 'tr' ? '🇹🇷' : '🇬🇧'}
            <span style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace" }}>
              {lang.toUpperCase()}
            </span>
          </button>

          {/* Bildirim Butonu */}
          <div style={{ position: 'relative' }}>
            <button className="topbar-btn" title={t('alarms')} onClick={() => setShowNotif(!showNotif)}>
              <Bell size={16} />
              {activeCount > 0 && <span className="dot"></span>}
            </button>

            {showNotif && (
              <div className="notif-dropdown">
                <div className="notif-header">
                  <span style={{ fontWeight: 600, fontSize: '12.5px' }}>{t('activeAlarms')}</span>
                  <button onClick={() => setShowNotif(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}>
                    <X size={14} />
                  </button>
                </div>
                {alerts.length === 0 ? (
                  <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--muted)', fontSize: '12.5px' }}>
                    {t('noActiveAlarm')}
                  </div>
                ) : (
                  alerts.map(a => {
                    const score = Math.round(a.anomaly_score * 100);
                    const dotColor = score > 85 ? 'var(--red)' : score > 60 ? 'var(--amber)' : 'var(--accent)';
                    return (
                      <div key={a.id} className="notif-item">
                        <div className="alarm-dot" style={{ background: dotColor, marginTop: '4px' }}></div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '12.5px', fontWeight: 500 }}>{a.turbine_id} — {a.anomaly_type}</div>
                          <div style={{ fontSize: '10.5px', color: 'var(--muted)', fontFamily: "'JetBrains Mono', monospace", marginTop: '1px' }}>
                            {t('score')}: {score} · {timeAgo(a.created_at, t)}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <NavLink to="/alerts" onClick={() => setShowNotif(false)} className="notif-footer">
                  {t('all')} {t('alarms').toLowerCase()} →
                </NavLink>
              </div>
            )}
          </div>

          <div className="topbar-avatar" onClick={onLogout} title={t('logout')}>
            {initials}
          </div>
        </div>
      </header>

      <div className="main-wrapper">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-label">{t('monitoring')}</div>
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><LayoutDashboard size={15} /> {t('dashboard')}</span>
          </NavLink>
          <NavLink to="/turbines" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><Fan size={15} /> {t('turbines')}</span>
          </NavLink>
          <NavLink to="/alerts" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <span className="sidebar-link-left"><AlertTriangle size={15} /> {t('alarms')}</span>
            {activeCount > 0 && <span className="sidebar-badge">{activeCount}</span>}
          </NavLink>

          <div className="sidebar-divider"></div>
          <div className="sidebar-label">{t('system')}</div>
          <NavLink to="/alerts" className="sidebar-link">
            <span className="sidebar-link-left"><Activity size={15} /> {t('systemStatus')}</span>
          </NavLink>

          <div style={{ marginTop: 'auto' }}>
            <div className="sidebar-divider"></div>
            <button onClick={onLogout} className="sidebar-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: '13px', color: 'var(--muted)' }}>
              <span className="sidebar-link-left"><LogOut size={15} /> {t('logout')}</span>
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
