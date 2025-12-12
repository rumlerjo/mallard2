from discord.ext.commands import Cog, Bot
from discord import app_commands, Interaction, File
from Util import AsyncVideoProcessor
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

        file_downloader = AsyncVideoProcessor(url=url)

        try:
            await file_downloader.download()
            compressed = False
            downloaded_size = round(file_downloader.get_filesize(), 2)
            if downloaded_size > upload_limit:
                await file_downloader.compress_to_size(target_mb=upload_limit)
                compressed = True

            result_file = open(file_downloader.filepath, "rb")
            file_bytes = result_file.read()
            result_file.close()
            file_to_send = File(BytesIO(file_bytes), "result.mp4")
                
            await interaction.response.send_message(f"Attached is your video.{' It had to be compressed to meet upload limits.' if compressed else ''}", file=file_to_send, ephemeral=hidden)

            file_to_send.close()

            file_downloader.cleanup_file()

        except RuntimeError:
            await interaction.response.send_message("Something went wrong with the video download. Check your url.", ephemeral=True)
        
        except FileNotFoundError:
            await interaction.response.send_message("Something went wrong initializing the downloader. Try again later.", ephemeral=True)
