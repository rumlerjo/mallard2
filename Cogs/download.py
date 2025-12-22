from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, File
from Util import AsyncVideoProcessor, VideoProcessingQueue, VideoJob
from io import BytesIO

class Download(Cog):
    """
    Contains commands for downloading from a link
    """
    def __init__(self, bot: Bot):
        """
        :param bot: discord.py Bot instance
        """
        self.bot = bot
        self.download_queue = VideoProcessingQueue() # instantiate a queue with a single worker
        self.download_queue.start()

    download = app_commands.Group(
        name="download",
        description="Commands for downloading from a URL to mp3 or mp4",
        guild_ids=[351497847750787084, 301824927370313728]
    )

    @download.command(name="video", description="Takes URL and outputs in MP4. File upload limits apply.")
    @app_commands.describe(
        url="URL for video file. Some links may not work.",
        hidden="If true only you can see the response."
    )
    async def download_video(self, interaction: Interaction, url: str, hidden: bool):
        upload_limit = 8.0 # default upload size in megabytes
        if interaction.guild:
            upload_limit = float(interaction.guild.filesize_limit / 1024 ** 2)

        would_wait = self.download_queue.would_enqueue_wait()
        queue_position = self.download_queue.next_queue_position()

        if would_wait == True:
            interaction.response.send_message(f"Added download to queue. You are position {queue_position}. Quack quack.", ephemeral=hidden)
        else:
            interaction.response.send_message("I'm processing your file now. A response will be sent when I finish. Quack.", ephemeral=hidden)

        async def on_complete(filepath: str, compressed: bool, deferred: bool, cb_interaction: Interaction) -> None:
            result_file = open(filepath, "rb")
            file_bytes = result_file.read()
            result_file.close()
            file_to_send = File(BytesIO(file_bytes), "result.mp4")

            userid = cb_interaction.user.id

            

            await cb_interaction.channel.send(f"<@{userid}>, here is your video.{' It had to be compressed to meet upload limits.' if compressed else ''}", file=file_to_send, ephemeral=hidden)

            file_to_send.close()

        async def on_too_large(deferred: bool, cb_interaction: Interaction) -> None:
            userid = cb_interaction.user.id

            await cb_interaction.channel.send(f"<@{userid}>, your requested file was too large to download.", ephemeral=hidden)
        
        async def on_error(e: Exception, deferred: bool, cb_interaction: Interaction) -> None:
            userid = cb_interaction.user.id

            await cb_interaction.channel.send(f"<@{userid}>, an error occured with your download.", ephemeral=hidden)

        new_job  = VideoJob(url=url, target_mb=upload_limit, to_mp3=False, complete_callback=on_complete, 
                            error_callback=on_error, file_too_large_callback=on_too_large, 
                            interaction=interaction, deferred=would_wait)
        
        self.download_queue.enqueue(new_job)

    def cog_unload(self):
        super().cog_unload()
        self.download_queue.stop()