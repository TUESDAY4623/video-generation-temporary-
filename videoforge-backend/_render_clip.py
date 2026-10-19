import sys, time, shutil, os, json
from pathlib import Path

html_path = Path(sys.argv[1])
duration = float(sys.argv[2])
width = int(sys.argv[3])
height = int(sys.argv[4])
record_dir = Path(sys.argv[5])

try:
    from playwright.sync_api import sync_playwright
    pw_args = ["--disable-web-security", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required", "--enable-gpu-rasterization", "--ignore-gpu-blocklist", "--enable-zero-copy"]
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=pw_args)
        except Exception:
            browser = p.chromium.launch(args=["--disable-web-security", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"])
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            record_video_dir=str(record_dir),
            record_video_size={"width": width, "height": height},
            color_scheme="dark",
        )
        t_start = time.time()
        page = context.new_page()
        page.goto(f"file:///{html_path.resolve().as_posix()}", wait_until="load", timeout=15000)
        try:
            page.wait_for_selector(".screen-canvas", state="visible", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(250)
        
        t_ready = time.time()
        ready_offset = max(0.0, t_ready - t_start)
        
        while time.time() - t_ready < duration:
            page.wait_for_timeout(50)
            
        video = page.video
        page.close()
        final_path = record_dir / "output.webm"
        video.save_as(str(final_path))
        context.close()
        browser.close()
        
        meta_file = record_dir / "meta.json"
        meta_file.write_text(json.dumps({"ready_offset": ready_offset}), encoding="utf-8")
        print(f"OK:{ready_offset:.3f}")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
