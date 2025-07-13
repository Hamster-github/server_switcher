from typing import Dict

from mcdreforged.api.utils.serializer import Serializable


class Configuration(Serializable):
	size_display: bool = True
	servers_path: str = './server_switcher'
	server_path: str = './server'
	minimum_permission_level: Dict[str, int] = {
		'switch': 2,
		'rename': 2,
		'confirm': 1,
		'abort': 1,
		'reload': 2,
		'list': 0,
		's': 2,
		'r': 2,
		'c': 1,
		'a': 1,
		'l': 0,
	}

if __name__ == '__main__':
	config = Configuration().get_default()
