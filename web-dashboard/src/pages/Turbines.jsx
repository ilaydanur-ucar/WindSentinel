import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Fan, ArrowLeft, AlertTriangle, CheckCircle, Activity } from 'lucide-react';
import { api } from '../services/api';

export function TurbineList() {
  const [turbines, setTurbines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTurbines().then((res) => { setTurbines(res.data); setLoading(false); });
  }, []);

  if (loading) return <div className="text-muted">Loading...</div>;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Turbines</h1>
        <p className="page-subtitle">Wind Farm A fleet overview</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
        {turbines.map((t) => {
          const alerts = Number(t.active_alerts);
          const health = alerts === 0 ? 100 : alerts < 3 ? 60 : 20;
          const healthColor = health > 80 ? 'var(--green)' : health > 40 ? 'var(--amber)' : 'var(--red)';

          return (
            <Link to={`/turbines/${t.turbine_id}`} key={t.turbine_id} style={{ textDecoration: 'none' }}>
              <div className="turbine-card">
                <div className="flex items-center gap-3" style={{ marginBottom: '1.25rem' }}>
                  <div className="stat-icon cyan"><Fan size={22} /></div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{t.turbine_id}</div>
                    <div className="text-muted text-sm">{t.farm_name} - Asset {t.asset_id}</div>
                  </div>
                  <span className={`badge badge-${t.status}`} style={{ marginLeft: 'auto' }}>{t.status}</span>
                </div>

                <div className="flex gap-4">
                  <div style={{ flex: 1 }}>
                    <div className="stat-label">Health</div>
                    <div className="flex items-center gap-2 mt-2">
                      <div className="score-bar" style={{ flex: 1 }}>
                        <div className="score-fill" style={{ width: `${health}%`, background: healthColor }}></div>
                      </div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: healthColor }}>{health}%</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div className="stat-label">Alerts</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: alerts > 0 ? 'var(--red-light)' : 'var(--text-dim)', marginTop: '0.25rem' }}>
                      {alerts}
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}

export function TurbineDetail() {
  const { turbineId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTurbine(turbineId).then((res) => { setData(res.data); setLoading(false); }).catch(() => navigate('/turbines'));
  }, [turbineId, navigate]);

  if (loading) return <div className="text-muted">Loading...</div>;
  const { turbine, alerts, stats } = data;

  return (
    <>
      <div className="page-header">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/turbines')} style={{ marginBottom: '1rem' }}>
          <ArrowLeft size={16} /> Back to Fleet
        </button>
        <div className="flex items-center gap-3">
          <div className="stat-icon cyan" style={{ width: 48, height: 48 }}><Fan size={26} /></div>
          <div>
            <h1 className="page-title">{turbine.turbine_id}</h1>
            <p className="page-subtitle">{turbine.farm_name} - Asset ID: {turbine.asset_id}</p>
          </div>
          <span className={`badge badge-${turbine.status}`} style={{ marginLeft: '1rem', fontSize: '0.85rem' }}>{turbine.status}</span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card red">
          <div className="stat-icon red"><AlertTriangle size={18} /></div>
          <div className="stat-label">Active Alerts</div>
          <div className="stat-value" style={{ color: 'var(--red-light)' }}>{stats.active_count}</div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon green"><CheckCircle size={18} /></div>
          <div className="stat-label">Resolved</div>
          <div className="stat-value" style={{ color: 'var(--emerald)' }}>{stats.resolved_count}</div>
        </div>
        <div className="stat-card purple">
          <div className="stat-icon purple"><Activity size={18} /></div>
          <div className="stat-label">Total Events</div>
          <div className="stat-value" style={{ color: 'var(--purple)' }}>{stats.total_count}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><AlertTriangle size={16} /> Alert History</h3>
        </div>
        <table className="table">
          <thead>
            <tr><th>Type</th><th>Score</th><th>Confidence</th><th>Status</th><th>Detected</th></tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>No alerts recorded</td></tr>
            ) : alerts.map((a) => {
              const score = a.anomaly_score * 100;
              const scoreColor = score > 85 ? 'var(--red)' : score > 60 ? 'var(--amber)' : 'var(--blue)';
              return (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.anomaly_type}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="score-bar" style={{ width: 50 }}>
                        <div className="score-fill" style={{ width: `${score}%`, background: scoreColor }}></div>
                      </div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: scoreColor }}>{score.toFixed(0)}%</span>
                    </div>
                  </td>
                  <td>{(a.confidence * 100).toFixed(0)}%</td>
                  <td><span className={`badge badge-${a.status}`}>{a.status}</span></td>
                  <td className="text-muted text-sm">{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
