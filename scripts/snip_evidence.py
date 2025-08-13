import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import List, Tuple


SNIP_DIR = os.path.join("data", "snippedvideos")
TMP_DIR = os.path.join("data", ".tmp_snip")


def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _norm_time_token(token: str) -> str:
    """Normalize a time token into HH:MM:SS string.
    Accepts forms like HH:MM:SS, HH:MM, MM:SS. Pads as needed.
    """
    token = token.strip()
    parts = token.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    if len(parts) == 2:
        # Interpret as MM:SS relative to video start
        m, s = parts
        return f"00:{int(m):02d}:{int(s):02d}"
    if len(parts) == 1 and parts[0].isdigit():
        # Treat as seconds
        total = int(parts[0])
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    # Fallback: return as-is (ffmpeg may still parse) but try to make HH:MM:SS
    return token


def _parse_range(expr: str) -> Tuple[str, str, bool]:
    """Parse an evidence time expression into (start, end, is_point_window).
    Supports:
      - "HH:MM-HH:MM" (also accepts en-dash)
      - "MM:SS-HH:MM" or "MM:SS-MM:SS"
      - "~HH:MM" or "~MM:SS" => single point, let caller convert to window
    Returns HH:MM:SS strings when possible.
    """
    expr = expr.strip()
    expr = expr.replace("–", "-")  # normalize en-dash to hyphen
    if expr.startswith("~"):
        t = expr[1:].strip()
        return _norm_time_token(t), _norm_time_token(t), True
    if "-" in expr:
        a, b = expr.split("-", 1)
        return _norm_time_token(a), _norm_time_token(b), False
    # Single token means a point; treat as point window
    return _norm_time_token(expr), _norm_time_token(expr), True


def _safe_name(t: str) -> str:
    # For filenames replace ":" with "-"
    return t.replace(":", "-")


def _run(cmd: List[str]):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    return proc.stdout


def _cleanup_partial(dest_path: str):
    try:
        # Remove target or temporary partials if present
        if os.path.exists(dest_path):
            os.remove(dest_path)
        # gcloud may leave a temp file with _ .gstmp suffix
        tmp = dest_path + "_.gstmp"
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass


def _download_gcs(gcs_uri: str, dest_path: str):
    """Download using gsutil if available, otherwise gcloud. Retry across tools if one fails."""
    has_gsutil = _which("gsutil")
    has_gcloud = _which("gcloud")
    if not (has_gsutil or has_gcloud):
        raise RuntimeError("Neither 'gcloud' nor 'gsutil' found on PATH; cannot download video from GCS.")

    errors = []
    # Prefer gsutil for stability
    if has_gsutil:
        try:
            _run(["gsutil", "cp", gcs_uri, dest_path])
            return
        except Exception as e:
            errors.append(str(e))
            _cleanup_partial(dest_path)

    if has_gcloud:
        try:
            _run(["gcloud", "storage", "cp", gcs_uri, dest_path])
            return
        except Exception as e:
            errors.append(str(e))
            _cleanup_partial(dest_path)

    # Last attempt: if both exist, try the other order once more
    if has_gsutil and has_gcloud:
        try:
            _run(["gsutil", "cp", gcs_uri, dest_path])
            return
        except Exception as e:
            errors.append(str(e))
            _cleanup_partial(dest_path)

    raise RuntimeError("GCS download failed. Attempts:\n" + "\n---\n".join(errors))


def _ffmpeg_cut(input_path: str, start_hms: str, duration_hms: str, out_path: str):
    # Use re-encode and -t duration for more reliable non-zero outputs
    _run([
        "ffmpeg", "-y",
        "-ss", start_hms,
        "-t", duration_hms,
        "-i", input_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        out_path,
    ])


def snip_evidence_for_video(
    video_id: str,
    evidence_times: List[str],
    gcs_uri: str,
    window_seconds_for_point: int = 10,
) -> List[str]:
    """Download the GCS video, snip clips per evidence time, return output clip paths.
    Cleans up the downloaded source video afterwards.
    """
    if not evidence_times:
        return []

    _ensure_dir(SNIP_DIR)
    _ensure_dir(TMP_DIR)

    # Download source video
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(TMP_DIR, f"{video_id}_{ts}.mp4")
    _download_gcs(gcs_uri, local_path)

    outputs: List[str] = []
    # Minimum duration for any clip
    min_dur = max(1, int(window_seconds_for_point))
    for et in evidence_times:
        try:
            start, end, is_point = _parse_range(et)
            # Helpers
            def to_seconds(t: str) -> int:
                h, m, s = [int(x) for x in t.split(":")]
                return h * 3600 + m * 60 + s
            def to_hms(sec: int) -> str:
                if sec < 0:
                    sec = 0
                h = sec // 3600
                m = (sec % 3600) // 60
                s = sec % 60
                return f"{h:02d}:{m:02d}:{s:02d}"
            if is_point:
                # 10s forward from the point time
                start_hms = start
                start_sec = to_seconds(start_hms)
                dur_sec = min_dur
                end_hms = to_hms(start_sec + dur_sec)
            else:
                # Use provided end but ensure at least 10s duration from start
                start_hms, end_hms = start, end
                start_sec = to_seconds(start_hms)
                end_sec = to_seconds(end_hms)
                dur_sec = max(min_dur, max(0, end_sec - start_sec))
                end_hms = to_hms(start_sec + dur_sec)

            if dur_sec <= 0:
                continue
            duration_hms = to_hms(dur_sec)
            safe_start = _safe_name(start_hms)
            safe_end = _safe_name(end_hms)
            out_path = os.path.join(SNIP_DIR, f"{video_id}__{safe_start}__{safe_end}.mp4")
            _ffmpeg_cut(local_path, start_hms, duration_hms, out_path)
            outputs.append(out_path)
        except Exception:
            # Skip bad entry but continue others
            continue

    # Cleanup source video
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
    except Exception:
        pass

    return outputs


def snip_evidence_for_offsets(
    video_id: str,
    ranges_seconds: List[Tuple[int, int]],
    gcs_uri: str,
) -> List[str]:
    """Snip given (start_sec, end_sec) ranges relative to the start of the video.
    Downloads the source, produces clips, and cleans up source.
    """
    if not ranges_seconds:
        return []

    _ensure_dir(SNIP_DIR)
    _ensure_dir(TMP_DIR)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(TMP_DIR, f"{video_id}_{ts}.mp4")
    _download_gcs(gcs_uri, local_path)

    def to_hms(sec: int) -> str:
        if sec < 0:
            sec = 0
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    outputs: List[str] = []
    for s, e in ranges_seconds:
        try:
            s = max(0, int(s))
            e = max(0, int(e))
            if e <= s:
                continue
            start_hms = to_hms(s)
            dur_hms = to_hms(e - s)
            safe_start = _safe_name(start_hms)
            safe_end = _safe_name(to_hms(e))
            out_path = os.path.join(SNIP_DIR, f"{video_id}__{safe_start}__{safe_end}.mp4")
            _ffmpeg_cut(local_path, start_hms, dur_hms, out_path)
            outputs.append(out_path)
        except Exception:
            continue

    try:
        if os.path.exists(local_path):
            os.remove(local_path)
    except Exception:
        pass

    return outputs
