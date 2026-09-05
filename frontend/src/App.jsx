import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import InboxPage from './pages/InboxPage';
import IncidentDetailPage from './pages/IncidentDetailPage';
import EquipmentListPage from './pages/EquipmentListPage';
import EquipmentDetailPage from './pages/EquipmentDetailPage';
import AiChatPage from './pages/AiChatPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/incidents" element={<InboxPage />} />
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
        <Route path="/equipment" element={<EquipmentListPage />} />
        <Route path="/equipment/:id" element={<EquipmentDetailPage />} />
        <Route path="/ai" element={<AiChatPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}