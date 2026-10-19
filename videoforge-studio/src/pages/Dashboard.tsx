import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Plus, Play, Trash2, Film, Clock, User, Palette } from 'lucide-react';
import { useProjectStore } from '../stores/projectStore';
import { getVideoUrl, deleteProject } from '../services/api';
import { PIPELINE_STAGES } from '../types';

const statusConfig: Record<string, { color: string; label: string }> = {
  draft: { color: 'bg-slate-500', label: 'Draft' },
  generating: { color: 'bg-warning', label: 'Generating' },
  rendering: { color: 'bg-secondary', label: 'Rendering' },
  complete: { color: 'bg-success', label: 'Complete' },
  failed: { color: 'bg-danger', label: 'Failed' },
};

export default function Dashboard() {
  const { projects, loading, fetchProjects, removeProject } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this project?')) return;
    try {
      await deleteProject(id);
      removeProject(id);
    } catch (e) {
      console.error('Delete failed:', e);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-slate-400 mt-1">Manage your video generation projects</p>
        </div>
        <Link to="/create" className="btn-primary">
          <Plus size={20} />
          New Project
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-40 bg-dark-3 rounded-lg mb-4" />
              <div className="h-6 bg-dark-3 rounded w-3/4 mb-2" />
              <div className="h-4 bg-dark-3 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-20"
        >
          <Film size={64} className="mx-auto text-slate-600 mb-4" />
          <h2 className="text-xl font-semibold text-slate-300 mb-2">No projects yet</h2>
          <p className="text-slate-500 mb-6">Create your first AI-generated video</p>
          <Link to="/create" className="btn-primary">
            <Plus size={20} />
            Create Project
          </Link>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project, i) => {
            const status = statusConfig[project.status] || statusConfig.draft;
            const videoUrl = getVideoUrl(project.final_video_path);
            const currentStageIndex = PIPELINE_STAGES.findIndex(
              (s) => s.key === project.current_stage
            );

            return (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="card hover:border-primary/30 transition-colors group"
              >
                {/* Thumbnail / preview */}
                <div className="relative h-40 bg-dark-3 rounded-lg overflow-hidden mb-4">
                  {videoUrl ? (
                    <video
                      src={videoUrl}
                      className="w-full h-full object-cover"
                      muted
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <Film size={48} className="text-slate-600" />
                    </div>
                  )}
                  <div className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold text-white ${status.color}`}>
                    {status.label}
                  </div>
                </div>

                {/* Info */}
                <h3 className="text-lg font-semibold text-white mb-1 truncate">
                  {project.name || project.topic}
                </h3>
                <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                  {project.subtopic || project.user_explanation || 'No description'}
                </p>

                {/* Meta */}
                <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                  <span className="flex items-center gap-1">
                    <Clock size={14} />
                    {project.target_duration_minutes}m
                  </span>
                  <span className="flex items-center gap-1">
                    <User size={14} />
                    {project.target_audience}
                  </span>
                  <span className="flex items-center gap-1">
                    <Palette size={14} />
                    {project.visual_style}
                  </span>
                </div>

                {/* Progress bar */}
                {project.status === 'generating' || project.status === 'rendering' ? (
                  <div className="mb-4">
                    <div className="h-2 bg-dark-3 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-primary"
                        initial={{ width: 0 }}
                        animate={{ width: `${project.progress_pct}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {PIPELINE_STAGES[currentStageIndex]?.label || 'Processing'} — {Math.round(project.progress_pct)}%
                    </p>
                  </div>
                ) : null}

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {videoUrl ? (
                    <Link to={`/project/${project.id}`} className="btn-primary flex-1 justify-center">
                      <Play size={18} />
                      View
                    </Link>
                  ) : (
                    <Link to={`/project/${project.id}`} className="btn-secondary flex-1 justify-center">
                      View
                    </Link>
                  )}
                  <button
                    onClick={() => handleDelete(project.id)}
                    className="p-2.5 rounded-lg text-slate-400 hover:text-danger hover:bg-danger/10 transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
