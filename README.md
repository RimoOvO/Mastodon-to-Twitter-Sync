## Mastodon-to-Twitter-Sync
从Mastodon同步新嘟文到Twitter

支持媒体上传、长嘟文自动分割，以回复的形式同步，会排除回复和引用、以及以`@`开头的嘟文。可根据自己发文频率修改`SYNC_TIME`，它控制了多少秒检查一次有没有新嘟文。

- 需要用到的包：`requests、mastodon.py、pickle、tweepy、retrying、termcolor、bs4`

- 自动生成的`media`文件夹用于保存媒体缓存，`synced_toots.pkl` 保存已经同步过的嘟文

昨天另一个同步工具不能用了，用了几个小时整出来的，可能会有点bug什么的;w;;

![1689405706148.png](https://global.cdn.mikupics.cn/2023/07/15/64b24910d56be.png)

## 使用方法

- 安装包 ```pip install -r requirements.txt```
- 拷贝一份 `config.sample.py` 到同目录并更名为 `config.py`
- 修改 `config.py` 中有关 Twitter 和 Mastodon 的参数，之后 `python mtSync.py` 即可

## Linux 后台常驻

- 按发行版及系统情况修改 systemd 文件 `mastodon-twitter-sync.service`
- ```systemctl enable mastodon-twitter-sync # 开机自启```
- ```systemctl start mastodon-twitter-sync # 启动```
