import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Ask from './pages/Ask';
import Ingestion from './pages/Ingestion';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="search" element={<Search />} />
        <Route path="ask" element={<Ask />} />
        <Route path="ingestion" element={<Ingestion />} />
      </Route>
    </Routes>
  );
}

export default App;
