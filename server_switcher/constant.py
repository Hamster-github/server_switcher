import os

from mcdreforged.api.event import LiteralEvent

PLUGIN_ID = 'server_switcher'
Prefix = '!!ss'
CONFIG_FILE = os.path.join('config', 'ServerSwitcher.json')

SWITCH_DONE_EVENT 		= LiteralEvent('{}.switch_done'.format(PLUGIN_ID))  # -> source, slot, slot_info
TRIGGER_SWITCH_EVENT 	= LiteralEvent('{}.trigger_switch'.format(PLUGIN_ID))  # <- source, slot