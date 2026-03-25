import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, ShieldCheck, Calculator } from 'lucide-react';
import { api } from '../services/api';

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Az önce';
  if (mins < 60) return `${mins} dk önce`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} saat önce`;
  return `${Math.floor(hours / 24)} gün önce`;
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

// Manuel Ölçüm Paneli
function ManualMeasurement() {
  const [values, setValues] = useState({
    wind_speed: '',
    power_output: '',
    generator_rpm: '',
    gearbox_oil_temp: '',
    vibration: '',
  });
  const [result, setResult] = useState(null);
  const [calculating, setCalculating] = useState(false);

  const handleChange = (field, val) => {
    setValues(prev => ({ ...prev, [field]: val }));
    setResult(null);
  };

  const calculate = () => {
    setCalculating(true);

    // Risk hesaplama: sensör değerlerinden anomali skoru türet
    const ws = parseFloat(values.wind_speed) || 0;
    const po = parseFloat(values.power_output) || 0;
    const rpm = parseFloat(values.generator_rpm) || 0;
    const temp = parseFloat(values.gearbox_oil_temp) || 0;
    const vib = parseFloat(values.vibration) || 0;

    // Güç eğrisi sapması: beklenen güç vs gerçek güç
    const expectedPower = ws > 3 ? Math.min(ws * ws * ws * 0.0005, 3.0) : 0;
    const powerDeviation = Math.abs(po - expectedPower) / (expectedPower + 0.1);

    // RPM anomalisi: rüzgar hızına göre beklenen RPM sapması
    const expectedRpm = ws > 3 ? ws * 120 : 0;
    const rpmDeviation = rpm > 0 ? Math.abs(rpm - expectedRpm) / (expectedRpm + 1) : 0;

    // Sıcaklık riski: 65°C üstü uyarı, 80°C üstü kritik
    const tempRisk = temp > 80 ? 0.9 : temp > 65 ? 0.5 : temp > 50 ? 0.2 : 0.05;

    // Titreşim riski: 3 mm/s üstü uyarı, 6 mm/s üstü kritik
    const vibRisk = vib > 6 ? 0.95 : vib > 3 ? 0.5 : vib > 1.5 ? 0.15 : 0.03;

    // Ağırlıklı toplam risk skoru
    const riskScore = Math.min(100, Math.round(
      (powerDeviation * 25 + rpmDeviation * 20 + tempRisk * 100 * 0.3 + vibRisk * 100 * 0.25)
    ));

    const severity = riskScore >= 70 ? 'KRİTİK' : riskScore >= 40 ? 'UYARI' : 'NORMAL';
    const severityClass = riskScore >= 70 ? 'crit' : riskScore >= 40 ? 'warn' : 'ok';

    setTimeout(() => {
      setResult({ riskScore, severity, severityClass, powerDeviation: (powerDeviation * 100).toFixed(1), tempRisk: (tempRisk * 100).toFixed(0), vibRisk: (vibRisk * 100).toFixed(0) });
      setCalculating(false);
    }, 500);
  };

  const fields = [
    { key: 'wind_speed', label: 'Rüzgâr Hızı', unit: 'm/s', placeholder: '8.5' },
    { key: 'power_output', label: 'Güç Üretimi', unit: 'MW', placeholder: '2.1' },
    { key: 'generator_rpm', label: 'Jeneratör RPM', unit: 'rpm', placeholder: '1200' },
    { key: 'gearbox_oil_temp', label: 'Dişli Kutusu Sıcaklığı', unit: '°C', placeholder: '45' },
    { key: 'vibration', label: 'Titreşim Seviyesi', unit: 'mm/s', placeholder: '1.2' },
  ];

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Manuel Ölçüm</span>
        <span style={{ fontSize: '10px', color: 'var(--muted)', fontFamily: "'JetBrains Mono', monospace" }}>Sensör değerlerini girin</span>
      </div>
      <div className="panel-body">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
          {fields.map(f => (
            <div key={f.key}>
              <div style={{ fontSize: '9.5px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '3px' }}>
                {f.label}
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  className="input"
                  type="number"
                  step="0.1"
                  placeholder={f.placeholder}
                  value={values[f.key]}
                  onChange={e => handleChange(f.key, e.target.value)}
                  style={{ paddingRight: '2.2rem', fontSize: '12.5px', fontFamily: "'JetBrains Mono', monospace" }}
                />
                <span style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', fontSize: '10px', color: 'var(--muted)' }}>
                  {f.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button className="btn btn-primary" onClick={calculate} disabled={calculating} style={{ fontSize: '12px' }}>
            <Calculator size={14} /> {calculating ? 'Hesaplanıyor...' : 'Risk Hesapla'}
          </button>
          {result && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Risk Skoru:</span>
                <span className={`alarm-badge ${result.severityClass}`} style={{ fontSize: '13px', padding: '3px 10px' }}>
                  {result.riskScore}/100 — {result.severity}
                </span>
              </div>
              <div style={{ fontSize: '10.5px', color: 'var(--muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                Güç Sapması: %{result.powerDeviation} · Sıcaklık Riski: %{result.tempRisk} · Titreşim Riski: %{result.vibRisk}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
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

  if (loading) return <div className="empty-state"><Activity size={20} /><div style={{ marginTop: 8 }}>Yükleniyor...</div></div>;

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
            <div className="page-sub">Wind Farm A — Gerçek zamanlı izleme</div>
          </div>
          <div className="flex gap-2">
            <span className="btn btn-ghost btn-sm">Son 24 Saat</span>
          </div>
        </div>
      </div>

      {/* İstatistik Kartları */}
      <div className="stats-row">
        <div className="stat-card blue">
          <div className="stat-label">Aktif Türbin</div>
          <div className="stat-value blue">{onlineCount}<span style={{ fontSize: '0.7em', color: 'var(--muted)' }}>/{turbines.length}</span></div>
          <div className="stat-sub">{turbines.length - onlineCount === 0 ? 'Tümü operasyonel' : `${turbines.length - onlineCount} devre dışı`}</div>
        </div>

        <div className="stat-card green">
          <div className="stat-label">Çözüm Oranı</div>
          <div className="stat-value green">{resolutionRate}%</div>
          <div className="stat-sub">{resolvedAlerts}/{totalAlerts} çözüldü</div>
        </div>

        <div className="stat-card amber">
          <div className="stat-label">Ort. Risk Skoru</div>
          <div className="stat-value amber">{avgRisk}</div>
          <div className="stat-sub">/100 puan</div>
        </div>

        <div className="stat-card red">
          <div className="stat-label">Aktif Alarm</div>
          <div className="stat-value red">{activeAlerts}</div>
          <div className="stat-sub">{affectedTurbines} türbin etkilendi</div>
        </div>
      </div>

      {/* Türbin Risk Durumu + Alarmlar */}
      <div className="grid-2-wide mb-3">
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Türbin Risk Durumu</span>
            <Link to="/turbines" className="btn btn-ghost btn-sm">Tümü <ArrowRight size={12} /></Link>
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
                          <div className="t-metric-lbl">Çiftlik</div>
                        </div>
                        <div className="t-metric">
                          <div className="t-metric-val">{t.status === 'online' ? 'AKTİF' : 'KAPALI'}</div>
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

        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Aktif Alarmlar</span>
            <Link to="/alerts" className="btn btn-ghost btn-sm">Tümü <ArrowRight size={12} /></Link>
          </div>
          <div className="alarm-list">
            {alerts.length === 0 ? (
              <div className="empty-state"><ShieldCheck size={18} /><div style={{ marginTop: 6 }}>Aktif alarm yok</div></div>
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
                      <div className="alarm-meta">Skor: {score} · {timeAgo(a.created_at)}</div>
                    </div>
                    <span className={`alarm-badge ${severity}`}>
                      {severity === 'crit' ? 'KRİTİK' : severity === 'warn' ? 'UYARI' : 'BİLGİ'}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Risk Skoru Trendi */}
      <div className="panel mb-3">
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

      {/* Manuel Ölçüm */}
      <ManualMeasurement />
    </>
  );
}
