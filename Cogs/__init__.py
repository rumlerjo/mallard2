# stuff needed for typehints
from typing import List
from discord.ext.commands import Cog

# the important stuff
from .listeners import Listeners
from .ping import Ping
from .download import Download
from .selectable_role_commands import SelectableRoleCommands, PersistentRoleView # named this way to not conflict with data model name

cog_list: List[Cog] = [Listeners, Ping, Download, SelectableRoleCommands]