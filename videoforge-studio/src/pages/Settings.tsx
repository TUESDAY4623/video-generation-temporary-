import { useState } from 'react';
import { Check, Save } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Settings() {
  const [saved, setSaved] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [ttsUrl, setTtsUrl] = useState('http://localhost:8000');

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
      <p className="text-slate-400 mb-8">Configure API keys and service endpoints</p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card space-y-6"
      >
        {/* API Keys */}
        <section>
          <h3 className="text-lg font-semibold text-white mb-4">API Keys</h3>
          <div>
            <label className="input-label">Anthropic (Claude) API Key</label>
            <input
              type="password"
              className="input"
              placeholder="sk-ant-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
            <p className="text-xs text-slate-500 mt-1.5">Required for all AI generation</p>
          </div>
        </section>

        {/* Local Services */}
        <section>
          <h3 className="text-lg font-semibold text-white mb-4">Local Services</h3>
          <div className="space-y-4">
            <div>
              <label className="input-label">StyleTTS2 URL</label>
              <input
                className="input"
                value={ttsUrl}
                onChange={(e) => setTtsUrl(e.target.value)}
              />
              <p className="text-xs text-slate-500 mt-1.5">Primary TTS engine (localhost:8000)</p>
            </div>
            <div>
              <label className="input-label">Seed-VC URL</label>
              <input
                className="input"
                placeholder="http://localhost:8001"
                defaultValue="http://localhost:8001"
              />
              <p className="text-xs text-slate-500 mt-1.5">Voice cloning (optional)</p>
            </div>
            <div>
              <label className="input-label">MAA URL</label>
              <input
                className="input"
                placeholder="http://localhost:8002"
                defaultValue="http://localhost:8002"
              />
              <p className="text-xs text-slate-500 mt-1.5">Sound effects & music (optional)</p>
            </div>
          </div>
        </section>

        {/* Save button */}
        <div className="flex items-center justify-between pt-4 border-t border-dark-3">
          <AnimatePresence>
            {saved && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="text-success text-sm flex items-center gap-1.5"
              >
                <Check size={16} />
                Settings saved
              </motion.span>
            )}
          </AnimatePresence>
          <button onClick={handleSave} className="btn-primary">
            <Save size={18} />
            Save Settings
          </button>
        </div>
      </motion.div>
    </div>
  );
}
