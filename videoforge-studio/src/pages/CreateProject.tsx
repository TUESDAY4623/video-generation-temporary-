import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2 } from 'lucide-react';
import { useProjectStore } from '../stores/projectStore';
import { createProject, startPipeline } from '../services/api';

const AUDIENCE_OPTIONS = ['beginner', 'intermediate', 'advanced'] as const;
const STYLE_OPTIONS = ['cinematic', 'educational', 'minimal', 'corporate'] as const;
const PACING_OPTIONS = ['slow', 'moderate', 'fast'] as const;

export default function CreateProject() {
  const navigate = useNavigate();
  const { addProject, selectProject } = useProjectStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    topic: '',
    subtopic: '',
    user_explanation: '',
    target_duration_minutes: 45,
    target_audience: 'intermediate' as const,
    visual_style: 'cinematic' as const,
    pacing: 'moderate' as const,
  });

  const update = (field: string, value: any) =>
    setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.topic.trim()) {
      setError('Topic is required');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const project = await createProject(form);
      addProject(project);
      selectProject(project);
      await startPipeline(project.id);
      navigate(`/project/${project.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold text-white mb-2">Create New Video</h1>
        <p className="text-slate-400 mb-8">
          Enter your topic and let AI generate a professional video
        </p>

        <form onSubmit={handleSubmit} className="card space-y-6">
          {error && (
            <div className="bg-danger/10 border border-danger/30 text-danger px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="input-label">Project Name</label>
              <input
                className="input"
                placeholder="e.g., Python Tutorial Series"
                value={form.name}
                onChange={(e) => update('name', e.target.value)}
              />
            </div>

            <div className="md:col-span-2">
              <label className="input-label">Topic *</label>
              <input
                className="input"
                placeholder="e.g., Python Programming"
                value={form.topic}
                onChange={(e) => update('topic', e.target.value)}
                required
              />
            </div>

            <div>
              <label className="input-label">Sub-topic</label>
              <input
                className="input"
                placeholder="e.g., Lists and Data Structures"
                value={form.subtopic}
                onChange={(e) => update('subtopic', e.target.value)}
              />
            </div>

            <div>
              <label className="input-label">Duration (minutes)</label>
              <input
                type="number"
                className="input"
                min={5}
                max={60}
                value={form.target_duration_minutes}
                onChange={(e) => update('target_duration_minutes', parseInt(e.target.value) || 5)}
              />
            </div>

            <div className="md:col-span-2">
              <label className="input-label">Explanation / Notes</label>
              <textarea
                className="input min-h-[120px] resize-y"
                placeholder="Describe what you want to cover, key points, or any specific requirements..."
                value={form.user_explanation}
                onChange={(e) => update('user_explanation', e.target.value)}
              />
            </div>

            <div>
              <label className="input-label">Target Audience</label>
              <select
                className="input"
                value={form.target_audience}
                onChange={(e) => update('target_audience', e.target.value)}
              >
                {AUDIENCE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt} className="bg-dark-2">
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="input-label">Visual Style</label>
              <select
                className="input"
                value={form.visual_style}
                onChange={(e) => update('visual_style', e.target.value)}
              >
                {STYLE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt} className="bg-dark-2">
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="input-label">Pacing</label>
              <select
                className="input"
                value={form.pacing}
                onChange={(e) => update('pacing', e.target.value)}
              >
                {PACING_OPTIONS.map((opt) => (
                  <option key={opt} value={opt} className="bg-dark-2">
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-dark-3">
            <p className="text-sm text-slate-500">
              Generation takes ~{Math.max(5, form.target_duration_minutes * 2)}–{Math.max(10, form.target_duration_minutes * 3)} minutes
            </p>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  Generate Video
                  <ArrowRight size={20} />
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
