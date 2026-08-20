"""
MAX 2.0 — AI Image Generation Skill
Uses Pollinations.ai (free, no API key needed) to generate images from text.
"""
import os
import urllib.parse
import webbrowser
from skills.router import skill
from core.logger import log


@skill("generate_image")
def generate_image(args: dict, spoken: str) -> str:
    prompt = args.get("prompt", "") or args.get("description", "") or args.get("query", "")
    if not prompt:
        from core.voice import take_command
        prompt = take_command(prompt="What should I generate an image of?")
    if not prompt:
        return "What would you like me to draw?"

    log.info(f"Generating image: {prompt}")

    # Build Pollinations URL (free, no key needed)
    encoded = urllib.parse.quote(prompt)
    width = args.get("width", 1024)
    height = args.get("height", 768)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"

    # Open in browser so user can see and save it
    webbrowser.open(image_url)

    # Also try to download and save locally
    try:
        import requests
        import datetime
        resp = requests.get(image_url, timeout=30)
        if resp.status_code == 200:
            save_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MAX_Generated")
            os.makedirs(save_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"max_art_{ts}.jpg"
            save_path = os.path.join(save_dir, filename)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            log.info(f"Image saved: {save_path}")
            return (spoken or
                    f"Generated an image of '{prompt}'! Saved to your Pictures/MAX_Generated folder "
                    f"and opened in your browser.")
    except Exception as e:
        log.warning(f"Image download failed (still opened in browser): {e}")

    return spoken or f"Generated an image of '{prompt}' and opened it in your browser!"


@skill("edit_image")
def edit_image(args: dict, spoken: str) -> str:
    """Generate a variation on an existing concept."""
    original = args.get("original", "") or args.get("base", "")
    modification = args.get("modification", "") or args.get("change", "")

    if not original:
        from core.voice import take_command
        original = take_command(prompt="What's the base image concept?")
    if not modification:
        from core.voice import take_command
        modification = take_command(prompt="How should I modify it?")

    prompt = f"{original}, {modification}, highly detailed, photorealistic"
    return generate_image({"prompt": prompt}, spoken)
