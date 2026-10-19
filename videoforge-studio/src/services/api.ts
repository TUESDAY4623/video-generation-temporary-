import axios from 'axios';
import type { Project, StageRun } from '../types';

export const API_BASE = 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export interface CreateProjectData {
  name: string;
  topic: string;
  subtopic: string;
  user_explanation: string;
  target_duration_minutes: number;
  target_audience: string;
  visual_style: string;
  pacing: string;
}

// Project CRUD
export async function fetchProjects(): Promise<Project[]> {
  const { data } = await api.get('/projects');
  return data.items || data;
}

export async function fetchProject(id: string): Promise<Project> {
  const { data } = await api.get(`/projects/${id}`);
  return data;
}

export async function createProject(payload: CreateProjectData): Promise<Project> {
  const { data } = await api.post('/projects', payload);
  return data;
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

// Pipeline
export async function startPipeline(projectId: string): Promise<any> {
  const { data } = await api.post(`/pipeline/${projectId}/start`);
  return data;
}

export async function pausePipeline(projectId: string): Promise<any> {
  const { data } = await api.post(`/pipeline/${projectId}/pause`);
  return data;
}

export async function abortPipeline(projectId: string): Promise<any> {
  const { data } = await api.post(`/pipeline/${projectId}/abort`);
  return data;
}

export async function fetchPipelineStatus(projectId: string): Promise<any> {
  const { data } = await api.get(`/pipeline/${projectId}/status`);
  return data;
}

export async function fetchStageRuns(projectId: string): Promise<StageRun[]> {
  const { data } = await api.get(`/pipeline/${projectId}/stages`);
  return data;
}

// Video
export function getVideoUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${API_BASE.replace('/api/v1', '')}/static/${path}`;
}
