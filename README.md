## Mastodon-to-Twitter-Sync
从Mastodon同步新嘟文到Twitter

支持媒体上传、长嘟文自动分割，以回复的形式同步，会排除回复和引用、以及以`@`开头的嘟文；支持过短视频自动延长。

如果是第一次运行，只会从第一次运行后的写的嘟文开始同步

如果想把之前所有的推文同步到mastodon，[试试这个！](https://github.com/klausi/mastodon-twitter-sync)，我自己搭建的实例已经把所有之前的推文全部成功导入了

- 需要用到的包：`requests、mastodon.py、pickle、tweepy、retrying、termcolor、bs4、moviepy`

- 自动生成的`media`文件夹用于保存媒体缓存，`synced_toots.pkl` 保存已经同步过的嘟文

![1689405706148.png](https://global.cdn.mikupics.cn/2023/07/15/64b24910d56be.png)

## 使用方法

- 安装包 ```pip install -r requirements.txt```
- 拷贝一份 `config.sample.py` 到同目录并更名为 `config.py`
- 修改 `config.py` 中有关 Twitter 和 Mastodon 的参数，之后 `python mtSync.py` 即可

## Linux 后台常驻

- 按发行版及系统情况修改 systemd 文件 `mastodon-twitter-sync.service`
- ```systemctl enable mastodon-twitter-sync # 开机自启```
- ```systemctl start mastodon-twitter-sync # 启动```

## config.py 参数说明
`sync_time`:程序会每隔一定的时间循环访问mastodon，看看有没有新嘟文，由这个时间控制（单位秒）

`log_to_file`:是否保存日志到`out.log`

`limit_retry_attempt`:最大重试次数，默认为13次，仍失败则跳过嘟文，保存嘟文id到sync_failed.txt，设置为0则无限重试，此举可能会耗尽 API 请求次数，但不会因为报错达到最大尝试上限而退出程序

`wait_exponential_max`：单次重试的最大等待时间，单位为毫秒，默认为30分钟，遇到错误，每次的等待时间会越来越长

`wait_exponential_multiplier`：单次重试的等待时间指数增长，默认为800，800即为`原等待时间x0.8`，如果你想缩短每次的等待时间，可以减少该值

每次等待时间（秒） = （ `2`的`当前重试次数`次方 ) * ( `wait_exponential_multiplier` / 1000 )
