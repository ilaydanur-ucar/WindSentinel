import { useState, useEffect } from 'react';
import { CheckCircle, Download } from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../hooks/useLanguage';
import { generateCSV, generatePDF } from '../services/reportService';

export default function Alerts() {
  const { t, lang } = useLanguage();
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
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchAlerts(filter); }, [filter]);

  const handleResolve = async (id) => {
    try { await api.resolveAlert(id); fetchAlerts(filter); }
    catch (err) { alert(err.message); }
  };

  const locale = lang === 'tr' ? 'tr-TR' : 'en-US';

  return (
    <>
      <div className="page-header">
        <div className="page-title">{t('alarmManagement')}</div>
        <div className="page-sub">{t('anomalyResults')}</div>
      </div>

      <div className="flex gap-2 mb-3" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
        {[['', t('allFilter')], ['active', t('activeFilter')], ['resolved', t('resolvedFilter')]].map(([f, label]) => (
          <button key={f} className={`btn btn-filter ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
            {label}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
          <button className="btn btn-ghost btn-sm" style={{ fontSize: '10.5px' }} onClick={() => {
            const cols = [
              { key: 'id', label: t('id') },
              { key: 'turbine_id', label: t('turbine') },
              { key: 'anomaly_type', label: t('type') },
              { key: 'anomaly_score', label: t('score'), format: v => Math.round(v * 100) },
              { key: 'confidence', label: t('confidence'), format: v => Math.round(v * 100) + '%' },
              { key: 'status', label: t('status'), format: v => v === 'active' ? t('activeStatus') : t('resolvedStatus') },
              { key: 'created_at', label: t('date'), format: v => new Date(v).toLocaleString(locale) },
            ];
            generateCSV(alerts, cols, 'wind-sentinel-alerts.csv');
          }}>
            <Download size={11} /> CSV
          </button>
          <button className="btn btn-ghost btn-sm" style={{ fontSize: '10.5px' }} onClick={() => {
            const cols = [
              { key: 'id', label: t('id') },
              { key: 'turbine_id', label: t('turbine') },
              { key: 'anomaly_type', label: t('type') },
              { key: 'anomaly_score', label: t('score'), format: v => Math.round(v * 100) },
              { key: 'confidence', label: t('confidence'), format: v => Math.round(v * 100) + '%' },
              { key: 'status', label: t('status'), format: v => v === 'active' ? t('activeStatus') : t('resolvedStatus') },
              { key: 'created_at', label: t('date'), format: v => new Date(v).toLocaleString(locale) },
            ];
            generatePDF(alerts, cols, t('reportAlerts'), 'wind-sentinel-alerts.pdf');
          }}>
            <Download size={11} /> PDF
          </button>
          <span className="text-muted text-sm" style={{ fontFamily: "'JetBrains Mono', monospace", marginLeft: '0.3rem' }}>
            {pagination.total || 0} {t('records')}
          </span>
        </span>
      </div>

      <div className="panel" style={{ overflowX: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>{t('id')}</th>
              <th>{t('turbine')}</th>
              <th>{t('type')}</th>
              <th>{t('score')}</th>
              <th>{t('confidence')}</th>
              <th>{t('status')}</th>
              <th>{t('date')}</th>
              <th>{t('action')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="empty-state">{t('loading')}</td></tr>
            ) : alerts.length === 0 ? (
              <tr><td colSpan={8} className="empty-state">{t('notFound')}</td></tr>
            ) : alerts.map(a => {
              const score = Math.round(a.anomaly_score * 100);
              const severity = score > 85 ? 'crit' : score > 60 ? 'warn' : 'ok';
              const scoreColor = severity === 'crit' ? 'var(--red)' : severity === 'warn' ? 'var(--amber)' : 'var(--green)';
              return (
                <tr key={a.id}>
                  <td style={{ color: 'var(--muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>#{a.id}</td>
                  <td style={{ fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: '12.5px' }}>{a.turbine_id}</td>
                  <td>{a.anomaly_type}</td>
                  <td><span style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: scoreColor }}>{score}</span></td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", color: a.confidence >= 0.85 ? 'var(--green)' : a.confidence >= 0.70 ? 'var(--amber)' : 'var(--red)' }}>{Math.round(a.confidence * 100)}%</td>
                  <td>
                    <span className={`badge-status badge-${a.status === 'active' ? 'crit' : 'resolved'}`}>
                      {a.status === 'active' ? t('activeStatus') : t('resolvedStatus')}
                    </span>
                  </td>
                  <td className="text-muted text-sm">{new Date(a.created_at).toLocaleString(locale)}</td>
                  <td>
                    {a.status === 'active' ? (
                      <button className="btn btn-success btn-sm" onClick={() => handleResolve(a.id)}>
                        <CheckCircle size={12} /> {t('resolve')}
                      </button>
                    ) : (
                      <span className="text-muted text-sm">
                        {a.resolved_at ? new Date(a.resolved_at).toLocaleString(locale) : '—'}
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
