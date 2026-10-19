export type ProjectStatus = 'draft' | 'generating' | 'rendering' | 'complete' | 'failed';

export type PipelineStageStatus = 'pending' | 'running' | 'complete' | 'failed' | 'skipped';

export type Audience = 'beginner' | 'intermediate' | 'advanced';
export type VisualStyle = 'cinematic' | 'educational' | 'minimal' | 'corporate';
export type Pacing = 'slow' | 'moderate' | 'fast';

export interface Project {
  id: string;
  name: string;
  topic: string;
  subtopic: string;
  user_explanation: string;
  target_duration_minutes: number;
  target_audience: Audience;
  visual_style: VisualStyle;
  pacing: Pacing;
  status: ProjectStatus;
  current_stage: string;
  progress_pct: number;
  error_message: string | null;
  final_video_path: string | null;
  thumbnail_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  topic: string;
  subtopic: string;
  user_explanation: string;
  target_duration_minutes: number;
  target_audience: Audience;
  visual_style: VisualStyle;
  pacing: Pacing;
}

export interface StageRun {
  id: string;
  project_id: string;
  stage_name: string;
  status: PipelineStageStatus;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  output_artifacts: Record<string, any>;
}

export interface PipelineEvent {
  type: 'started' | 'progress' | 'stage_complete' | 'complete' | 'failed';
  project_id: string;
  stage_name: string;
  stage_index: number;
  total_stages: number;
  message: string;
  progress_pct: number;
  timestamp: number;
}

export interface Scene {
  scene_id: string;
  scene_type: string;
  title: string;
  script_text: string;
  duration_seconds: number;
  html_path: string | null;
  narration_path: string | null;
  transition_in: string;
  transition_out: string;
  effect: string;
}

export interface Chapter {
  chapter_number: number;
  title: string;
  summary: string;
  duration_seconds: number;
  scenes: Scene[];
  video_path: string | null;
}

export const PIPELINE_STAGES = [
  { key: 'research', label: 'Research', icon: 'search' },
  { key: 'proposal', label: 'Proposal', icon: 'file-text' },
  { key: 'script', label: 'Script', icon: 'type' },
  { key: 'chapterize', label: 'Chapters', icon: 'book-open' },
  { key: 'scene_plan', label: 'Scenes', icon: 'layout' },
  { key: 'assets', label: 'Assets', icon: 'image' },
  { key: 'edit', label: 'Edit', icon: 'film' },
  { key: 'compose', label: 'Compose', icon: 'play-circle' },
  { key: 'publish', label: 'Publish', icon: 'upload' },
] as const;
