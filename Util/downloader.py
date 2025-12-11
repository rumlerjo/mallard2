import os
import asyncio
from yt_dlp import YoutubeDL


class AsyncVideoProcessor:
    """
    Asynchronous video downloader & processor using yt-dlp and ffmpeg.
    """

    def __init__(self, url: str,
                 ffmpeg_path="ffmpeg.exe",
                 ffprobe_path="ffprobe.exe"):

        self.url = url
        self.filepath = None

        self.ffmpeg = self._resolve_absolute_path(ffmpeg_path)
        self.ffprobe = self._resolve_absolute_path(ffprobe_path)

    def _resolve_absolute_path(path: str) -> str:
        """
        Resolve file path from relative to absolute.
        This is required for asyncio.create_subprocess_exec to find ffmpeg and ffprobe.
        """
        if os.path.isabs(path):
            resolved = path
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            resolved = os.path.join(base_dir, path)

        resolved = os.path.abspath(resolved)

        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Executable not found: {resolved}")

        return resolved


    async def _run_ffmpeg(self, *args):
        process = await asyncio.create_subprocess_exec(
            self.ffmpeg,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed:\n{stderr.decode(errors='ignore')}")

        return stdout, stderr


    async def _run_ffprobe(self, *args):
        process = await asyncio.create_subprocess_exec(
            self.ffprobe,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"ffprobe failed:\n{stderr.decode(errors='ignore')}")

        return float(stdout.decode().strip())


    async def download(self, output_dir="./VideoDownloads"):

        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "format": "mp4/bestvideo+bestaudio",
        }

        def blocking_download():
            ydl = YoutubeDL(ydl_opts)
            info = ydl.extract_info(self.url, download=True)
            return os.path.abspath(ydl.prepare_filename(info))

        self.filepath = await asyncio.to_thread(blocking_download)
        return self.filepath


    async def convert_to_mp3(self):

        if not self.filepath:
            raise ValueError("No file downloaded yet.")

        base, _ = os.path.splitext(self.filepath)
        output_path = base + ".mp3"

        await self._run_ffmpeg(
            "-y",
            "-i", self.filepath,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            output_path
        )

        self.filepath = output_path
        return output_path


    async def compress_to_size(self, target_mb: float):

        if not self.filepath:
            raise ValueError("No file to compress.")

        if os.path.exists(self.filepath):
            duration = await self._run_ffprobe(
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.filepath
            )
        else:
            raise FileNotFoundError(f"Video file not found: {self.filepath}")

        target_bytes = target_mb * 1024**2
        target_bitrate = (target_bytes * 8) / duration
        target_bitrate_k = int(target_bitrate / 1000)

        base, ext = os.path.splitext(self.filepath)
        output_path = f"{base}_compressed{ext}"

        await self._run_ffmpeg(
            "-y",
            "-i", self.filepath,
            "-b:v", f"{target_bitrate_k}k",
            "-bufsize", f"{target_bitrate_k}k",
            output_path
        )

        os.remove(self.filepath)

        self.filepath = output_path
        return output_path


    def cleanup_file(self):
        if self.filepath and os.path.exists(self.filepath):
            os.remove(self.filepath)


    def cleanup_download_dir(self, cleanup_dir="./VideoDownloads"):
        if os.path.exists(cleanup_dir):
            for file in os.listdir(cleanup_dir):
                os.remove(os.path.join(cleanup_dir, file))