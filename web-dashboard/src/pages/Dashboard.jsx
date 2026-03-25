import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Az once';
  if (mins < 60) return `${mins} dk once`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} saat once`;
  return `${Math.floor(hours / 24)} gun once`;
}

function RiskChart({ alerts }) {
  const points = alerts.length > 0
    ? alerts.slice(0, 8).reverse().map((a, i) => ({
        x: 50 + i * 72,
        y: 155 - Math.round(a.anomaly_score * 140),
        score: Math.round(a.anomaly_score * 100),
      }))
    : Array.from({ length: 8 }, (_, i) => ({ x: 50 + i * 72, y: 120 - Math.sin(i * 0.7) * 30 }));

  const linePoints = points.map(p => `${p.x},${p.y}`).join(' ');
  const areaPath = `M${points[0].x},${points[0].y} ${points.map(p => `L${p.x},${p.y}`).join(' ')} L${points[points.length-1].x},160 L${points[0].x},160 Z`;

  return (
    <svg viewBox="0 0 600 165" style={{ width: '100%', height: '100%' }}>
      <defs>
        <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.1" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.01" />
        </linearGradient>
      </defs>
      {[0, 40, 80, 120, 160].map(y => (
        <line key={y} x1="40" y1={y} x2="575" y2={y} stroke="#e2e6ee" strokeWidth="0.5" />
      ))}
      {['100', '75', '50', '25', '0'].map((l, i) => (
        <text key={l} x="34" y={i * 40 + 5} fontSize="9" fill="#94a3b8" textAnchor="end" fontFamily="JetBrains Mono">{l}</text>
      ))}
      <path d={areaPath} fill="url(#cg)" />
      <polyline points={linePoints} fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3.5" fill="white" stroke="#2563eb" strokeWidth="1.5" />
          {p.score !== undefined && (
            <text x={p.x} y={p.y - 9} fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="600" fontFamily="JetBrains Mono">{p.score}</text>
          )}
        </g>
      ))}
    </svg>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [turbines, setTurbines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [s, t, a] = await Promise.all([
          api.getAlertStats(),
          api.getTurbines(),
          api.getAlerts({ limit: 8, sort: 'created_at_desc' }),
        ]);
        setStats(s.data);
        setTurbines(t.data);
        setAlerts(a.data);
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    }
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, []);

  if (loading) return <div className="empty-state"><Activity size={20} /><div style={{ marginTop: 8 }}>Yukleniyor...</div></div>;

  const onlineCount = turbines.filter(t => t.status === 'online').length;
  const activeAlerts = Number(stats?.active_alerts || 0);
  const resolvedAlerts = Number(stats?.resolved_alerts || 0);
  const totalAlerts = Number(stats?.total_alerts || 0);
  const affectedTurbines = Number(stats?.affected_turbines || 0);
  const resolutionRate = totalAlerts > 0 ? Math.round((resolvedAlerts / totalAlerts) * 100) : 100;
  const avgRisk = activeAlerts > 0
    ? Math.round(alerts.filter(a => a.status === 'active').reduce((s, a) => s + a.anomaly_score, 0) / activeAlerts * 100)
    : 0;

  return (
    <>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <div className="page-title">Kontrol Paneli</div>
            <div className="page-sub">Wind Farm A - Gercek zamanli izleme</div>
          </div>
          <div className="flex gap-2">
            <span className="btn btn-ghost btn-sm">Son 24 Saat</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-row">
        <div className="stat-card blue">
          <div className="stat-label">Aktif Turbin</div>
          <div className="stat-value blue">{onlineCount}<span style={{ fontSize: '0.7em', color: 'var(--muted)' }}>/{turbines.length}</span></div>
          <div className="stat-sub">{turbines.length - onlineCount === 0 ? 'Tumu aktif' : `${turbines.length - onlineCount} devre disi`}</div>
        </div>

        <div className="stat-card green">
          <div className="stat-label">Cozum Orani</div>
          <div className="stat-value green">{resolutionRate}%</div>
          <div className="stat-sub">{resolvedAlerts}/{totalAlerts} cozuldu</div>
        </div>

        <div className="stat-card amber">
          <div className="stat-label">Ort. Risk Skoru</div>
          <div className="stat-value amber">{avgRisk}</div>
          <div className="stat-sub">/100 puan</div>
        </div>

        <div className="stat-card red">
          <div className="stat-label">Aktif Alarm</div>
          <div className="stat-value red">{activeAlerts}</div>
          <div className="stat-sub">{affectedTurbines} turbin etkilendi</div>
        </div>
      </div>

      {/* Chart + Alarms */}
      <div className="grid-2-wide mb-3">
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Risk Skoru Trendi</span>
            <div className="flex gap-2">
              <span className="btn btn-filter btn-sm active" style={{ fontSize: '10px' }}>24S</span>
              <span className="btn btn-filter btn-sm" style={{ fontSize: '10px' }}>7G</span>
            </div>
          </div>
          <div className="panel-body">
            <div className="chart-area">
              <RiskChart alerts={alerts} />
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Son Alarmlar</span>
            <Link to="/alerts" className="btn btn-ghost btn-sm">Tumu <ArrowRight size={12} /></Link>
          </div>
          <div className="alarm-list">
            {alerts.length === 0 ? (
              <div className="empty-state"><ShieldCheck size={18} /><div style={{ marginTop: 6 }}>Aktif alarm yok</div></div>
            ) : (
              alerts.slice(0, 5).map(a => {
                const score = Math.round(a.anomaly_score * 100);
                const severity = score > 85 ? 'crit' : score > 60 ? 'warn' : 'info';
                const dotColor = severity === 'crit' ? 'var(--red)' : severity === 'warn' ? 'var(--amber)' : 'var(--accent)';
                return (
                  <div key={a.id} className="alarm-item">
                    <div className="alarm-dot" style={{ background: dotColor }}></div>
                    <div className="alarm-info">
                      <div className="alarm-title">{a.turbine_id} - {a.anomaly_type}</div>
                      <div className="alarm-meta">Skor: {score} | {timeAgo(a.created_at)}</div>
                    </div>
                    <span className={`alarm-badge ${severity}`}>
                      {severity === 'crit' ? 'Kritik' : severity === 'warn' ? 'Uyari' : 'Bilgi'}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Turbine Grid */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Turbin Durumu</span>
          <Link to="/turbines" className="btn btn-ghost btn-sm">Tumu <ArrowRight size={12} /></Link>
        </div>
        <div className="panel-body">
          <div className="turbine-grid">
            {turbines.map(t => {
              const alertCount = Number(t.active_alerts);
              const turbineAlerts = alerts.filter(a => a.turbine_id === t.turbine_id && a.status === 'active');
              const riskScore = turbineAlerts.length > 0
                ? Math.round(turbineAlerts.reduce((s, a) => s + a.anomaly_score, 0) / turbineAlerts.length * 100)
                : 0;
              const riskClass = riskScore >= 70 ? 'high' : riskScore >= 30 ? 'med' : 'low';
              const cardClass = riskScore >= 70 ? 'critical' : riskScore >= 30 ? 'warning' : '';
              const dotClass = riskScore >= 70 ? 'dot-crit' : riskScore >= 30 ? 'dot-warn' : 'dot-ok';

              return (
                <Link key={t.turbine_id} to={`/turbines/${t.turbine_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <div className={`turbine-card ${cardClass}`}>
                    <div className="turbine-top">
                      <span className="turbine-id">{t.turbine_id}</span>
                      <div className={`turbine-status-dot ${dotClass}`}></div>
                    </div>
                    <div className="risk-label">Risk Skoru: {riskScore}/100</div>
                    <div className="risk-bar">
                      <div className={`risk-fill ${riskClass}`} style={{ width: `${Math.max(riskScore, 3)}%` }}></div>
                    </div>
                    <div className="turbine-metrics">
                      <div className="t-metric">
                        <div className="t-metric-val">{alertCount}</div>
                        <div className="t-metric-lbl">Alarm</div>
                      </div>
                      <div className="t-metric">
                        <div className="t-metric-val">{t.farm_name?.replace('Wind Farm ', '') || 'A'}</div>
                        <div className="t-metric-lbl">Farm</div>
                      </div>
                      <div className="t-metric">
                        <div className="t-metric-val">{t.status === 'online' ? 'ON' : 'OFF'}</div>
                        <div className="t-metric-lbl">Durum</div>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
