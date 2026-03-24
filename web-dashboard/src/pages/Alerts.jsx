import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';
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
      console.error('Alert fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts(filter);
  }, [filter]);

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
        <h1 className="page-title">Alerts</h1>
        <p className="page-subtitle">Anomaly detection results</p>
      </div>

      {/* Filters */}
      <div className="flex gap-2" style={{ marginBottom: '1rem' }}>
        {['', 'active', 'resolved'].map((f) => (
          <button
            key={f}
            className={`btn ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setFilter(f)}
          >
            {f === '' ? 'All' : f === 'active' ? 'Active' : 'Resolved'}
          </button>
        ))}
        <span className="text-muted" style={{ marginLeft: 'auto', alignSelf: 'center', fontSize: '0.85rem' }}>
          {pagination.total || 0} total
        </span>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Turbine</th>
              <th>Type</th>
              <th>Score</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Time</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="text-muted" style={{ textAlign: 'center' }}>Loading...</td></tr>
            ) : alerts.length === 0 ? (
              <tr><td colSpan={8} className="text-muted" style={{ textAlign: 'center' }}>No alerts found</td></tr>
            ) : (
              alerts.map((a) => (
                <tr key={a.id}>
                  <td>#{a.id}</td>
                  <td style={{ fontWeight: 500 }}>{a.turbine_id}</td>
                  <td>{a.anomaly_type}</td>
                  <td>
                    <span className={`badge ${a.anomaly_score > 0.85 ? 'badge-critical' : 'badge-warning'}`}>
                      {(a.anomaly_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>{(a.confidence * 100).toFixed(0)}%</td>
                  <td><span className={`badge badge-${a.status}`}>{a.status}</span></td>
                  <td className="text-muted" style={{ fontSize: '0.8rem' }}>
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td>
                    {a.status === 'active' ? (
                      <button className="btn btn-success" style={{ padding: '0.3rem 0.7rem', fontSize: '0.8rem' }}
                        onClick={() => handleResolve(a.id)}>
                        <CheckCircle size={14} style={{ marginRight: '0.3rem' }} />Resolve
                      </button>
                    ) : (
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                        {a.resolved_at ? new Date(a.resolved_at).toLocaleString() : '-'}
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
