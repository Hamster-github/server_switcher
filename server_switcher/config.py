from typing import Dict

from mcdreforged.api.utils.serializer import Serializable


class Configuration(Serializable):
	size_display: bool = True
	servers_path: str = './server_switcher'
	server_path: str = './server'
	minimum_permission_level: Dict[str, int] = {
		's': 2,
		'r': 2,
		'c': 1,
		'a': 1,
		'reload': 2,
		'l': 0,
	}

if __name__ == '__main__':
	config = Configuration().get_default()
