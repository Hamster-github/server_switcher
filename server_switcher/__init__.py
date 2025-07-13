import functools
import json
import os
import re
import time
from threading import Lock, Event
from typing import Optional, Any, Callable, Tuple

from mcdreforged.api.all import *

from server_switcher.config import Configuration
from server_switcher.constant import Prefix, SWITCH_DONE_EVENT, \
	CONFIG_FILE, TRIGGER_SWITCH_EVENT


config: Configuration
server_inst: PluginServerInterface
HelpMessage: RTextBase
slot_selected = None  # type: Optional[int]
abort_switch = Event()
plugin_unloaded = False
operation_lock = Lock()
operation_name = RText('?')
game_saved = Event()


def tr(translation_key: str, *args) -> RTextMCDRTranslation:
	return ServerInterface.get_instance().rtr('server_switcher.{}'.format(translation_key), *args)


def print_message(source: CommandSource, msg, tell=True, prefix='[SS] '):
	msg = RTextList(prefix, msg)
	if source.is_player and not tell:
		source.get_server().say(msg)
	else:
		source.reply(msg)


def command_run(message: Any, text: Any, command: str) -> RTextBase:
	fancy_text = message.copy() if isinstance(message, RTextBase) else RText(message)
	return fancy_text.set_hover_text(text).set_click_event(RAction.run_command, command)


def get_slot_count():
	return len(os.listdir(config.servers_path))


def get_slot_path(slot: int):
	return os.path.join(config.servers_path, os.listdir(config.servers_path)[slot - 1])

def get_slot_name(slot: int) -> str:
	"""
	:param int slot: the index of the slot
	:return: the name of the slot
	:rtype: str
	"""
	try:
		return os.listdir(config.servers_path)[slot - 1]
	except IndexError:
		return 'slot{}'.format(slot)


def get_slot_info(slot: int):
	"""
	:param int slot: the index of the slot
	:return: the slot info
	:rtype: dict or None
	"""
	try:
		if os.path.join(get_slot_path(slot), 'info.json') not in os.listdir(get_slot_path(slot)):
			create_slot_info(slot, get_slot_name(slot))
		with open(os.path.join(get_slot_path(slot), 'info.json'), encoding='utf8') as f:
			info = json.load(f)
	except:
		info = None
	return info


def format_time():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def format_slot_info(info_dict: Optional[dict] = None) -> Optional[RTextBase]:
	if isinstance(info_dict, dict):
		info = info_dict
	else:
		return None

	if info is None:
		return None
	return tr('slot_info', info['time'], info.get('comment', tr('empty_comment')))

def mkdir(path: str):
	if os.path.isfile(path):
		os.remove(path)
	if not os.path.isdir(path):
		os.mkdir(path)

def touch_servers_folder():
	mkdir(config.servers_path)

def slot_check(source: CommandSource, slot: int) -> Optional[Tuple[int, dict]]:
	if not 1 <= slot <= get_slot_count():
		print_message(source, tr('unknown_slot', 1, get_slot_count()))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(source, tr('empty_slot', slot))
		return None
	return slot, slot_info


def create_slot_info(slot, comment) -> dict:
	slot_info = {
		'time': format_time(),
		'time_stamp': time.time(),
		'comment': comment
	}
	write_slot_info(get_slot_path(slot), slot_info)


def write_slot_info(slot_path: str, slot_info: dict):
	with open(os.path.join(slot_path, 'info.json'), 'w', encoding='utf8') as f:
		json.dump(slot_info, f, indent=4, ensure_ascii=False)


def single_op(name: RTextBase):
	def wrapper(func: Callable):
		@functools.wraps(func)
		def wrap(source: CommandSource, *args, **kwargs):
			global operation_name
			acq = operation_lock.acquire(blocking=False)
			if acq:
				operation_name = name
				try:
					func(source, *args, **kwargs)
				finally:
					operation_lock.release()
			else:
				print_message(source, tr('lock.warning', operation_name))
		return wrap
	return wrapper

