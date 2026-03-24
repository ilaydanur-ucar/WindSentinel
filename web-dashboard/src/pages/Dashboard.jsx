import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Fan, Zap, AlertTriangle, Thermometer, Wind, ArrowRight, Clock, TrendingUp, Activity } from 'lucide-react';
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
          api.getAlerts({ limit: 6, sort: 'created_at_desc' }),
        ]);
        setStats(s.data);
        setTurbines(t.data);
        setAlerts(a.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, []);

  if (loading) return <div className="text-muted" style={{ padding: '2rem' }}>Yukleniyor...</div>;

  const onlineCount = turbines.filter(t => t.status === 'online').length;
  const totalAlerts = Number(stats?.total_alerts || 0);
  const activeAlerts = Number(stats?.active_alerts || 0);
  const resolvedAlerts = Number(stats?.resolved_alerts || 0);
  const affectedTurbines = Number(stats?.affected_turbines || 0);

  return (
    <>
      {/* Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div>
            <div className="stat-label">Aktif Turbin</div>
            <div className="stat-value">{onlineCount}/{turbines.length}</div>
            <div className="stat-sub">{turbines.length - onlineCount} devre disi</div>
          </div>
          <div className="stat-icon navy"><Fan size={20} /></div>
        </div>

        <div className="stat-card highlight-green">
          <div>
            <div className="stat-label">Toplam Guc</div>
            <div className="stat-value">-</div>
            <div className="stat-sub">MW uretim</div>
          </div>
          <div className="stat-icon green"><Zap size={20} /></div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-label">Ort. Risk</div>
            <div className="stat-value">{activeAlerts > 0 ? Math.round((activeAlerts / turbines.length) * 100) : 0}</div>
            <div className="stat-sub">Skoru /100</div>
          </div>
          <div className="stat-icon amber"><TrendingUp size={20} /></div>
        </div>

        <div className="stat-card highlight-red">
          <div>
            <div className="stat-label">Kritik Alarm</div>
            <div className="stat-value">{activeAlerts}</div>
            <div className="stat-sub">Son 24 saat</div>
          </div>
          <div className="stat-icon red"><AlertTriangle size={20} /></div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-label">Etkilenen</div>
            <div className="stat-value">{affectedTurbines}</div>
            <div className="stat-sub">Turbin</div>
          </div>
          <div className="stat-icon amber"><Activity size={20} /></div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-label">Ruzgar Hizi</div>
            <div className="stat-value">-</div>
            <div className="stat-sub">m/s ortalama</div>
          </div>
          <div className="stat-icon blue"><Wind size={20} /></div>
        </div>
      </div>

      {/* Chart + Recent Alerts */}
      <div className="grid-2 mb-4">
        {/* Chart Area */}
        <div className="card">
          <div className="card-title">Risk Skoru Trendi</div>
          <div className="card-subtitle">Son alarmlar - Wind Farm A</div>
          <div className="chart-area" style={{ marginTop: '1rem' }}>
            <svg viewBox="0 0 600 180" style={{ width: '100%', height: '100%' }}>
              {/* Grid lines */}
              {[0, 45, 90, 135, 180].map(y => (
                <line key={y} x1="40" y1={y} x2="580" y2={y} stroke="#e5e7eb" strokeWidth="0.5" />
              ))}
              {/* Y axis labels */}
              <text x="30" y="8" fontSize="10" fill="#9ca3af" textAnchor="end">100</text>
              <text x="30" y="48" fontSize="10" fill="#9ca3af" textAnchor="end">75</text>
              <text x="30" y="93" fontSize="10" fill="#9ca3af" textAnchor="end">50</text>
              <text x="30" y="138" fontSize="10" fill="#9ca3af" textAnchor="end">25</text>
              <text x="30" y="178" fontSize="10" fill="#9ca3af" textAnchor="end">0</text>
              {/* Area fill */}
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3182ce" stopOpacity="0.15" />
                  <stop offset="100%" stopColor="#3182ce" stopOpacity="0.01" />
                </linearGradient>
              </defs>
              <path d="M60,160 L120,150 L180,140 L240,110 L300,90 L360,70 L420,65 L480,80 L540,120 L540,180 L60,180 Z" fill="url(#areaGrad)" />
              {/* Line */}
              <polyline
                points="60,160 120,150 180,140 240,110 300,90 360,70 420,65 480,80 540,120"
                fill="none" stroke="#3182ce" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              />
              {/* Dots */}
              {[[60,160],[120,150],[180,140],[240,110],[300,90],[360,70],[420,65],[480,80],[540,120]].map(([x,y],i) => (
                <circle key={i} cx={x} cy={y} r="3" fill="#3182ce" />
              ))}
              {/* X axis labels */}
              {['00:00','03:00','06:00','09:00','12:00','15:00','18:00','21:00','24:00'].map((label,i) => (
                <text key={label} x={60 + i * 60} y="178" fontSize="9" fill="#9ca3af" textAnchor="middle">{label}</text>
              ))}
            </svg>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Son Alarmlar</div>
              <div className="card-subtitle">AI destekli erken uyarilar</div>
            </div>
            <Link to="/alerts" className="btn btn-ghost btn-sm">Tumunu gor <ArrowRight size={14} /></Link>
          </div>
          <div>
            {alerts.length === 0 ? (
              <div className="text-muted" style={{ textAlign: 'center', padding: '2rem' }}>Alarm yok - Sistem saglam</div>
            ) : (
              alerts.map((a) => (
                <div key={a.id} className="alert-item">
                  <div className="alert-item-icon">
                    <AlertTriangle size={14} color="#d97706" />
                  </div>
                  <div className="alert-item-content">
                    <div className="alert-item-title">{a.turbine_id}</div>
                    <div className="alert-item-desc">{a.anomaly_type}</div>
                  </div>
                  <div className="alert-item-time">
                    <Clock size={12} /> {timeAgo(a.created_at)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Turbine Status Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Turbin Durumlari</div>
            <div className="card-subtitle">Gercek zamanli izleme verileri</div>
          </div>
          <Link to="/turbines" className="btn btn-ghost btn-sm">Tumu <ArrowRight size={14} /></Link>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Turbin</th>
              <th>Durum</th>
              <th>Risk Skoru</th>
              <th>Aktif Alert</th>
              <th>Cozulen</th>
              <th>Toplam</th>
            </tr>
          </thead>
          <tbody>
            {turbines.map((t) => {
              const alertCount = Number(t.active_alerts);
              const riskScore = alertCount === 0 ? 0 : alertCount < 2 ? 35 : alertCount < 4 ? 67 : 89;
              const riskClass = riskScore < 30 ? 'risk-low' : riskScore < 60 ? 'risk-medium' : 'risk-high';
              const statusLabel = alertCount > 3 ? 'Kritik' : alertCount > 0 ? 'Uyari' : 'Aktif';
              const statusBadge = alertCount > 3 ? 'badge-kritik' : alertCount > 0 ? 'badge-uyari' : 'badge-aktif';

              return (
                <tr key={t.turbine_id}>
                  <td>
                    <Link to={`/turbines/${t.turbine_id}`} style={{ color: 'var(--gray-800)', textDecoration: 'none' }}>
                      <div className="flex items-center gap-2">
                        <Fan size={16} color="var(--gray-400)" />
                        <div>
                          <div style={{ fontWeight: 600 }}>{t.turbine_id}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--gray-400)' }}>Asset-{t.asset_id}</div>
                        </div>
                      </div>
                    </Link>
                  </td>
                  <td><span className={`badge ${statusBadge}`}>{statusLabel}</span></td>
                  <td><span className={`risk-score ${riskClass}`}>{riskScore}</span></td>
                  <td style={{ fontWeight: 600, color: alertCount > 0 ? 'var(--red)' : 'var(--gray-300)' }}>{alertCount}</td>
                  <td className="text-muted">{resolvedAlerts}</td>
                  <td className="text-muted">{totalAlerts}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
