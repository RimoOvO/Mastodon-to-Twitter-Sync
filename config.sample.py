# Twitter API Config
twitter_config = {
    'consumer_key': '',
    'consumer_secret': '',
    'access_token': '',
    'access_token_secret': '',
    'bearer_token': ''
}

# Mastodon Config
mastodon_config = {
    'client_id': '',
    'client_secret': '',
    'access_token': '',
    'api_base_url': 'https://'
}

main_config = {
    'sync_time' : 60 , # 检查是否有新同步的时间间隔，单位为秒，如果发文较为频繁，可以缩小该值
    'log_to_file' : True , # 是否将日志写入文件
    'limit_retry_attempt' : 13 , # 最大重试次数，默认为13次，仍失败则保存到sync_failed.txt，设置为0则无限重试，此举可能会耗尽 API 请求次数
    'wait_exponential_max': 1000*60*30 ,# 单次重试的最大等待时间，单位为毫秒，默认为30分钟
    'wait_exponential_multiplier': 800 # 单次重试的等待时间指数增长，单位为毫秒，默认为800毫秒，减少该值会减少每次尝试的等待时间
}
