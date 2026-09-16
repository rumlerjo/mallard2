from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, File
from Util import AsyncVideoProcessor, VideoProcessingQueue, VideoJob
from io import BytesIO
from MallardModels import MallardUser

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

    async def cog_load(self):
        self.download_queue.start()

    download = app_commands.Group(
        name="download",
        description="Commands for downloading from a URL to mp3 or mp4",
    )

    @download.command(name="video", description="Takes URL and outputs in MP4. File upload limits apply.")
    @app_commands.describe(
        url="URL for video file. Some links may not work.",
        hidden="If true only you can see the response."
    )
    async def download_video(self, interaction: Interaction, url: str, hidden: bool = True):
        bot_user = MallardUser()
        await bot_user.load(interaction=interaction)

        upload_limit = 8.0 # default upload size in megabytes
        if interaction.guild:
            upload_limit = float(interaction.guild.filesize_limit / 1024 ** 2)

        would_wait = self.download_queue.would_enqueue_wait()
        queue_position = self.download_queue.next_queue_position()

        if would_wait == True:
            await interaction.response.send_message(f"Added download to queue. You are position {queue_position}. Quack Quack 🦆", ephemeral=hidden)
        else:
            await interaction.response.defer(ephemeral=hidden)

        level_up = bot_user.add_command_xp()
        await bot_user.save()

        async def on_complete(filepath: str, compressed: bool, cb_interaction: Interaction) -> None:
            result_file = open(filepath, "rb")
            file_bytes = result_file.read()
            result_file.close()
            file_to_send = File(BytesIO(file_bytes), "result.mp4")

            await cb_interaction.followup.send(f"Here is your video.{' It had to be compressed to meet upload limits.' if compressed else ''} Quack.", file=file_to_send, ephemeral=hidden)

            file_to_send.close()

            if level_up and bot_user.level_notifs_on:
                await cb_interaction.followup.send(f"Congrats! You levelled up to level {bot_user.level}!", ephemeral=hidden)

        async def on_delay_reply(cb_interaction: Interaction) -> None:
            await cb_interaction.followup.send("Your file will be sent in a reply to this message. Quack Quack 🦆", ephemeral=hidden)

        async def on_too_large(cb_interaction: Interaction) -> None:
            await cb_interaction.followup.send("Your requested file was too large to download.", ephemeral=hidden)

            if level_up and bot_user.level_notifs_on:
                await cb_interaction.followup.send(f"Congrats! You levelled up to level {bot_user.level}!", ephemeral=hidden)
        
        async def on_error(e: Exception, cb_interaction: Interaction) -> None:
            await cb_interaction.followup.send("An error occured with your download.", ephemeral=hidden)

            if level_up and bot_user.level_notifs_on:
                await cb_interaction.followup.send(f"Congrats! You levelled up to level {bot_user.level}!", ephemeral=hidden)

        new_job  = VideoJob(url=url, target_mb=upload_limit, to_mp3=False, complete_callback=on_complete, 
                            error_callback=on_error, file_too_large_callback=on_too_large,
                            delay_reply_callback=on_delay_reply, interaction=interaction)
        
        await self.download_queue.enqueue(new_job)

    def cog_unload(self):
        self.bot.loop.create_task(self.download_queue.stop())