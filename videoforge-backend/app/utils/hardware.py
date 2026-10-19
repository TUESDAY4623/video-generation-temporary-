"""Dynamic Hardware Detection and Adaptive Quality Profiler for VideoForge.

Analyzes the user's host system (CPU cores, RAM, GPU availability, VRAM, and FFmpeg
hardware encoder support) and dynamically selects the optimal video quality settings:
- Resolution: up to 2K (2560x1440) for high-end systems, 1080p for medium, 720p for low.
- Frame Rate: up to 60 FPS for high-end systems, 30 FPS for low.
- Words Per Minute: strictly fixed at 150 WPM.
- GPU Video Encoding: probes and utilizes hardware encoders (NVENC, AMF, QSV, VideoToolbox, MediaFoundation)
  with seamless zero-crash fallback to CPU (libx264).
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("videoforge.hardware")


@dataclass
class HardwareSpecs:
    """Raw system specifications detected at runtime."""
    os_name: str
    os_version: str
    cpu_model: str
    cpu_physical_cores: int
    cpu_logical_cores: int
    ram_total_gb: float
    ram_available_gb: float
    gpus: List[Dict[str, Any]] = field(default_factory=list)
    has_dedicated_gpu: bool = False
    working_hw_encoders: List[str] = field(default_factory=list)
    primary_encoder: str = "libx264"
    is_hw_accelerated: bool = False


@dataclass
class QualityProfile:
    """Adaptive video rendering and encoding profile determined from hardware."""
    tier: str  # 'ultra', 'medium', 'low'
    width: int
    height: int
    fps: int
    wpm: int = 150  # Strictly fixed at 150 words per minute
    video_encoder: str = "libx264"
    fallback_encoder: str = "libx264"
    is_gpu_accelerated: bool = False
    video_bitrate: str = "12M"
    max_workers: int = 4
    playwright_gpu_args: List[str] = field(default_factory=list)
    system_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemProfiler:
    """Cross-platform dynamic system hardware detection and adaptive profiler."""

    _cached_specs: Optional[HardwareSpecs] = None
    _cached_profile: Optional[QualityProfile] = None

    @classmethod
    def get_specs(cls, force_refresh: bool = False) -> HardwareSpecs:
        """Detect and return host system hardware specifications."""
        if cls._cached_specs is not None and not force_refresh:
            return cls._cached_specs

        os_name = platform.system()
        os_version = platform.release()
        cpu_model = platform.processor() or "Unknown CPU"

        # CPU Cores
        try:
            import psutil
            cpu_logical = psutil.cpu_count(logical=True) or (os.cpu_count() or 4)
            cpu_physical = psutil.cpu_count(logical=False) or max(1, cpu_logical // 2)
            vm = psutil.virtual_memory()
            ram_total_gb = round(vm.total / (1024 ** 3), 2)
            ram_avail_gb = round(vm.available / (1024 ** 3), 2)
        except Exception:
            cpu_logical = os.cpu_count() or 4
            cpu_physical = max(1, cpu_logical // 2)
            ram_total_gb = 8.0
            ram_avail_gb = 4.0

        # GPU Detection
        gpus: List[Dict[str, Any]] = []
        has_dedicated_gpu = False

        # 1. Try nvidia-smi
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        name = parts[0]
                        vram_mb = float(parts[1]) if parts[1].replace(".", "").isdigit() else 0
                        driver = parts[2] if len(parts) > 2 else "unknown"
                        gpus.append({
                            "vendor": "NVIDIA",
                            "name": name,
                            "vram_gb": round(vram_mb / 1024, 2),
                            "driver": driver,
                            "is_dedicated": True,
                        })
                        has_dedicated_gpu = True
        except Exception:
            pass

        # 2. Windows PowerShell CIM check for additional / non-NVIDIA GPUs
        if os_name == "Windows" and not gpus:
            try:
                ps_cmd = (
                    "Get-CimInstance Win32_VideoController | "
                    "Select-Object -Property Name,AdapterRAM,DriverVersion | ConvertTo-Json"
                )
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                    capture_output=True, text=True, timeout=5
                )
                if res.returncode == 0 and res.stdout.strip():
                    raw_data = json.loads(res.stdout.strip())
                    items = raw_data if isinstance(raw_data, list) else [raw_data]
                    for it in items:
                        name = str(it.get("Name", ""))
                        if not name:
                            continue
                        ram_bytes = it.get("AdapterRAM", 0) or 0
                        vram_gb = round(float(ram_bytes) / (1024 ** 3), 2) if ram_bytes > 0 else 0.0
                        driver = str(it.get("DriverVersion", "unknown"))
                        vendor = "Unknown"
                        is_dedicated = False
                        if "nvidia" in name.lower():
                            vendor = "NVIDIA"
                            is_dedicated = True
                        elif "amd" in name.lower() or "radeon" in name.lower():
                            vendor = "AMD"
                            is_dedicated = True
                        elif "intel" in name.lower():
                            vendor = "Intel"
                            is_dedicated = "arc" in name.lower() or "iris" in name.lower()
                        
                        if is_dedicated:
                            has_dedicated_gpu = True

                        gpus.append({
                            "vendor": vendor,
                            "name": name,
                            "vram_gb": vram_gb,
                            "driver": driver,
                            "is_dedicated": is_dedicated,
                        })
            except Exception:
                pass

        # 3. Linux lspci check
        if os_name == "Linux" and not gpus:
            try:
                res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if any(k in line.lower() for k in ["vga", "3d", "display"]):
                            gpus.append({"vendor": "Linux GPU", "name": line.split(":")[-1].strip(), "vram_gb": 0, "is_dedicated": True})
                            has_dedicated_gpu = True
            except Exception:
                pass

        # 4. macOS system_profiler check
        if os_name == "Darwin" and not gpus:
            try:
                res = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"], capture_output=True, text=True, timeout=4)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    displays = data.get("SPDisplaysDataType", [])
                    for d in displays:
                        name = d.get("sppci_model", d.get("_name", "Apple GPU"))
                        gpus.append({"vendor": "Apple", "name": name, "vram_gb": 0, "is_dedicated": True})
                        has_dedicated_gpu = True
            except Exception:
                pass

        # Probe FFmpeg Hardware Encoders
        working_hw_encoders, primary_encoder, is_hw_accel = cls._probe_working_ffmpeg_encoders()

        specs = HardwareSpecs(
            os_name=os_name,
            os_version=os_version,
            cpu_model=cpu_model,
            cpu_physical_cores=cpu_physical,
            cpu_logical_cores=cpu_logical,
            ram_total_gb=ram_total_gb,
            ram_available_gb=ram_avail_gb,
            gpus=gpus,
            has_dedicated_gpu=has_dedicated_gpu,
            working_hw_encoders=working_hw_encoders,
            primary_encoder=primary_encoder,
            is_hw_accelerated=is_hw_accel,
        )
        cls._cached_specs = specs
        return specs

    @classmethod
    def _probe_working_ffmpeg_encoders(cls) -> Tuple[List[str], str, bool]:
        """Probes the host FFmpeg installation to verify which hardware encoders actually execute."""
        candidate_encoders = [
            "h264_nvenc",        # NVIDIA GPU
            "h264_amf",          # AMD GPU
            "h264_qsv",          # Intel Quick Sync
            "h264_videotoolbox", # Apple Silicon
            "h264_mf",           # Windows Media Foundation (DirectX GPU)
            "h264_vaapi",        # Linux VAAPI
        ]

        # First check if ffmpeg is in PATH
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        try:
            check = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, timeout=3)
            if check.returncode != 0:
                return [], "libx264", False
        except Exception:
            return [], "libx264", False

        # Get compiled encoders list
        try:
            enc_out = subprocess.run([ffmpeg_bin, "-encoders"], capture_output=True, text=True, timeout=3).stdout
        except Exception:
            enc_out = ""

        available_candidates = [e for e in candidate_encoders if e in enc_out]
        working_encoders: List[str] = []

        # Perform micro-encode probe on available candidates
        with tempfile.TemporaryDirectory(prefix="vf_enc_probe_") as tmpdir:
            for enc in available_candidates:
                probe_mp4 = Path(tmpdir) / f"probe_{enc}.mp4"
                cmd = [
                    ffmpeg_bin, "-y",
                    "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
                    "-c:v", enc,
                    "-pix_fmt", "yuv420p",
                    "-t", "0.2",
                    str(probe_mp4),
                ]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if res.returncode == 0 and probe_mp4.exists() and probe_mp4.stat().st_size > 1000:
                        working_encoders.append(enc)
                        logger.info("✓ Hardware encoder verified working: %s", enc)
                except Exception:
                    continue

        if working_encoders:
            return working_encoders, working_encoders[0], True
        return [], "libx264", False

    @classmethod
    def get_profile(cls, force_refresh: bool = False) -> QualityProfile:
        """Determines the adaptive QualityProfile tailored strictly to host system specs."""
        if cls._cached_profile is not None and not force_refresh:
            return cls._cached_profile

        specs = cls.get_specs(force_refresh=force_refresh)

        # Base Chromium launch arguments for GPU acceleration
        base_playwright_args = [
            "--disable-web-security",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--autoplay-policy=no-user-gesture-required",
        ]

        # ── Hardware Evaluation ────────────────────────────────────────────────
        # Criteria for ULTRA (High specs):
        # 1. Has dedicated GPU OR confirmed working hardware video encoder
        # 2. RAM >= 12.0 GB
        # 3. CPU Logical Cores >= 8
        is_high_end = (
            (specs.has_dedicated_gpu or specs.is_hw_accelerated) and
            specs.ram_total_gb >= 12.0 and
            specs.cpu_logical_cores >= 8
        )

        # Criteria for MEDIUM (Mid specs):
        # 1. RAM >= 7.5 GB
        # 2. CPU Logical Cores >= 4
        is_mid_end = (specs.ram_total_gb >= 7.5 and specs.cpu_logical_cores >= 4)

        if is_high_end:
            tier = "ultra"
            width, height = 2560, 1440  # 2K resolution as requested
            fps = 60                   # 60 FPS as requested
            bitrate = "14M"
            workers = min(4, max(2, specs.cpu_logical_cores // 4))
            gpu_args = base_playwright_args + [
                "--enable-gpu-rasterization",
                "--ignore-gpu-blocklist",
                "--enable-zero-copy",
            ]
            summary = (
                f"High-End System: 2K QHD (2560x1440) @ 60 FPS, {specs.primary_encoder} GPU acceleration, "
                f"{workers} workers, 150 WPM"
            )

        elif is_mid_end:
            tier = "medium"
            width, height = 1920, 1080  # 1080p Full HD
            fps = 60 if specs.is_hw_accelerated else 30
            bitrate = "7M"
            workers = min(4, max(2, specs.cpu_logical_cores // 4))
            gpu_args = base_playwright_args + (
                ["--enable-gpu-rasterization", "--ignore-gpu-blocklist"]
                if (specs.has_dedicated_gpu or specs.is_hw_accelerated) else []
            )
            summary = (
                f"Mid-Range System: 1080p FHD (1920x1080) @ {fps} FPS, {specs.primary_encoder}, "
                f"{workers} workers, 150 WPM"
            )

        else:
            tier = "low"
            width, height = 1280, 720   # 720p HD
            fps = 30
            bitrate = "3M"
            workers = min(2, max(1, specs.cpu_logical_cores // 2))
            gpu_args = base_playwright_args
            summary = (
                f"Entry-Level System: 720p HD (1280x720) @ 30 FPS, libx264 CPU fallback, "
                f"{workers} workers, 150 WPM"
            )

        profile = QualityProfile(
            tier=tier,
            width=width,
            height=height,
            fps=fps,
            wpm=150,  # Strictly fixed at 150 WPM
            video_encoder=specs.primary_encoder,
            fallback_encoder="libx264",
            is_gpu_accelerated=specs.is_hw_accelerated,
            video_bitrate=bitrate,
            max_workers=workers,
            playwright_gpu_args=gpu_args,
            system_summary=summary,
        )

        cls._cached_profile = profile
        return profile

    @classmethod
    def print_system_banner(cls, profile: Optional[QualityProfile] = None) -> None:
        """Prints a clean, informative system diagnostics and selected quality profile banner."""
        specs = cls.get_specs()
        prof = profile or cls.get_profile()

        gpu_info = (
            ", ".join(f"{g.get('name', 'GPU')} ({g.get('vram_gb', 0)}GB VRAM)" for g in specs.gpus)
            if specs.gpus else "Integrated / No dedicated GPU detected"
        )
        encoders_info = (
            ", ".join(specs.working_hw_encoders) if specs.working_hw_encoders else "None (libx264 CPU fallback)"
        )

        print("\n" + "=" * 70)
        print("  [VIDEOFORGE DYNAMIC SYSTEM BENCHMARK & HARDWARE PROFILER]")
        print("=" * 70)
        print(f"  OS Platform:     {specs.os_name} {specs.os_version}")
        print(f"  CPU Cores:       {specs.cpu_logical_cores} logical ({specs.cpu_physical_cores} physical)")
        print(f"  RAM Memory:      {specs.ram_total_gb} GB total ({specs.ram_available_gb} GB available)")
        print(f"  GPU Hardware:    {gpu_info}")
        print(f"  Hardware Encs:   {encoders_info}")
        print("-" * 70)
        print(f"  >> ADAPTIVE PROFILE:  [{prof.tier.upper()}]")
        print(f"  >> Resolution:        {prof.width}x{prof.height} ({'2K QHD' if prof.width >= 2560 else '1080p FHD' if prof.width >= 1920 else '720p HD'})")
        print(f"  >> Frame Rate:        {prof.fps} FPS")
        print(f"  >> Words Per Min:     {prof.wpm} WPM (Fixed)")
        print(f"  >> Primary Encoder:   {prof.video_encoder} ({'GPU Accelerated' if prof.is_gpu_accelerated else 'CPU Soft'})")
        print(f"  >> Target Bitrate:    {prof.video_bitrate}")
        print(f"  >> Parallel Workers:  {prof.max_workers}")
        print("=" * 70 + "\n")

    @classmethod
    def save_profile_to_project(cls, project_dir: Path | str, profile: Optional[QualityProfile] = None) -> Path:
        """Saves system_profile.json in the specified project directory."""
        p_dir = Path(project_dir)
        p_dir.mkdir(parents=True, exist_ok=True)
        prof = profile or cls.get_profile()
        specs = cls.get_specs()

        data = {
            "system_specs": asdict(specs),
            "quality_profile": prof.to_dict(),
        }
        dest = p_dir / "system_profile.json"
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return dest
