# ServerSwitcher

一个支持多槽位的服务器切换
改自QBM,简单易懂

需要 `v2.0.1` 以上的 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

当前未在运行的服务器将会存放至 server_switcher 文件夹中

## 命令格式说明

`!!ss` 显示帮助信息

`!!ss switch [<slot>]` 切换为槽位 `<slot>` 的服务器。

`!!ss rename <slot> <comment>` 修改槽位 `<slot>` 的注释，即重命名这一槽位

`!!ss confirm` 在执行 `switch` 后使用，再次确认是否进行切换

`!!ss abort` 在任何时候键入此指令可中断操作

`!!ss list` 显示各槽位的服务器信息

`!!ss reload` 重新加载配置文件

当 `<slot>` 未被指定时默认选择槽位 `1`

## 配置文件选项说明

配置文件为 `config/ServerSwitcher.json`。它会在第一次运行时自动生成
