import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Play, Pause, X, Check, Loader2, Film } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useProjectStore } from '../stores/projectStore';
import {
  fetchProject, fetchPipelineStatus, fetchStageRuns,
  pausePipeline, abortPipeline, getVideoUrl
} from '../services/api';
import { PIPELINE_STAGES, PipelineEvent, StageRun, Project } from '../types';

const stageIcons: Record<string, React.ElementType> = {
  research: Film,
  proposal: Film,
  script: Film,
  chapterize: Film,
  scene_plan: Film,
  assets: Film,
  edit: Film,
  compose: Film,
  publish: Film,
};

export default function PipelineMonitor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { updateProject: _updateProject, removeProject } = useProjectStore();
  const [project, setProject] = useState<Project | null>(null);
  const [stageRuns, setStageRuns] = useState<StageRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState<string>('');
  const [activeMessage, setActiveMessage] = useState('');
  const [progressPct, setProgressPct] = useState(0);

  const loadData = useCallback(async () => {
    if (!id) return;
    try {
      const [p, status, runs] = await Promise.all([
        fetchProject(id),
        fetchPipelineStatus(id).catch(() => null),
        fetchStageRuns(id).catch(() => []),
      ]);
      setProject(p);
      setStageRuns(runs);
      if (status?.current_stage) setActiveStage(status.current_stage);
    } catch (e) {
      console.error('Failed to load pipeline:', e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // WebSocket for real-time updates
  useWebSocket<PipelineEvent>(
    id ? `ws://localhost:8000/ws/${id}` : '',
    (event) => {
      setActiveStage(event.stage_name);
      setActiveMessage(event.message);
      setProgressPct(event.progress_pct);
      loadData();
    }
  );

  // Poll fallback
  useEffect(() => {
    if (!id || activeStage) return;
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, [id, activeStage, loadData]);

  const handlePause = async () => {
    if (!id) return;
    try { await pausePipeline(id); } catch (e) { console.error(e); }
  };

  const handleAbort = async () => {
    if (!id) return;
    if (!confirm('Abort pipeline? This cannot be undone.')) return;
    try {
      await abortPipeline(id);
      removeProject(id);
      navigate('/');
    } catch (e) { console.error(e); }
  };

  const handleViewVideo = () => {
    if (project?.final_video_path) {
      const url = getVideoUrl(project.final_video_path);
      if (url) window.open(url, '_blank');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={40} className="animate-spin text-primary" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400">Project not found</p>
        <button onClick={() => navigate('/')} className="btn-primary mt-4">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const isGenerating = project.status === 'generating' || project.status === 'rendering';
  const isComplete = project.status === 'complete';
  const isFailed = project.status === 'failed';
  const stageRunMap = new Map(stageRuns.map((r) => [r.stage_name, r]));
  const currentIndex = PIPELINE_STAGES.findIndex((s) => s.key === activeStage);

  return (
    <div className="max-w-5xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={() => navigate('/')} className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-dark-3">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{project.name || project.topic}</h1>
          <p className="text-slate-400 text-sm">{project.subtopic}</p>
        </div>
        {isComplete && (
          <button onClick={handleViewVideo} className="btn-primary">
            <Play size={18} />
            Watch Video
          </button>
        )}
      </div>

      {/* Status Banner */}
      <AnimatePresence mode="wait">
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-success/10 border border-success/30 text-success px-5 py-4 rounded-xl mb-8 flex items-center gap-3"
          >
            <Check size={24} />
            <div>
              <p className="font-semibold">Video Generated Successfully</p>
              <p className="text-sm opacity-80">Your video is ready to watch</p>
            </div>
          </motion.div>
        )}
        {isFailed && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-danger/10 border border-danger/30 text-danger px-5 py-4 rounded-xl mb-8"
          >
            <p className="font-semibold">Pipeline Failed</p>
            <p className="text-sm opacity-80">{project.error_message}</p>
          </motion.div>
        )}
        {isGenerating && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card mb-8"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <Loader2 size={20} className="animate-spin text-primary" />
                <span className="font-medium text-white">{activeMessage || PIPELINE_STAGES[currentIndex]?.label || 'Processing...'}</span>
              </div>
              <span className="text-sm text-slate-400">{Math.round(progressPct)}%</span>
            </div>
            <div className="h-3 bg-dark-3 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-primary to-secondary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progressPct}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Controls */}
      {isGenerating && (
        <div className="flex gap-3 mb-8">
          <button onClick={handlePause} className="btn-secondary">
            <Pause size={18} />
            Pause
          </button>
          <button onClick={handleAbort} className="btn-secondary text-danger hover:text-danger">
            <X size={18} />
            Abort
          </button>
        </div>
      )}

      {/* Pipeline Stages */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-6">Pipeline Progress</h2>
        <div className="space-y-0">
          {PIPELINE_STAGES.map((stage, i) => {
            const run = stageRunMap.get(stage.key);
            const isActive = stage.key === activeStage;
            const isPast = i < currentIndex;
            const Icon = stageIcons[stage.key] || Film;

            const getStatus = () => {
              if (isActive && isGenerating) return 'running';
              if (run?.status === 'complete') return 'complete';
              if (run?.status === 'failed') return 'failed';
              if (isPast) return 'complete';
              return 'pending';
            };

            const status = getStatus();

            return (
              <div key={stage.key} className="flex items-center gap-4">
                {/* Connector */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                      status === 'running'
                        ? 'bg-primary text-white'
                        : status === 'complete'
                        ? 'bg-success text-white'
                        : status === 'failed'
                        ? 'bg-danger text-white'
                        : 'bg-dark-3 text-slate-500'
                    }`}
                  >
                    {status === 'running' ? (
                      <Loader2 size={20} className="animate-spin" />
                    ) : status === 'complete' ? (
                      <Check size={20} />
                    ) : status === 'failed' ? (
                      <X size={20} />
                    ) : (
                      <Icon size={20} />
                    )}
                  </div>
                  {i < PIPELINE_STAGES.length - 1 && (
                    <div
                      className={`w-0.5 h-12 ${
                        isPast || (isActive && isGenerating) ? 'bg-primary' : 'bg-dark-3'
                      }`}
                    />
                  )}
                </div>

                {/* Stage info */}
                <div className="flex-1 py-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className={`font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}>
                        {stage.label}
                      </p>
                      {run?.error_message && (
                        <p className="text-sm text-danger mt-0.5">{run.error_message}</p>
                      )}
                    </div>
                    {run && (
                      <span className="text-xs text-slate-500">
                        {Math.round(run.progress_pct)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
