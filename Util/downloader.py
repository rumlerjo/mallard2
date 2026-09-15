import os
import asyncio
from yt_dlp import YoutubeDL
from typing import Tuple, Callable, Optional
from dataclasses import dataclass
import logging
from discord import Interaction
from yt_dlp.networking.impersonate import ImpersonateTarget


class AsyncVideoProcessor:
    """
    Asynchronous video downloader & processor using yt-dlp and ffmpeg.
    """

    def __init__(self, url: str, ffmpeg_path="ffmpeg.exe", ffprobe_path="ffprobe.exe") -> 'AsyncVideoProcessor':

        self.url = url
        self.filepath = None

        self.ffmpeg = self._resolve_absolute_path(ffmpeg_path)
        self.ffprobe = self._resolve_absolute_path(ffprobe_path)


    def _resolve_absolute_path(self, path: str) -> str:
        """
        Resolve file path from relative to absolute.
        This is required for asyncio.create_subprocess_exec to find ffmpeg and ffprobe.
        Assumes executables are packaged within the software's root directory.
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


    async def _run_ffmpeg(self, *args) -> Tuple[bytes, bytes]:
        """
        Runs ffmpeg in a subprocess
        
        :param args: Arguments for ffmpeg
        :return: Stdout and Stderr as bytes
        """
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


    async def _run_ffprobe(self, *args) -> float:
        """
        Runs ffprobe in a subprocess to get video duration
        
        :param args: Arguments for ffprobe
        :return: Output and errors from ffmpeg run as bytes
        """
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
    
    
    async def get_estimated_download_size(self) -> float:
        """
        Estimates the download size in megabytes without downloading.
        Uses yt-dlp metadata only.
        
        :return: Estimated filesize in megabytes. Returns 0.0 if unable to estimate.
        """
        def extract_helper():
            ydl_opts = {
                "format": "mp4/bestvideo+bestaudio",
                "skip_download": True,
                "verbose": True,
                "ffmpeg_location": self.ffmpeg
            }

            # Safely resolve cookie path without triggering the Executable check
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cookie_path = os.path.join(base_dir, "Cookies", "cookies.txt")

            # platform-specific injection
            if "twitter.com" in self.url or "x.com" in self.url:
                ydl_opts["cookiefile"] = cookie_path
                ydl_opts["extractor_args"] = {"twitter": {"api": ["graphql", "syndication", "guest"]}}
                
            elif "instagram.com" in self.url:
                # ydl_opts["impersonate"] = "chrome"
                ydl_opts["cookiefile"] = cookie_path
                
            elif "tiktok.com" in self.url:
                ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            total_bytes = 0

            if "requested_formats" in info:
                for fmt in info.get("requested_formats"):
                    size = fmt.get("filesize") or fmt.get("filesize_approx")
                    if size:
                        total_bytes += size
            else:
                size = info.get("filesize") or info.get("filesize_approx")
                if size:
                    total_bytes = size

            if total_bytes == 0:
                duration = info.get("duration")
                tbr = info.get("tbr")  # total bitrate (kbps)
                if duration and tbr:
                    total_bytes = int((tbr * 1000 / 8) * duration)

            # many social media sites won't provide size before download.
            return total_bytes

        size_bytes = await asyncio.to_thread(extract_helper)
        return size_bytes / (1024 ** 2) if size_bytes > 0 else 0.0


    async def download(self, output_dir="./Util/VideoDownloads") -> str:
        """
        Download an MP4 video from this object's specified URL
        
        :param output_dir: Output directory for resulting file
        :return: File path to downloaded video
        """
        os.makedirs(output_dir, exist_ok=True) # exist_ok passes exceptions for existing directory

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "format": "mp4/bestvideo+bestaudio",
            "merge_output_format": "mp4",
            "verbose": True,
            "ffmpeg_location": self.ffmpeg
        }

        # Safely resolve cookie path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cookie_path = os.path.join(base_dir, "Cookies", "cookies.txt")

        # platform-specific injection
        if "twitter.com" in self.url or "x.com" in self.url:
            ydl_opts["cookiefile"] = cookie_path
            ydl_opts["extractor_args"] = {"twitter": {"api": ["graphql", "syndication", "guest"]}}
            
        elif "instagram.com" in self.url:
            # ydl_opts["impersonate"] = "chrome"
            ydl_opts["cookiefile"] = cookie_path
            
        elif "tiktok.com" in self.url:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")

        def download_helper():
            ydl = YoutubeDL(ydl_opts)
            info = ydl.extract_info(self.url, download=True)
            return os.path.abspath(ydl.prepare_filename(info))

        self.filepath = await asyncio.to_thread(download_helper)
        return self.filepath


    async def convert_to_mp3(self) -> str:
        """
        Converts a downloaded MP4 file to MP3
        :return: File path of MP3 file
        """
        if not self.filepath:
            raise ValueError("No file downloaded yet.")

        base, _ = os.path.splitext(self.filepath)
        output_path = base + ".mp3"

        # -y auto confirm (like in most scripts)
        # -i input path, in this case our filepath
        # -vn disables video
        # -acodec sets codec, LAME is a open source mp3 encoder
        # -q:a specifies audio quality from 0-6, with lower being higher quality
        await self._run_ffmpeg(
            "-y",
            "-i", self.filepath,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            output_path
        )
        
        self.cleanup_file() # Clean up original MP4
        self.filepath = output_path
        return output_path


    async def convert_to_gif(self, fps: int = 15, scale: int = 480) -> str:
        """
        Converts the downloaded video to a GIF using a high-quality palette filter.
        
        :param fps: Frames per second for the resulting GIF
        :param scale: Width resolution (height is auto-scaled)
        :return: File path of the GIF file
        """
        if not self.filepath:
            raise ValueError("No file downloaded yet.")

        base, _ = os.path.splitext(self.filepath)
        output_path = f"{base}.gif"

        # uses FFmpeg's palettegen and paletteuse for much better looking GIFs
        filter_complex = f"fps={fps},scale={scale}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"

        await self._run_ffmpeg(
            "-y",
            "-i", self.filepath,
            "-vf", filter_complex,
            "-loop", "0",
            output_path
        )
        
        self.cleanup_file() # Clean up original MP4
        self.filepath = output_path
        return output_path


    async def compress_to_size(self, target_mb: float) -> str:
        """
        Compresses processed file to a target size
        
        :param target_mb: Target compressed size in megabytes
        :return: Filepath of compressed file
        """
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
        
        # calculate overall bitrate, then subtract standard audio bitrate (e.g. 128kbps)
        # to ensure the final file doesn't slightly overshoot the limit.
        overall_target_bitrate = (target_bytes * 8) / duration
        audio_bitrate = 128000
        video_target_bitrate = overall_target_bitrate - audio_bitrate
        
        # ensure bitrate doesn't dip below a baseline to prevent complete failure
        video_target_bitrate = max(100000, video_target_bitrate) 
        target_bitrate_k = int(video_target_bitrate / 1000)

        base, ext = os.path.splitext(self.filepath)
        output_path = f"{base}_compressed{ext}"

        await self._run_ffmpeg(
            "-y",
            "-i", self.filepath,
            "-b:v", f"{target_bitrate_k}k",
            "-b:a", "128k", # Force audio bitrate consistency
            "-bufsize", f"{target_bitrate_k * 2}k", # Standard ffmpeg practice
            output_path
        )

        self.cleanup_file()

        self.filepath = output_path
        return output_path
    

    def get_filesize(self) -> float:
        """
        Gets the filesize of video downloaded
        
        :return: Filesize in megabytes
        """
        if self.filepath and os.path.exists(self.filepath):
            file_size = os.path.getsize(self.filepath) # returns in bytes
            return float(file_size / 1024 ** 2)
        return 0.0


    def cleanup_file(self) -> None:
        """
        Removes created file
        """
        if self.filepath and os.path.exists(self.filepath):
            os.remove(self.filepath)


    def cleanup_download_dir(self, cleanup_dir: str="./Util/VideoDownloads") -> None:
        """
        Removes all files in a specified directory
        :param cleanup_dir: path to directory as string
        """
        if os.path.exists(cleanup_dir):
            for file in os.listdir(cleanup_dir):
                file_path = os.path.join(cleanup_dir, file)
                if os.path.isfile(file_path): # Prevent crashing on subdirectories
                    os.remove(file_path)

@dataclass
class VideoJob:
    url: str
    target_mb: Optional[float] = None
    to_mp3: bool = False
    to_gif: bool = False
    complete_callback: Optional[Callable[[str, bool, Interaction], None]] = None
    file_too_large_callback: Optional[Callable[[Interaction], None]] = None
    error_callback: Optional[Callable[[Exception, Interaction], None]] = None
    delay_reply_callback: Optional[Callable[[Interaction], None]] = None
    interaction: Optional[Interaction] = None

class VideoProcessingQueue:
    """
    Creates a queue for processing video jobs
    """
    MAX_COMPRESSION_MULT = 3
    MB_DELAY_REPLY = 25.00

    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue[VideoJob] = asyncio.Queue()
        self.next_queued: int = 0
        self.workers: list[asyncio.Task] = []
        self.started = False

    def start(self) -> None:
        """
        Starts download workers
        """
        if self.started:
            return

        self.started = True
        for i in range(self.max_concurrent):
            self.workers.append(asyncio.create_task(self._worker(i)))

    async def stop(self) -> None:
        """
        Stops download workers
        """
        for _ in range(self.max_concurrent):
            await self.queue.put(None)

        await self.queue.join()

        for task in self.workers:
            task.cancel()

        self.workers.clear()
        self.started = False

    async def enqueue(self, job: VideoJob) -> None:
        """
        Enqueues a video job to the queue to be worked
        :param job: A VideoJob containing information about the video download
        """
        if not self.started:
            raise RuntimeError("Queue not started")

        self.next_queued += 1

        await self.queue.put(job)

    async def _worker(self, worker_id: int) -> None:
        """
        Creates a queue worker

        :param worker_id: id of the worker being created
        """
        try:
            while True:
                job = await self.queue.get()

                if job is None:
                    self.queue.task_done()
                    break

                try:
                    await self._process_job(job)
                except Exception as e:
                    if job.error_callback:
                        await job.error_callback(e, job.interaction)
                    else:
                        logging.exception(f"Worker {worker_id}: job failed")

                self.next_queued -= 1
                self.queue.task_done()

        except asyncio.CancelledError:
            pass

    async def _process_job(self, job: VideoJob):
        """
        Process a video download job
        
        :param job: Job information for a download
        """
        processor = AsyncVideoProcessor(job.url)
        compressed = False

        estimated_dl_size = await processor.get_estimated_download_size()

        # If size > 0, it means we got valid metadata. If 0, we skip the check and download anyway.
        if job.target_mb and estimated_dl_size > 0:
            if estimated_dl_size > self.MAX_COMPRESSION_MULT * job.target_mb:
                if job.file_too_large_callback:
                    await job.file_too_large_callback(job.interaction)
                return
            
            if estimated_dl_size >= self.MB_DELAY_REPLY:
                if job.delay_reply_callback:
                    await job.delay_reply_callback(job.interaction)

        path = await processor.download()

        # In case estimation failed, perform the size check post-download
        actual_size = processor.get_filesize()
        if job.target_mb and estimated_dl_size == 0.0:
            if actual_size > self.MAX_COMPRESSION_MULT * job.target_mb:
                if job.file_too_large_callback:
                    await job.file_too_large_callback(job.interaction)
                processor.cleanup_file()
                return

        if job.to_mp3:
            path = await processor.convert_to_mp3()
        elif job.to_gif:
            path = await processor.convert_to_gif()

        # Re-check size after format conversion
        if job.target_mb and job.target_mb < processor.get_filesize():
            # Don't try to compress GIFs or MP3s using standard video bitrates
            if not job.to_mp3 and not job.to_gif:
                path = await processor.compress_to_size(job.target_mb)
                compressed = True

        if job.complete_callback:
            await job.complete_callback(path, compressed, job.interaction)

        processor.cleanup_file()

    def next_queue_position(self) -> int:
        """
        Determines what the next queue position would be should an enqueue execute
        
        :return: Next queue position
        """
        return self.next_queued

    def would_enqueue_wait(self) -> bool:
        """
        Determines if an enqueue would queue based on the number of workers
        
        :return: True if enqueue would wait
        """
        return self.next_queue_position() >= self.max_concurrent