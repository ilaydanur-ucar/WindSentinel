import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
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
    return <Login onLogin={login} />;
  }

  return (
    <BrowserRouter>
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
  );
}
