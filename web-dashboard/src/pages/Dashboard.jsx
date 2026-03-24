import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, Fan, ShieldCheck,
  Zap, ArrowRight, CheckCircle, Clock, Wind

} from 'lucide-react';
import { api } from '../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [turbines, setTurbines] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, turbinesRes, alertsRes] = await Promise.all([
          api.getAlertStats(),
          api.getTurbines(),
          api.getAlerts({ limit: 5, sort: 'created_at_desc' }),
        ]);
        setStats(statsRes.data);
        setTurbines(turbinesRes.data);
        setRecentAlerts(alertsRes.data);
      } catch (err) {
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="text-muted">Loading dashboard...</div>;

  const onlineTurbines = turbines.filter(t => t.status === 'online').length;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Wind Farm A - Real-time monitoring overview</p>
      </div>

      {/* Stats Row */}
      <div className="stats-grid">
        <div className="stat-card red">
          <div className="stat-icon red"><AlertTriangle size={20} /></div>
          <div className="stat-label">Active Alerts</div>
          <div className="stat-value" style={{ color: 'var(--red-light)' }}>
            {stats?.active_alerts || 0}
          </div>
        </div>

        <div className="stat-card green">
          <div className="stat-icon green"><CheckCircle size={20} /></div>
          <div className="stat-label">Resolved</div>
          <div className="stat-value" style={{ color: 'var(--emerald)' }}>
            {stats?.resolved_alerts || 0}
          </div>
        </div>

        <div className="stat-card amber">
          <div className="stat-icon amber"><Zap size={20} /></div>
          <div className="stat-label">Affected Turbines</div>
          <div className="stat-value" style={{ color: 'var(--amber)' }}>
            {stats?.affected_turbines || 0}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}> / {turbines.length}</span>
          </div>
        </div>

        <div className="stat-card cyan">
          <div className="stat-icon cyan"><Fan size={20} /></div>
          <div className="stat-label">Turbines Online</div>
          <div className="stat-value" style={{ color: 'var(--cyan)' }}>
            {onlineTurbines}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}> / {turbines.length}</span>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Turbine Status */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><Fan size={16} /> Turbine Fleet</h3>
            <Link to="/turbines" className="btn btn-ghost btn-sm">View All <ArrowRight size={14} /></Link>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Turbine</th>
                <th>Status</th>
                <th>Alerts</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              {turbines.map((t) => {
                const alertCount = Number(t.active_alerts);
                const health = alertCount === 0 ? 100 : alertCount < 3 ? 60 : 20;
                const healthColor = health > 80 ? 'var(--green)' : health > 40 ? 'var(--amber)' : 'var(--red)';
                return (
                  <tr key={t.turbine_id}>
                    <td>
                      <Link to={`/turbines/${t.turbine_id}`} style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                        {t.turbine_id}
                      </Link>
                    </td>
                    <td><span className={`badge badge-${t.status}`}>{t.status}</span></td>
                    <td>
                      {alertCount > 0
                        ? <span className="badge badge-active">{alertCount} active</span>
                        : <span className="text-muted">-</span>}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="score-bar" style={{ width: '60px' }}>
                          <div className="score-fill" style={{ width: `${health}%`, background: healthColor }}></div>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: healthColor, fontWeight: 600 }}>{health}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Recent Alerts */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><AlertTriangle size={16} /> Recent Alerts</h3>
            <Link to="/alerts" className="btn btn-ghost btn-sm">View All <ArrowRight size={14} /></Link>
          </div>
          {recentAlerts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
              <ShieldCheck size={40} style={{ marginBottom: '0.5rem', opacity: 0.3 }} />
              <p>No alerts - System healthy</p>
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Turbine</th>
                  <th>Type</th>
                  <th>Score</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentAlerts.map((a) => {
                  const score = a.anomaly_score * 100;
                  const scoreColor = score > 85 ? 'var(--red)' : score > 60 ? 'var(--amber)' : 'var(--blue)';
                  return (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 600 }}>{a.turbine_id}</td>
                      <td style={{ fontSize: '0.8rem' }}>{a.anomaly_type}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="score-bar" style={{ width: '50px' }}>
                            <div className="score-fill" style={{ width: `${score}%`, background: scoreColor }}></div>
                          </div>
                          <span style={{ fontSize: '0.75rem', color: scoreColor, fontWeight: 600 }}>{score.toFixed(0)}%</span>
                        </div>
                      </td>
                      <td><span className={`badge badge-${a.status}`}>{a.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* System Info */}
      <div className="grid-2 mt-4">
        <div className="card">
          <div className="card-title" style={{ marginBottom: '0.75rem' }}>
            <Wind size={16} /> Farm Info
          </div>
          <div style={{ fontSize: '0.85rem' }}>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Farm</span>
              <span>Wind Farm A</span>
            </div>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Turbines</span>
              <span>{turbines.length} units</span>
            </div>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Measurement</span>
              <span>Every 10 min</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Sensors</span>
              <span>6 primary + derived</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{ marginBottom: '0.75rem' }}>
            <Clock size={16} /> Alert Summary
          </div>
          <div style={{ fontSize: '0.85rem' }}>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Total Alerts</span>
              <span style={{ fontWeight: 700 }}>{stats?.total_alerts || 0}</span>
            </div>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Active</span>
              <span style={{ color: 'var(--red-light)', fontWeight: 600 }}>{stats?.active_alerts || 0}</span>
            </div>
            <div className="flex justify-between mb-4">
              <span className="text-muted">Resolved</span>
              <span style={{ color: 'var(--green)', fontWeight: 600 }}>{stats?.resolved_alerts || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Resolution Rate</span>
              <span style={{ color: 'var(--cyan)' }}>
                {stats?.total_alerts > 0
                  ? ((stats.resolved_alerts / stats.total_alerts) * 100).toFixed(0) + '%'
                  : '-'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
