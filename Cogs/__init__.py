# stuff needed for typehints
from typing import List
from discord.ext.commands import Cog

# the important stuff
from .listeners import Listeners
from .ping import Ping
from .download import Download
cog_list: List[Cog] = [Listeners, Ping, Download]