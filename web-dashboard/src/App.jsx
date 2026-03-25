import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { LanguageProvider } from './hooks/useLanguage';
import Layout from './components/Layout';
import AlertToast from './components/AlertToast';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import { TurbineList, TurbineDetail } from './pages/Turbines';
import Alerts from './pages/Alerts';

export default function App() {
  const { user, loading, login, logout } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <LanguageProvider>
        <Login onLogin={login} />
      </LanguageProvider>
    );
  }

  return (
    <LanguageProvider>
      <BrowserRouter>
        <div className="bg-grid"></div>
        <div className="bg-glow"></div>
        <div className="bg-glow-2"></div>
        <Layout onLogout={logout} user={user}>
          <AlertToast />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/turbines" element={<TurbineList />} />
            <Route path="/turbines/:turbineId" element={<TurbineDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </LanguageProvider>
  );
}
