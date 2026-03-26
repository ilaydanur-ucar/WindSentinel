import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Activity, Download } from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../hooks/useLanguage';
import { generateCSV, generatePDF } from '../services/reportService';

export function TurbineList() {
  const { t, lang } = useLanguage();
  const [turbines, setTurbines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getTurbines(), api.getAlerts({ limit: 50 })]).then(([tb, a]) => {
      setTurbines(tb.data);
      setAlerts(a.data);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="empty-state"><Activity size={18} /><div style={{ marginTop: 8 }}>{t('loading')}</div></div>;

  return (
    <>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <div className="page-title">{t('turbineStatuses')}</div>
            <div className="page-sub">{t('realTimeData')}</div>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-ghost btn-sm" style={{ fontSize: '10.5px' }} onClick={() => {
              const cols = [
                { key: 'turbine_id', label: t('turbine') },
                { key: 'status', label: t('status') },
                { key: 'active_alerts', label: t('activeAlarmLabel') },
                { key: 'farm_name', label: t('farmLabel') },
              ];
              generateCSV(turbines, cols, 'wind-sentinel-turbines.csv');
            }}>
              <Download size={11} /> CSV
            </button>
            <button className="btn btn-ghost btn-sm" style={{ fontSize: '10.5px' }} onClick={() => {
              const cols = [
                { key: 'turbine_id', label: t('turbine') },
                { key: 'status', label: t('status') },
                { key: 'active_alerts', label: t('activeAlarmLabel') },
                { key: 'farm_name', label: t('farmLabel') },
              ];
              generatePDF(turbines, cols, t('reportTurbines'), 'wind-sentinel-turbines.pdf');
            }}>
              <Download size={11} /> PDF
            </button>
          </div>
        </div>
      </div>

      <div className="panel">
        <div style={{ overflowX: 'auto', width: '100%' }}>
        <table className="table" style={{ minWidth: '420px' }}>
          <thead>
            <tr>
              <th>{t('turbine')}</th>
              <th>{t('status')}</th>
              <th>{t('riskScore')}</th>
              <th>{t('activeAlarmLabel')}</th>
              <th>{t('farmLabel')}</th>
            </tr>
          </thead>
          <tbody>
            {turbines.map(tb => {
              const alertCount = Number(tb.active_alerts);
              const turbineAlerts = alerts.filter(a => a.turbine_id === tb.turbine_id && a.status === 'active');
              const riskScore = turbineAlerts.length > 0
                ? Math.round(turbineAlerts.reduce((s, a) => s + a.anomaly_score, 0) / turbineAlerts.length * 100)
                : 0;
              const severity = riskScore >= 70 ? 'crit' : riskScore >= 30 ? 'warn' : 'ok';

              return (
                <tr key={tb.turbine_id} onClick={() => window.location.href = `/turbines/${tb.turbine_id}`}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div className={`turbine-status-dot dot-${severity === 'ok' ? 'ok' : severity === 'warn' ? 'warn' : 'crit'}`} style={{ width: 8, height: 8 }}></div>
                      <div>
                        <div style={{ fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: '12.5px' }}>{tb.turbine_id}</div>
                        <div style={{ fontSize: '10.5px', color: 'var(--muted)' }}>Asset-{tb.asset_id}</div>
                      </div>
                    </div>
                  </td>
                  <td><span className={`badge-status badge-${severity}`}>{severity === 'crit' ? t('severityCritical') : severity === 'warn' ? t('severityWarning') : t('severityActive')}</span></td>
                  <td>
                    <span style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: severity === 'crit' ? 'var(--red)' : severity === 'warn' ? 'var(--amber)' : 'var(--green)' }}>
                      {riskScore}
                    </span>
                  </td>
                  <td>
                    {alertCount > 0
                      ? <span style={{ fontWeight: 700, color: 'var(--red)', fontFamily: "'JetBrains Mono', monospace" }}>{alertCount}</span>
                      : <span style={{ color: 'var(--dim)' }}>0</span>}
                  </td>
                  <td style={{ color: 'var(--muted)', fontSize: '12.5px' }}>{tb.farm_name}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>
    </>
  );
}

export function TurbineDetail() {
  const { t, lang } = useLanguage();
  const { turbineId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const locale = lang === 'tr' ? 'tr-TR' : 'en-US';

  useEffect(() => {
    api.getTurbine(turbineId).then(res => { setData(res.data); setLoading(false); }).catch(() => navigate('/turbines'));
  }, [turbineId, navigate]);

  if (loading) return <div className="empty-state">{t('loading')}</div>;
  const { turbine, alerts, stats } = data;

  return (
    <>
      <div className="page-header">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/turbines')} style={{ marginBottom: '0.5rem' }}>
          <ArrowLeft size={14} /> {t('back')}
        </button>
        <div className="detail-header">
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
            <rect x="14.5" y="14" width="3" height="14" rx="1.5" fill="#1a2b4a" opacity="0.7"/>
            <g className="spinning" style={{'--spd': '3s'}}>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#1a2b4a" opacity="0.8" transform="rotate(0,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#1a2b4a" opacity="0.5" transform="rotate(120,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#1a2b4a" opacity="0.5" transform="rotate(240,16,13)"/>
            </g>
            <circle cx="16" cy="13" r="2.5" fill="#1a2b4a"/>
            <circle cx="16" cy="13" r="1.2" fill="white"/>
          </svg>
          <div>
            <div className="page-title">{turbine.turbine_id}</div>
            <div className="page-sub">{turbine.farm_name} — Asset ID: {turbine.asset_id}</div>
          </div>
        </div>
      </div>

      <div className="detail-stats">
        <div className="stat-card red">
          <div className="stat-label">{t('activeAlarmsLabel')}</div>
          <div className="stat-value red">{stats.active_count}</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">{t('resolvedLabel')}</div>
          <div className="stat-value green">{stats.resolved_count}</div>
        </div>
        <div className="stat-card blue">
          <div className="stat-label">{t('totalEvents')}</div>
          <div className="stat-value blue">{stats.total_count}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">{t('alarmHistory')}</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr><th>{t('type')}</th><th>{t('score')}</th><th>{t('confidence')}</th><th>{t('status')}</th><th>{t('date')}</th></tr>
            </thead>
            <tbody>
              {alerts.length === 0 ? (
                <tr><td colSpan={5} className="empty-state">{t('noAlarmRecorded')}</td></tr>
              ) : alerts.map(a => {
                const score = Math.round(a.anomaly_score * 100);
                const severity = score > 85 ? 'crit' : score > 60 ? 'warn' : 'ok';
                return (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 500 }}>{a.anomaly_type}</td>
                    <td>
                      <span style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: severity === 'crit' ? 'var(--red)' : severity === 'warn' ? 'var(--amber)' : 'var(--green)' }}>
                        {score}
                      </span>
                    </td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", color: a.confidence >= 0.85 ? 'var(--green)' : a.confidence >= 0.70 ? 'var(--amber)' : 'var(--red)' }}>{Math.round(a.confidence * 100)}%</td>
                    <td><span className={`badge-status badge-${a.status === 'active' ? 'crit' : 'resolved'}`}>{a.status === 'active' ? t('activeStatus') : t('resolvedStatus')}</span></td>
                    <td className="text-muted text-sm">{new Date(a.created_at).toLocaleString(locale)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
