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
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t._id !== toast._id));
      }, 10000);
    });
    return () => disconnectSocket();
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t._id} className="toast">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} color="var(--red)" />
              <strong style={{ fontSize: '0.85rem' }}>Yeni Alarm</strong>
            </div>
            <button onClick={() => setToasts(prev => prev.filter(x => x._id !== t._id))}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--gray-400)' }}>
              <X size={15} />
            </button>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.82rem' }}>
            <div><strong>{t.turbine_id}</strong> - {t.anomaly_type}</div>
            <div className="text-muted text-sm">Skor: {Math.round((t.anomaly_score || 0) * 100)}%</div>
          </div>
        </div>
      ))}
    </div>
  );
}
