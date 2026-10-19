import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Film, FolderOpen, Plus, Settings, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { motion } from 'framer-motion';

const navItems = [
  { to: '/', icon: FolderOpen, label: 'Projects' },
  { to: '/create', icon: Plus, label: 'New Project' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <motion.aside
        className="bg-dark-2 border-r border-dark-3 flex flex-col"
        animate={{ width: sidebarOpen ? 240 : 72 }}
        transition={{ duration: 0.2 }}
      >
        <div className="flex items-center h-16 px-4 border-b border-dark-3">
          <Film className="text-primary shrink-0" size={28} />
          {sidebarOpen && (
            <motion.span
              className="ml-3 text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              VideoForge
            </motion.span>
          )}
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary/15 text-primary'
                    : 'text-slate-400 hover:text-white hover:bg-dark-3'
                }`
              }
            >
              <Icon size={20} className="shrink-0" />
              {sidebarOpen && <span className="font-medium">{label}</span>}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="m-3 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-dark-3 transition-colors"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </motion.aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {location.pathname !== '/' && (
          <header className="h-16 bg-dark-2/80 backdrop-blur border-b border-dark-3 flex items-center px-6">
            <h1 className="text-lg font-semibold text-white">
              {location.pathname === '/create' && 'New Project'}
              {location.pathname.startsWith('/project/') && 'Pipeline'}
              {location.pathname === '/settings' && 'Settings'}
            </h1>
          </header>
        )}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
