import { useState, useEffect } from 'react';
import { CheckCircle } from 'lucide-react';
import { api } from '../services/api';

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [pagination, setPagination] = useState({});
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async (status = '') => {
    setLoading(true);
    try {
      const params = { limit: 20, sort: 'created_at_desc' };
      if (status) params.status = status;
      const res = await api.getAlerts(params);
      setAlerts(res.data);
      setPagination(res.pagination);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAlerts(filter); }, [filter]);

  const handleResolve = async (id) => {
    try {
      await api.resolveAlert(id);
      fetchAlerts(filter);
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title">Alarmlar</div>
        <div className="page-subtitle">Anomali tespit sonuclari</div>
      </div>

      <div className="flex gap-2 mb-4">
        {[['', 'Tumu'], ['active', 'Aktif'], ['resolved', 'Cozulmus']].map(([f, label]) => (
          <button key={f} className={`btn btn-filter ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
            {label}
          </button>
        ))}
        <span className="text-muted" style={{ marginLeft: 'auto', alignSelf: 'center', fontSize: '0.82rem' }}>
          {pagination.total || 0} kayit
        </span>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Turbin</th>
              <th>Tip</th>
              <th>Skor</th>
              <th>Guven</th>
              <th>Durum</th>
              <th>Tarih</th>
              <th>Islem</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="text-muted" style={{ textAlign: 'center' }}>Yukleniyor...</td></tr>
            ) : alerts.length === 0 ? (
              <tr><td colSpan={8} className="text-muted" style={{ textAlign: 'center' }}>Alarm bulunamadi</td></tr>
            ) : alerts.map((a) => {
              const score = Math.round(a.anomaly_score * 100);
              const riskClass = score > 85 ? 'risk-high' : score > 60 ? 'risk-medium' : 'risk-low';
              return (
                <tr key={a.id}>
                  <td className="text-muted">#{a.id}</td>
                  <td style={{ fontWeight: 600 }}>{a.turbine_id}</td>
                  <td>{a.anomaly_type}</td>
                  <td><span className={`risk-score ${riskClass}`}>{score}</span></td>
                  <td>{Math.round(a.confidence * 100)}%</td>
                  <td>
                    <span className={`badge badge-${a.status === 'active' ? 'kritik' : 'resolved'}`}>
                      {a.status === 'active' ? 'Aktif' : 'Cozuldu'}
                    </span>
                  </td>
                  <td className="text-muted text-sm">{new Date(a.created_at).toLocaleString('tr-TR')}</td>
                  <td>
                    {a.status === 'active' ? (
                      <button className="btn btn-success btn-sm" onClick={() => handleResolve(a.id)}>
                        <CheckCircle size={14} /> Coz
                      </button>
                    ) : (
                      <span className="text-muted text-sm">
                        {a.resolved_at ? new Date(a.resolved_at).toLocaleString('tr-TR') : '-'}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
