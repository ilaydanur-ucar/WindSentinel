import { useState } from 'react';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try { await onLogin(email, password); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="login-page">
      <div className="bg-grid"></div>
      <div className="bg-glow"></div>
      <div className="login-box">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
          <svg width="36" height="36" viewBox="0 0 32 32" fill="none">
            <rect x="14.5" y="14" width="3" height="14" rx="1.5" fill="#2563eb" opacity="0.9"/>
            <g className="spinning" style={{'--spd': '4s'}}>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.9" transform="rotate(0,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.6" transform="rotate(120,16,13)"/>
              <ellipse cx="16" cy="13" rx="1.5" ry="7" fill="#2563eb" opacity="0.6" transform="rotate(240,16,13)"/>
            </g>
            <circle cx="16" cy="13" r="2.5" fill="#2563eb"/>
            <circle cx="16" cy="13" r="1.2" fill="white"/>
          </svg>
          <div>
            <div className="login-title">WIND <span style={{ color: 'var(--accent)' }}>SENTINEL</span></div>
            <div style={{ fontSize: '9px', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
              Erken Arıza Tespit Sistemi
            </div>
          </div>
        </div>
        <p className="login-subtitle">Türbin izleme paneline erişim için giriş yapın.</p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">E-posta</label>
            <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="admin@windsentinel.com" required />
          </div>
          <div className="input-group">
            <label className="input-label">Şifre</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%', padding: '0.6rem', justifyContent: 'center', fontSize: '13px' }} disabled={loading}>
            {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
          </button>
        </form>
      </div>
    </div>
  );
}
