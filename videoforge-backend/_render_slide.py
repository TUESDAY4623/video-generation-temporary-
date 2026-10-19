"""Standalone HTML-slide to video recorder (run in own process).

Records the HTML page (with its JS-driven sub-slide carousel) for the given
duration using Playwright's native video recording, then exits.
"""
import sys
import time
from pathlib import Path

html_path = Path(sys.argv[1])
duration = float(sys.argv[2])
width = int(sys.argv[3])
height = int(sys.argv[4])
record_dir = Path(sys.argv[5])

try:
    from playwright.sync_api import sync_playwright

    # Allow small extra time so the last slide transitions complete
    record_duration = duration + 1.0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--disable-web-security",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            record_video_dir=str(record_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        page.goto(f"file:///{html_path.as_posix()}")
        # Wait for page load + JS to initialize
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Wait for the required duration while animations run
        time.sleep(record_duration)

        # Save the video
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()

    # Move the video to a predictable location
    import shutil
    final_path = record_dir / "output.webm"
    shutil.move(video_path, str(final_path))
    print("OK")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