@new_thread('SS_Rename')
@single_op(tr('operations.rename'))
def rename_server(source: CommandSource, slot: int, comment: str):
	ret = slot_check(source, slot)
	if ret is None:
		return
	try:
		slot, slot_info = ret
		slot_info['comment'] = comment
		write_slot_info(get_slot_path(slot), slot_info)
		os.rename(get_slot_path(slot), os.path.join(config.servers_path, comment))
	except Exception as e:
		print_message(source, tr('rename_server.fail', slot, e), tell=False)
	else:
		print_message(source, tr('rename_server.success', slot), tell=False)

def switch_server(source: CommandSource, slot: int):
	ret = slot_check(source, slot)
	if ret is None:
		return
	else:
		slot, slot_info = ret
	global slot_selected
	slot_selected = slot
	abort_switch.clear()
	print_message(source, tr('switch_server.echo_action', slot, format_slot_info(info_dict=slot_info)), tell=False)
	info_path = os.path.join(config.server_path, 'info.json')
	if "default_server" in os.listdir(config.servers_path):
		print_message(source, tr('switch_server.warn_overwrite'), tell=False)

	print_message(
		source,
		command_run(tr('switch_server.confirm_hint', Prefix), tr('switch_server.confirm_hover'), '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run(tr('switch_server.abort_hint', Prefix), tr('switch_server.abort_hover'), '{0} abort'.format(Prefix))
		, tell=False
	)


@new_thread('SS_Switch')
def confirm_switch(source: CommandSource):
	global slot_selected
	if slot_selected is None:
		print_message(source, tr('confirm_switch.nothing_to_confirm'), tell=False)
	else:
		slot = slot_selected
		slot_selected = None
		_do_switch_server(source, slot)


@single_op(tr('operations.switch'))
def _do_switch_server(source: CommandSource, slot: int):
	try:
		print_message(source, tr('do_switch.countdown.intro'), tell=False)
		slot_info = get_slot_info(slot)
		for countdown in range(1, 10):
			print_message(source, command_run(
				tr('do_switch.countdown.text', 10 - countdown, slot, format_slot_info(info_dict=slot_info)),
				tr('do_switch.countdown.hover'),
				'{} abort'.format(Prefix)
			), tell=False)

			if abort_switch.wait(1):
				print_message(source, tr('do_switch.abort'), tell=False)
				return

		source.get_server().stop()
		server_inst.logger.info('Wait for server to stop')
		source.get_server().wait_for_start()

		dst_slot = get_slot_path(slot)
		info_path = os.path.join(config.server_path, 'info.json')
		if os.path.exists(info_path):
			with open(info_path, encoding='utf8') as f:
				info = json.load(f)
		else:
			info = {'comment': 'default_server'}
		os.rename(config.server_path, os.path.join(config.servers_path, info["comment"]))
		os.rename(dst_slot, config.server_path)

		source.get_server().start()
	except:
		server_inst.logger.exception('Fail to switch server to slot {}, triggered by {}'.format(slot, source))
	else:
		source.get_server().dispatch_event(SWITCH_DONE_EVENT, (source, slot, slot_info))  # async dispatch


def trigger_abort(source: CommandSource):
	global slot_selected
	abort_switch.set()
	slot_selected = None
	print_message(source, tr('trigger_abort.abort'), tell=False)


@new_thread('SS_List')
def list_server(source: CommandSource, size_display: bool = None):
	if size_display is None:
		size_display = config.size_display

	def get_dir_size(dir_: str):
		size = 0
		for root, dirs, files in os.walk(dir_):
			size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
		return size

	def format_dir_size(size: int):
		if size < 2 ** 30:
			return '{} MiB'.format(round(size / 2 ** 20, 2))
		else:
			return '{} GiB'.format(round(size / 2 ** 30, 2))

	print_message(source, tr('list_server.title'), prefix='')
	total_server_size = 0
	for i in range(get_slot_count()):
		slot_idx = i + 1
		slot_info = get_slot_info(slot_idx)
		formatted_slot_info = format_slot_info(slot_info)
		if size_display:
			dir_size = get_dir_size(get_slot_path(slot_idx))
		else:
			dir_size = 0
		total_server_size += dir_size
		# noinspection PyTypeChecker
		text = RTextList(
			RText(tr('list_server.slot.header', slot_idx)),
			' '
		)
		if formatted_slot_info is not None:
			text += RTextList(
				RText('[▷] ', color=RColor.green).h(tr('list_server.slot.switch', slot_idx)).c(RAction.run_command, f'{Prefix} switch {slot_idx}')
			)
			if size_display:
				text += RText(format_dir_size(dir_size) + ' ', RColor.dark_green)
		text += formatted_slot_info
		print_message(source, text, prefix='')
	if size_display:
		print_message(source, tr('list_server.total_space', format_dir_size(total_server_size)), prefix='')


@new_thread('SS_Help')
def print_help_message(source: CommandSource):
	if source.is_player:
		source.reply('')
	with source.preferred_language_context():
		for line in HelpMessage.to_plain_text().splitlines():
			prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
			if prefix is not None:
				print_message(source, RText(line).set_click_event(RAction.suggest_command, prefix.group()), prefix='')
			else:
				print_message(source, line, prefix='')
		list_server(source, size_display=False).join()


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
	print_message(source, command_run(
		tr('unknown_command.text', Prefix),
		tr('unknown_command.hover'),
		Prefix
	))


def register_command(server: PluginServerInterface):
	def get_literal_node(literal):
		lvl = config.minimum_permission_level.get(literal, 0)
		return Literal(literal).requires(lambda src: src.has_permission(lvl)).on_error(RequirementNotMet, lambda src: src.reply(tr('command.permission_denied')), handled=True)

	def get_slot_node():
		return Integer('slot').requires(lambda src, ctx: 1 <= ctx['slot'] <= get_slot_count()).on_error(RequirementNotMet, lambda src: src.reply(tr('command.wrong_slot')), handled=True)

	server.register_command(
		Literal(Prefix).
		runs(print_help_message).
		on_error(UnknownArgument, print_unknown_argument_message, handled=True).
		then(
			get_literal_node('switch').
			runs(lambda src: switch_server(src, 1)).
			then(get_slot_node().runs(lambda src, ctx: switch_server(src, ctx['slot'])))
		).
		then(
			get_literal_node('rename').
			then(
				get_slot_node().
				then(GreedyText('comment').runs(lambda src, ctx: rename_server(src, ctx['slot'], ctx['comment'])))
			)
		).
		then(get_literal_node('confirm').runs(confirm_switch)).
		then(get_literal_node('abort').runs(trigger_abort)).
		then(get_literal_node('list').runs(lambda src: list_server(src))).
		then(get_literal_node('reload').runs(lambda src: load_config(src.get_server(), src)))
	)


def load_config(server: ServerInterface, source: CommandSource or None = None):
	global config
	config = server_inst.load_config_simple(CONFIG_FILE, target_class=Configuration, in_data_folder=False, source_to_reply=source)

def register_event_listeners(server: PluginServerInterface):
	server.register_event_listener(TRIGGER_SWITCH_EVENT, lambda svr, source, slot: _do_switch_server(source, slot))


def on_load(server: PluginServerInterface, old):
	global operation_lock, operation_name, HelpMessage, server_inst
	server_inst = server
	if hasattr(old, 'operation_lock') and type(old.operation_lock) == type(operation_lock):
		operation_lock = old.operation_lock
		operation_name = getattr(old, 'operation_name', operation_name)

	meta = server.get_self_metadata()
	HelpMessage = tr('help_message', Prefix, meta.name, meta.version)
	load_config(server)
	register_command(server)
	register_event_listeners(server)
	touch_servers_folder()
	server.register_help_message(Prefix, command_run(tr('register.summory_help', get_slot_count()), tr('register.show_help'), Prefix))


def on_unload(server: PluginServerInterface):
	global plugin_unloaded
	plugin_unloaded = True
	abort_switch.set()  # plugin unload is a kind of "abort" too
	game_saved.set()  # interrupt the potential waiting on game saved