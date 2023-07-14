# Mastodon-to-Twitter-Sync
从Mastodon同步新嘟文到Twitter

支持媒体上传、长嘟文自动分割，以回复的形式同步，会排除回复和引用、以及以`@`开头的嘟文

需要用到的包：`requests、mastodon.py、pickle、tweepy、retrying、termcolor`

使用方法：修改`mtSync.py`开头的Twitter和Mastodon API，共计九个参数，之后`python mtSync.py`即可

可根据自己发文频率修改`SYNC_TIME`，它控制了多少秒检查一次有没有新嘟文

自动生成的`media`文件夹用于保存媒体缓存，`synced_toots.pkl`保存已经同步过的嘟文

昨天另一个同步工具不能用了，用了几个小时整出来的，可能会有点bug什么的;w;;
