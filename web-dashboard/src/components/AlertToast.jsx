import { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { connectSocket, disconnectSocket } from '../services/socket';

export default function AlertToast() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const socket = connectSocket();

    socket.on('new_alert', (alert) => {
      const toast = { ...alert, _id: Date.now() };
      setToasts((prev) => [toast, ...prev].slice(0, 5));

      // 10 saniye sonra otomatik kaldır
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t._id !== toast._id));
      }, 10000);
    });

    return () => disconnectSocket();
  }, []);

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t._id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t._id} className="toast toast-alert">
          <div className="flex items-center gap-2" style={{ justifyContent: 'space-between' }}>
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} color="var(--accent-red)" />
              <strong>New Alert</strong>
            </div>
            <button onClick={() => removeToast(t._id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
              <X size={16} />
            </button>
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
            <div><strong>{t.turbine_id}</strong> - {t.anomaly_type}</div>
            <div className="text-muted">Score: {(t.anomaly_score * 100).toFixed(0)}%</div>
          </div>
        </div>
      ))}
    </div>
  );
}
