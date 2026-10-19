import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Pause, Volume2, Maximize, SkipBack, SkipForward,
  List, LayoutGrid
} from 'lucide-react';
import { useProjectStore } from '../stores/projectStore';
import { getVideoUrl } from '../services/api';
import { Chapter } from '../types';

export default function VideoPlayer() {
  const { id } = useParams<{ id: string }>();
  const { projects } = useProjectStore();
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showTimeline, setShowTimeline] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  const project = projects.find((p) => p.id === id);
  const videoUrl = getVideoUrl(project?.final_video_path ?? null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTime = () => setCurrentTime(video.currentTime);
    const onDuration = () => setDuration(video.duration);
    const onEnd = () => setPlaying(false);

    video.addEventListener('timeupdate', onTime);
    video.addEventListener('loadedmetadata', onDuration);
    video.addEventListener('ended', onEnd);
    return () => {
      video.removeEventListener('timeupdate', onTime);
      video.removeEventListener('loadedmetadata', onDuration);
      video.removeEventListener('ended', onEnd);
    };
  }, [videoUrl]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) videoRef.current.pause();
    else videoRef.current.play();
    setPlaying(!playing);
  };

  const seek = (time: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = time;
    setCurrentTime(time);
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  // Mock chapters for timeline
  const chapters: Chapter[] = project
    ? [
        {
          chapter_number: 1,
          title: project.topic,
          summary: '',
          duration_seconds: 300,
          scenes: [],
          video_path: project.final_video_path,
        },
      ]
    : [];

  const _totalDuration = chapters.reduce(
    (sum, c) => sum + c.duration_seconds,
    0
  );

  return (
    <div className="max-w-6xl mx-auto p-8">
      {/* Video Player */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-black rounded-2xl overflow-hidden mb-6"
      >
        {videoUrl ? (
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full aspect-video"
            controls={false}
          />
        ) : (
          <div className="w-full aspect-video flex items-center justify-center bg-dark-2">
            <p className="text-slate-500">No video available</p>
          </div>
        )}

        {/* Controls */}
        <div className="bg-dark-2/90 backdrop-blur px-6 py-4">
          {/* Progress bar */}
          <div
            className="h-1.5 bg-dark-3 rounded-full mb-4 cursor-pointer group"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const pct = (e.clientX - rect.left) / rect.width;
              seek(pct * duration);
            }}
          >
            <div
              className="h-full bg-primary rounded-full relative"
              style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
            >
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => seek(Math.max(0, currentTime - 10))} className="text-slate-400 hover:text-white">
                <SkipBack size={22} />
              </button>
              <button
                onClick={togglePlay}
                disabled={!videoUrl}
                className="w-12 h-12 bg-white text-dark rounded-full flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-50"
              >
                {playing ? <Pause size={22} /> : <Play size={22} className="ml-1" />}
              </button>
              <button onClick={() => seek(Math.min(duration, currentTime + 10))} className="text-slate-400 hover:text-white">
                <SkipForward size={22} />
              </button>
              <span className="text-sm text-slate-400 font-mono">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Volume2 size={18} className="text-slate-400" />
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={volume}
                  onChange={(e) => {
                    setVolume(parseFloat(e.target.value));
                    if (videoRef.current) videoRef.current.volume = parseFloat(e.target.value);
                  }}
                  className="w-20 accent-primary"
                />
              </div>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className={`p-2 rounded-lg transition-colors ${showTimeline ? 'text-primary bg-primary/10' : 'text-slate-400 hover:text-white'}`}
              >
                {showTimeline ? <List size={20} /> : <LayoutGrid size={20} />}
              </button>
              <button className="text-slate-400 hover:text-white">
                <Maximize size={20} />
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Timeline */}
      <AnimatePresence>
        {showTimeline && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card"
          >
            <h3 className="text-lg font-semibold text-white mb-4">Timeline</h3>
            <div className="space-y-2">
              {chapters.map((chapter) => (
                <div key={chapter.chapter_number} className="border-l-2 border-primary pl-4">
                  <p className="text-sm font-medium text-white">
                    Chapter {chapter.chapter_number}: {chapter.title}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatTime(chapter.duration_seconds)}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
