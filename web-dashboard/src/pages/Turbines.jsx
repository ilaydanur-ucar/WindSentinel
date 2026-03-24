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

  if (loading) return <div className="text-muted">Yukleniyor...</div>;

  return (
    <>
      <div className="page-header">
        <div className="page-title">Turbin Durumlari</div>
        <div className="page-subtitle">Gercek zamanli izleme verileri</div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Turbin</th>
              <th>Durum</th>
              <th>Risk Skoru</th>
              <th>Aktif Alert</th>
              <th>Farm</th>
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
                  <td className="text-muted">{t.farm_name}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
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

  if (loading) return <div className="text-muted">Yukleniyor...</div>;
  const { turbine, alerts, stats } = data;

  return (
    <>
      <div className="page-header">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/turbines')} style={{ marginBottom: '0.75rem' }}>
          <ArrowLeft size={16} /> Geri
        </button>
        <div className="flex items-center gap-3">
          <Fan size={24} color="var(--navy)" />
          <div>
            <div className="page-title">{turbine.turbine_id}</div>
            <div className="page-subtitle">{turbine.farm_name} - Asset ID: {turbine.asset_id}</div>
          </div>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="stat-card highlight-red">
          <div>
            <div className="stat-label">Aktif Alarmlar</div>
            <div className="stat-value" style={{ color: 'var(--red)' }}>{stats.active_count}</div>
          </div>
          <div className="stat-icon red"><AlertTriangle size={18} /></div>
        </div>
        <div className="stat-card highlight-green">
          <div>
            <div className="stat-label">Cozulen</div>
            <div className="stat-value" style={{ color: 'var(--green)' }}>{stats.resolved_count}</div>
          </div>
          <div className="stat-icon green"><CheckCircle size={18} /></div>
        </div>
        <div className="stat-card">
          <div>
            <div className="stat-label">Toplam Olay</div>
            <div className="stat-value">{stats.total_count}</div>
          </div>
          <div className="stat-icon navy"><Activity size={18} /></div>
        </div>
      </div>

      <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}>Alarm Gecmisi</div>
        <table className="table">
          <thead>
            <tr><th>Tip</th><th>Skor</th><th>Guven</th><th>Durum</th><th>Tarih</th></tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr><td colSpan={5} className="text-muted" style={{ textAlign: 'center', padding: '2rem' }}>Bu turbin icin alarm kaydedilmemis</td></tr>
            ) : alerts.map((a) => {
              const score = Math.round(a.anomaly_score * 100);
              const riskClass = score > 85 ? 'risk-high' : score > 60 ? 'risk-medium' : 'risk-low';
              return (
                <tr key={a.id}>
                  <td style={{ fontWeight: 500 }}>{a.anomaly_type}</td>
                  <td><span className={`risk-score ${riskClass}`}>{score}</span></td>
                  <td>{Math.round(a.confidence * 100)}%</td>
                  <td><span className={`badge badge-${a.status === 'active' ? 'kritik' : 'resolved'}`}>{a.status === 'active' ? 'Aktif' : 'Cozuldu'}</span></td>
                  <td className="text-muted text-sm">{new Date(a.created_at).toLocaleString('tr-TR')}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
