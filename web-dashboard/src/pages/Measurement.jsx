import { useState, useEffect } from 'react';
import { Calculator, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import { useLanguage } from '../hooks/useLanguage';
import { calculateRisk } from '../utils/riskCalculator';
import { generateCSV } from '../services/reportService';

const SENSOR_FIELDS = [
  { key: 'wind_speed', unit: 'm/s', placeholder: '8.5' },
  { key: 'power_output', unit: 'MW', placeholder: '2.1' },
  { key: 'generator_rpm', unit: 'rpm', placeholder: '1200' },
  { key: 'gearbox_oil_temp', unit: '°C', placeholder: '45' },
  { key: 'vibration', unit: 'mm/s', placeholder: '1.2' },
];

const FIELD_LABELS = {
  wind_speed: 'windSpeed',
  power_output: 'powerOutput',
  generator_rpm: 'generatorRpm',
  gearbox_oil_temp: 'gearboxTemp',
  vibration: 'vibrationLevel',
};

function loadHistory() {
  try { return JSON.parse(localStorage.getItem('ws_measurements') || '[]'); }
  catch { return []; }
}

function saveHistory(history) {
  localStorage.setItem('ws_measurements', JSON.stringify(history.slice(0, 20)));
}

export default function Measurement() {
  const { t, lang } = useLanguage();
  const [turbines, setTurbines] = useState([]);
  const [selectedTurbine, setSelectedTurbine] = useState('');
  const [values, setValues] = useState({ wind_speed: '', power_output: '', generator_rpm: '', gearbox_oil_temp: '', vibration: '' });
  const [result, setResult] = useState(null);
  const [calculating, setCalculating] = useState(false);
  const [history, setHistory] = useState(loadHistory);

  useEffect(() => {
    api.getTurbines().then(res => setTurbines(res.data || [])).catch(() => {});
  }, []);

  const handleChange = (field, val) => {
    setValues(prev => ({ ...prev, [field]: val }));
    setResult(null);
  };

  const handleCalculate = () => {
    setCalculating(true);
    setTimeout(() => {
      const risk = calculateRisk(values);
      const severity = risk.riskScore >= 70 ? t('critical') : risk.riskScore >= 40 ? t('warning') : t('normal');
      const severityClass = risk.riskScore >= 70 ? 'crit' : risk.riskScore >= 40 ? 'warn' : 'ok';
      setResult({ ...risk, severity, severityClass });

      const entry = {
        id: Date.now(),
        turbine: selectedTurbine || '—',
        ...values,
        riskScore: risk.riskScore,
        severity: severityClass,
        date: new Date().toISOString(),
      };
      const newHistory = [entry, ...history].slice(0, 20);
      setHistory(newHistory);
      saveHistory(newHistory);
      setCalculating(false);
    }, 400);
  };

  const clearHistory = () => { setHistory([]); localStorage.removeItem('ws_measurements'); };

  const exportHistory = () => {
    generateCSV(history, [
      { key: 'turbine', label: t('turbine') },
      { key: 'wind_speed', label: t('windSpeed') },
      { key: 'power_output', label: t('powerOutput') },
      { key: 'generator_rpm', label: t('generatorRpm') },
      { key: 'gearbox_oil_temp', label: t('gearboxTemp') },
      { key: 'vibration', label: t('vibrationLevel') },
      { key: 'riskScore', label: t('riskScore') },
      { key: 'date', label: t('date'), format: (v) => new Date(v).toLocaleString(lang === 'tr' ? 'tr-TR' : 'en-US') },
    ], 'measurements.csv');
  };

  return (
    <>
      <div className="page-header">
        <div className="page-title">{t('measurementPage')}</div>
        <div className="page-sub">{t('measurementDesc')}</div>
      </div>

      {/* Türbin Seçici + Form */}
      <div className="panel mb-3">
        <div className="panel-header">
          <span className="panel-title"><Calculator size={14} style={{ marginRight: 6 }} />{t('calculateRisk')}</span>
        </div>
        <div className="panel-body">
          {/* Türbin dropdown */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontSize: '9.5px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '3px' }}>
              {t('selectTurbine')}
            </div>
            <select
              className="input"
              value={selectedTurbine}
              onChange={e => setSelectedTurbine(e.target.value)}
              style={{ maxWidth: '280px', fontSize: '12.5px', fontFamily: "'JetBrains Mono', monospace" }}
            >
              <option value="">— {t('selectTurbine')} —</option>
              {turbines.map(tb => (
                <option key={tb.turbine_id} value={tb.turbine_id}>{tb.turbine_id} ({tb.farm_name})</option>
              ))}
            </select>
          </div>

          {/* Sensör inputları */}
          <div className="manual-fields">
            {SENSOR_FIELDS.map(f => (
              <div key={f.key}>
                <div style={{ fontSize: '9.5px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '3px' }}>
                  {t(FIELD_LABELS[f.key])}
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

          {/* Hesapla butonu + sonuç */}
          <div className="manual-result-row" style={{ marginTop: '0.75rem' }}>
            <button className="btn btn-primary" onClick={handleCalculate} disabled={calculating} style={{ fontSize: '12px' }}>
              <Calculator size={14} /> {calculating ? t('calculating') : t('calculateRisk')}
            </button>
            {result && (
              <div className="manual-result-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '11px', color: 'var(--muted)' }}>{t('riskScore')}:</span>
                  <span className={`alarm-badge ${result.severityClass}`} style={{ fontSize: '14px', padding: '4px 12px' }}>
                    {result.riskScore}/100 — {result.severity}
                  </span>
                </div>
                <div style={{ fontSize: '10.5px', color: 'var(--muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {t('powerDeviation')}: %{result.powerDeviation} · {t('tempRisk')}: %{result.tempRisk} · {t('vibRisk')}: %{result.vibRisk}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Ölçüm Geçmişi */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">{t('measurementHistory')}</span>
          <div className="flex gap-2">
            {history.length > 0 && (
              <>
                <button className="btn btn-ghost btn-sm" onClick={exportHistory} style={{ fontSize: '10.5px' }}>
                  {t('downloadCSV')}
                </button>
                <button className="btn btn-ghost btn-sm" onClick={clearHistory} style={{ fontSize: '10.5px', color: 'var(--red)' }}>
                  <Trash2 size={11} /> {t('clearHistory')}
                </button>
              </>
            )}
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ minWidth: '520px' }}>
            <thead>
              <tr>
                <th>{t('turbine')}</th>
                <th>{t('windSpeed')}</th>
                <th>{t('powerOutput')}</th>
                <th>{t('generatorRpm')}</th>
                <th>{t('gearboxTemp')}</th>
                <th>{t('vibrationLevel')}</th>
                <th>{t('riskScore')}</th>
                <th>{t('date')}</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td colSpan={8} className="empty-state">{t('noMeasurement')}</td></tr>
              ) : history.map(h => {
                const sev = h.severity === 'crit' ? 'var(--red)' : h.severity === 'warn' ? 'var(--amber)' : 'var(--green)';
                return (
                  <tr key={h.id}>
                    <td style={{ fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.turbine}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.wind_speed || '—'}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.power_output || '—'}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.generator_rpm || '—'}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.gearbox_oil_temp || '—'}</td>
                    <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11.5px' }}>{h.vibration || '—'}</td>
                    <td><span style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: sev }}>{h.riskScore}</span></td>
                    <td className="text-muted text-sm">{new Date(h.date).toLocaleString(lang === 'tr' ? 'tr-TR' : 'en-US')}</td>
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
