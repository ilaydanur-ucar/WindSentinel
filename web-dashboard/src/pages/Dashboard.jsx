import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, ShieldCheck, Calculator } from 'lucide-react';

import { api } from '../services/api';
import { useLanguage } from '../hooks/useLanguage';
import { timeAgo } from '../utils/formatters';


function RiskChart({ alerts }) {
  // Build time-based data points from alerts (sorted by date)
  const sorted = [...alerts].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

  // Chart dimensions
  const W = 600, H = 260, PAD_L = 48, PAD_R = 24, PAD_T = 24, PAD_B = 32;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  // Generate points
  let points;
  let timeLabels;

  if (sorted.length > 0) {
    const minTime = new Date(sorted[0].created_at).getTime();
    const maxTime = new Date(sorted[sorted.length - 1].created_at).getTime();
    const range = maxTime - minTime || 1;

    points = sorted.map(a => {
      const score = Math.round(a.anomaly_score * 100);
      const t = (new Date(a.created_at).getTime() - minTime) / range;
      return {
        x: PAD_L + t * plotW,
        y: PAD_T + plotH - (score / 100) * plotH,
        score,
        date: new Date(a.created_at),
        type: a.anomaly_type,
        turbine: a.turbine_id,
      };
    });

    // Time labels (distribute evenly)
    const labelCount = Math.min(6, sorted.length);
    timeLabels = Array.from({ length: labelCount }, (_, i) => {
      const idx = Math.round(i * (sorted.length - 1) / Math.max(labelCount - 1, 1));
      const d = new Date(sorted[idx].created_at);
      const x = PAD_L + ((d.getTime() - minTime) / range) * plotW;
      return { x, label: `${d.getDate()}.${d.getMonth() + 1} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` };
    });
  } else {
    // Placeholder - animated sine wave
    points = Array.from({ length: 12 }, (_, i) => ({
      x: PAD_L + (i / 11) * plotW,
      y: PAD_T + plotH / 2 + Math.sin(i * 0.8) * plotH * 0.2,
      score: Math.round(50 + Math.sin(i * 0.8) * 20),
    }));
    timeLabels = Array.from({ length: 6 }, (_, i) => {
      const h = i * 4;
      return { x: PAD_L + (i / 5) * plotW, label: `${String(h).padStart(2, '0')}:00` };
    });
  }

  // Smooth curve path (catmull-rom to bezier)
  const curvePath = points.length < 2 ? '' : points.reduce((path, p, i, arr) => {
    if (i === 0) return `M${p.x},${p.y}`;
    const p0 = arr[Math.max(i - 2, 0)];
    const p1 = arr[i - 1];
    const p2 = p;
    const p3 = arr[Math.min(i + 1, arr.length - 1)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    return `${path} C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
  }, '');

  const areaPath = curvePath
    ? `${curvePath} L${points[points.length - 1].x},${PAD_T + plotH} L${points[0].x},${PAD_T + plotH} Z`
    : '';

  // Threshold lines
  const y70 = PAD_T + plotH - (70 / 100) * plotH;
  const y40 = PAD_T + plotH - (40 / 100) * plotH;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%' }}>
      <defs>
        <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.01" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      {/* Grid lines */}
      {[0, 25, 50, 75, 100].map(v => {
        const y = PAD_T + plotH - (v / 100) * plotH;
        return (
          <g key={v}>
            <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y} stroke="#edf0f5" strokeWidth="0.7" />
            <text x={PAD_L - 6} y={y + 3.5} fontSize="9" fill="#94a3b8" textAnchor="end" fontFamily="JetBrains Mono">{v}</text>
          </g>
        );
      })}

      {/* Threshold zones */}
      <rect x={PAD_L} y={PAD_T} width={plotW} height={y70 - PAD_T} fill="#fef2f2" opacity="0.4" rx="2" />
      <rect x={PAD_L} y={y70} width={plotW} height={y40 - y70} fill="#fffbeb" opacity="0.3" rx="2" />

      {/* Threshold lines */}
      <line x1={PAD_L} y1={y70} x2={W - PAD_R} y2={y70} stroke="#dc2626" strokeWidth="0.7" strokeDasharray="4 3" opacity="0.5" />
      <line x1={PAD_L} y1={y40} x2={W - PAD_R} y2={y40} stroke="#d97706" strokeWidth="0.7" strokeDasharray="4 3" opacity="0.4" />
      <text x={W - PAD_R + 2} y={y70 + 3} fontSize="7.5" fill="#dc2626" opacity="0.7" fontFamily="JetBrains Mono">70</text>
      <text x={W - PAD_R + 2} y={y40 + 3} fontSize="7.5" fill="#d97706" opacity="0.6" fontFamily="JetBrains Mono">40</text>

      {/* Area fill + curve */}
      {areaPath && <path d={areaPath} fill="url(#riskGrad)" />}
      {curvePath && <path d={curvePath} fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" filter="url(#glow)" />}

      {/* Data points */}
      {points.map((p, i) => {
        const color = p.score >= 70 ? '#dc2626' : p.score >= 40 ? '#d97706' : '#2563eb';
        return (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="4" fill="white" stroke={color} strokeWidth="2" />
            <text x={p.x} y={p.y - 10} fontSize="9" fill={color} textAnchor="middle" fontWeight="700" fontFamily="JetBrains Mono">
              {p.score}
            </text>
            {p.turbine && (
              <text x={p.x} y={p.y + 14} fontSize="7" fill="#94a3b8" textAnchor="middle" fontFamily="JetBrains Mono">
                {p.turbine}
              </text>
            )}
          </g>
        );
      })}

      {/* Time labels on X axis */}
      {timeLabels.map((tl, i) => (
        <text key={i} x={tl.x} y={H - 6} fontSize="8" fill="#94a3b8" textAnchor="middle" fontFamily="JetBrains Mono">
          {tl.label}
        </text>
      ))}
    </svg>
  );
}


export default function Dashboard() {
  const { t } = useLanguage();
  const [stats, setStats] = useState(null);
  const [turbines, setTurbines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [s, tr, a] = await Promise.all([
          api.getAlertStats(),
          api.getTurbines(),
          api.getAlerts({ limit: 8, sort: 'created_at_desc' }),
        ]);
        setStats(s.data);
        setTurbines(tr.data);
        setAlerts(a.data);
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    }
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, []);

  if (loading) return <div className="empty-state"><Activity size={20} /><div style={{ marginTop: 8 }}>{t('loading')}</div></div>;

  const onlineCount = turbines.filter(tb => tb.status === 'online').length;
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
            <div className="page-title">{t('controlPanel')}</div>
            <div className="page-sub">Wind Farm A — {t('realTimeMonitoring')}</div>
          </div>
          <div className="flex gap-2">
            <span className="btn btn-ghost btn-sm">{t('last24h')}</span>
          </div>
        </div>
      </div>

      <div className="stats-row">
        <div className="stat-card blue">
          <div className="stat-label">{t('activeTurbine')}</div>
          <div className="stat-value blue">{onlineCount}<span style={{ fontSize: '0.7em', color: 'var(--muted)' }}>/{turbines.length}</span></div>
          <div className="stat-sub">{turbines.length - onlineCount === 0 ? t('allOperational') : `${turbines.length - onlineCount} ${t('offline')}`}</div>
        </div>

        <div className="stat-card green">
          <div className="stat-label">{t('resolutionRate')}</div>
          <div className="stat-value green">{resolutionRate}%</div>
          <div className="stat-sub">{resolvedAlerts}/{totalAlerts} {t('resolved')}</div>
        </div>

        <div className="stat-card amber">
          <div className="stat-label">{t('avgRiskScore')}</div>
          <div className="stat-value amber">{avgRisk}</div>
          <div className="stat-sub">{t('points100')}</div>
        </div>

        <div className="stat-card red">
          <div className="stat-label">{t('activeAlarm')}</div>
          <div className="stat-value red">{activeAlerts}</div>
          <div className="stat-sub">{affectedTurbines} {t('turbinesAffected')}</div>
        </div>
      </div>

      <div className="grid-2-wide mb-3">
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">{t('turbineRiskStatus')}</span>
            <Link to="/turbines" className="btn btn-ghost btn-sm">{t('all')} <ArrowRight size={12} /></Link>
          </div>
          <div className="panel-body">
            <div className="turbine-grid">
              {turbines.map(tb => {
                const alertCount = Number(tb.active_alerts);
                const turbineAlerts = alerts.filter(a => a.turbine_id === tb.turbine_id && a.status === 'active');
                const riskScore = turbineAlerts.length > 0
                  ? Math.round(turbineAlerts.reduce((s, a) => s + a.anomaly_score, 0) / turbineAlerts.length * 100)
                  : 0;
                const riskClass = riskScore >= 70 ? 'high' : riskScore >= 30 ? 'med' : 'low';
                const cardClass = riskScore >= 70 ? 'critical' : riskScore >= 30 ? 'warning' : '';
                const dotClass = riskScore >= 70 ? 'dot-crit' : riskScore >= 30 ? 'dot-warn' : 'dot-ok';

                return (
                  <Link key={tb.turbine_id} to={`/turbines/${tb.turbine_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                    <div className={`turbine-card ${cardClass}`}>
                      <div className="turbine-top">
                        <span className="turbine-id">{tb.turbine_id}</span>
                        <div className={`turbine-status-dot ${dotClass}`}></div>
                      </div>
                      <div className="risk-label">{t('riskScore')}: {riskScore}/100</div>
                      <div className="risk-bar">
                        <div className={`risk-fill ${riskClass}`} style={{ width: `${Math.max(riskScore, 3)}%` }}></div>
                      </div>
                      <div className="turbine-metrics">
                        <div className="t-metric">
                          <div className="t-metric-val">{alertCount}</div>
                          <div className="t-metric-lbl">{t('alarm')}</div>
                        </div>
                        <div className="t-metric">
                          <div className="t-metric-val">{tb.farm_name?.replace('Wind Farm ', '') || 'A'}</div>
                          <div className="t-metric-lbl">{t('farm')}</div>
                        </div>
                        <div className="t-metric">
                          <div className="t-metric-val">{tb.status === 'online' ? t('active') : t('closed')}</div>
                          <div className="t-metric-lbl">{t('status')}</div>
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">{t('activeAlarms')}</span>
            <Link to="/alerts" className="btn btn-ghost btn-sm">{t('all')} <ArrowRight size={12} /></Link>
          </div>
          <div className="alarm-list">
            {alerts.length === 0 ? (
              <div className="empty-state"><ShieldCheck size={18} /><div style={{ marginTop: 6 }}>{t('noActiveAlarm')}</div><div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: 2 }}>{t('systemHealthy')}</div></div>
            ) : (
              alerts.slice(0, 6).map(a => {
                const score = Math.round(a.anomaly_score * 100);
                const severity = score > 85 ? 'crit' : score > 60 ? 'warn' : 'info';
                const dotColor = severity === 'crit' ? 'var(--red)' : severity === 'warn' ? 'var(--amber)' : 'var(--accent)';
                return (
                  <div key={a.id} className="alarm-item">
                    <div className="alarm-dot" style={{ background: dotColor }}></div>
                    <div className="alarm-info">
                      <div className="alarm-title">{a.turbine_id} — {a.anomaly_type}</div>
                      <div className="alarm-meta">{t('score')}: {score} · {timeAgo(a.created_at, t)}</div>
                    </div>
                    <span className={`alarm-badge ${severity}`}>
                      {severity === 'crit' ? t('severityCritical') : severity === 'warn' ? t('severityWarning') : t('severityActive')}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div className="panel mb-3">
        <div className="panel-header">
          <span className="panel-title">{t('riskScoreTrend')}</span>
          <div className="flex gap-2">
            <span className="btn btn-filter btn-sm active" style={{ fontSize: '10px' }}>24H</span>
            <span className="btn btn-filter btn-sm" style={{ fontSize: '10px' }}>7D</span>
          </div>
        </div>
        <div className="panel-body">
          <div className="chart-area">
            <RiskChart alerts={alerts} />
          </div>
        </div>
      </div>

      {/* Quick Measure - links to full page */}
      <Link to="/measurement" style={{ textDecoration: 'none', color: 'inherit' }}>
        <div className="panel" style={{ cursor: 'pointer', transition: 'box-shadow 0.15s' }}>
          <div className="panel-header">
            <span className="panel-title"><Calculator size={14} style={{ marginRight: 6 }} />{t('quickMeasure')}</span>
            <span className="btn btn-ghost btn-sm">{t('goToMeasurement')} <ArrowRight size={12} /></span>
          </div>
          <div className="panel-body" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--muted)', fontSize: '13px' }}>
            {t('enterSensorValues')}
          </div>
        </div>
      </Link>
    </>
  );
}
