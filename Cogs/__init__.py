# stuff needed for typehints
from typing import List
from discord.ext.commands import Cog

# the important stuff
from .listeners import Listeners
from .ping import Ping
from .download import Download
from .selectable_role import SelectableRole

cog_list: List[Cog] = [Listeners, Ping, Download, SelectableRole]