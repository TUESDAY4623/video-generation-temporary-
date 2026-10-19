import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import CreateProject from './pages/CreateProject';
import PipelineMonitor from './pages/PipelineMonitor';
import VideoPlayer from './pages/VideoPlayer';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/create" element={<CreateProject />} />
        <Route path="/project/:id" element={<PipelineMonitor />} />
        <Route path="/project/:id/watch" element={<VideoPlayer />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
