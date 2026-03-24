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
    try {
      await onLogin(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="flex items-center gap-3" style={{ marginBottom: '1.5rem' }}>
          <img src="/favicon.svg" alt="WindSentinel" style={{ width: 40, height: 40 }} />
          <div>
            <div className="login-title">WIND Sentinel</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Erken Ariza Tespit Sistemi
            </div>
          </div>
        </div>
        <p className="login-subtitle">Sisteme giris yaparak turbin izleme paneline erisebilirsiniz.</p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">E-posta</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@windsentinel.com" required />
          </div>
          <div className="input-group">
            <label className="input-label">Sifre</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%', padding: '0.7rem', justifyContent: 'center' }} disabled={loading}>
            {loading ? 'Giris yapiliyor...' : 'Giris Yap'}
          </button>
        </form>
      </div>
    </div>
  );
}
