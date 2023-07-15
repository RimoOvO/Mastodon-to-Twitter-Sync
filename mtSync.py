from mastodon import Mastodon
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1
import requests
import pickle
import os
import tweepy
from retrying import retry
import time
from math import ceil
from termcolor import colored
import shutil
os.system('color')

SYNC_TIME = 60 # 同步间隔，单位秒
LOG_TO_FILE = True # 是否将日志写入文件

# Mastodon API setup 
mastodon = Mastodon(
    client_id = "",
    client_secret = "",
    access_token = "",
    api_base_url = "https://", 
)
# Twitter API setup
consumer_key = ""
consumer_secret = ""
access_token = ""
access_token_secret = ""
bearer_token = ""

# 授权访问 API ,创建 API 对象
auth = tweepy.OAuthHandler(consumer_key, consumer_secret) # 创建验证对象
auth.set_access_token(access_token, access_token_secret) # 设置验证对象的访问令牌和访问密钥
client = tweepy.Client(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret) # 创建 API 对象
api = tweepy.API(auth) # 创建 tweepy API 对象

user = mastodon.account_verify_credentials()
user_id = user['id'] 

last_toot_id = "xxx" # 上一次的嘟文id

def retry_if_error(exception): 
    # 错误处理，重试并打印错误
    tprint(colored('[Error] 出现错误: ' + str(type(exception)) + ' ，等待重试...','light_red'))
    # 如果出现tweepy.errors.TweepyException或者requests.exceptions.SSLError错误，等待3分钟，很有可能是代理问题，都会导致SSLError
    if isinstance(exception, tweepy.errors.TweepyException) or isinstance(exception, requests.exceptions.SSLError):
        tprint(colored('[Error] 此错误可能是网络问题，请检查代理设置','light_red'))
        tprint(colored('[Error] 将等待3分钟后重试...','light_red'))
        time.sleep(180-60) # 3分钟减去一分钟，因为下面还有一分钟的等待
    return True

def get_media_url_from_media_attachment(media_attachment) -> list: 
    # 从Mastodon获取媒体链接，返回媒体url列表以便下载
    url_list = []
    for item in media_attachment:
        url_list.append(item['url'])
    return url_list 

def tprint(*args):
    # 和print函数一致，不过会在输出前面增加日期时间，同时会将输出内容写入out.log
    print('['+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+']',*args)
    if LOG_TO_FILE: # 只有在LOG_TO_FILE为True时才会把日志写入文件
        out_log_path = os.path.join(os.path.dirname(__file__),'out.log')
        with open(out_log_path,'a',encoding='utf-8') as f:
            f.write('['+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+']')
            f.write(' '.join(str(x) for x in args))
            f.write('\n')

@retry(stop_max_attempt_number=5, wait_fixed = 60 * 1000 , retry_on_exception=retry_if_error) # 重试5次，每次间隔60秒
def get_latest_toot() -> dict:
    # 读取最新的嘟文，返回一个字典
    # 包含嘟文id、嘟文内容和媒体url列表

    toots = mastodon.account_statuses(user_id, limit=1)
    latest_toot_content = toots[0]['content']
    # 嘟文id
    latest_toot_id = toots[0]['id']
    # 处理HTML标签
    latest_toot_text = filter(latest_toot_content)
    # 清除HTML标签，提供一份raw文本供本地查看
    soup = BeautifulSoup(latest_toot_content, 'html.parser')
    text_raw = soup.get_text()
    # 读取嘟文媒体和链接
    media_attachment = toots[0]['media_attachments']
    media_attachment_url = get_media_url_from_media_attachment(media_attachment)

    return {'toot_id':latest_toot_id,
            'text':latest_toot_text, # 包含换行符等的
            'text_raw':text_raw, # 没有任何标记的
            'media_attachment_url':media_attachment_url
            } # 返回推文内容和媒体的字典

def filter(content : str):
    # 处理原文中有用的的 html 标签
    content = content.replace("<br />","\n") # <br /> 为换行
    # 清除其余的HTML标签，
    soup = BeautifulSoup(content, 'html.parser')
    content = soup.get_text()
    return content

def load_synced_toots() -> list:
    # 读取已经同步的嘟文，返回一个列表
    pickle_name = 'synced_toots.pkl'
    try:
        with open(pickle_name, 'rb') as f:
            synced_toots = pickle.load(f)
        # tprint('[Check] 已同步的嘟文：',synced_toots)
    except:
        synced_toots = []
    return synced_toots

@retry(stop_max_attempt_number=5, wait_fixed = 60 * 1000 , retry_on_exception=retry_if_error) # 重试5次，每次间隔60秒
def download_media(media_URL,filename):
    # 下载媒体
    os.makedirs('./media/', exist_ok=True)
    r = requests.get(media_URL)
    __target = os.path.dirname(__file__)+'\\media\\'+filename
    with open(__target, 'wb') as f:
        f.write(r.content)  

def split_toots(input_string : str):
    # 文段以125字符进行拆分，返回拆分后的列表，并在结尾加入进度标记
    parts = ceil(len(input_string)/125) # 总共拆分数
    result = []
    while len(input_string) > 0:
        result.append(input_string[:125] + '...({part}/{all})'.format(part = len(result)+1 ,all = parts))  # 将前125个字符加入列表中，加入如(1/4)的结尾标记
        input_string = input_string[125:]  # 去除已加入列表的前125个字符
    return result

@retry(stop_max_attempt_number=3, wait_fixed = 60 * 1000 , retry_on_exception=retry_if_error) # 重试两次，每次间隔60秒
def main():
    global last_toot_id
    long_tweet : bool = False # 长推文标记
    
    # 主流程
    os.chdir(os.path.dirname(__file__)) # 前往工作目录
    # 清空媒体缓存文件夹
    if os.path.exists('./media/'):
        shutil.rmtree('./media/',ignore_errors=True)
    
    synced_toots : list = load_synced_toots() # 读取已经同步的嘟文，返回一个列表
    toot : dict = get_latest_toot() # 读取最新的嘟文
    toot_id : str = toot['toot_id'] # 嘟文id

    if last_toot_id == toot_id: # 监控到的嘟文和上次的嘟文id一致，不需要再在控制台重复显示了
        return 0

    toot_text : str = toot['text'] # 嘟文内容
    media_attachment_list : list = toot['media_attachment_url'] # 嘟文媒体列表

    # 判断是否是已经同步过的推文，若是，则结束本次循环
    if toot_id in synced_toots:
        tprint(colored('[Check] 最新的嘟文ID：','green'),toot_id)
        tprint(colored('[Check] 最新的推文已经同步过，继续监控...','green'))
        last_toot_id = toot_id
        return 0
    
    print() # 换行
    tprint(colored('[Check] 嘟文ID：','green'),toot['toot_id'])
    tprint(colored('[Check] 嘟文文本：','green'),toot['text_raw'])
    tprint(colored('[Check] 嘟文媒体：','green'),len(media_attachment_list))

    # 处理特殊情况
    if len(media_attachment_list) >= 5:
        tprint(colored('[Warning] 媒体数量超过4，超过Twitter最大展示量，只会展示4条媒体','yellow'))
    if len(toot_text) > 140:
        tprint(colored('[Warning] 嘟文过长！单篇推文最多支持140字','yellow'))
        tprint(colored('[Warning] 将以回复方式同步剩余的内容','yellow'))
        long_tweet : bool = True # 长推文标记
    if  toot_text.startswith('@'):
        tprint(colored('[Check] 最新的嘟文为回复/引用，跳过...','green'))
        last_toot_id = toot_id
        return 0

    if len(media_attachment_list) > 0: # 如果有媒体，则下载到缓存文件夹
        a = 0
        # 处理媒体格式
        for url in media_attachment_list:
            if url.endswith(".mp4"):
                format = ".mp4"
            elif url.endswith(".gif"):
                format = ".gif"
            else:
                format = ".jpg"

            filename = str(a) + format 
            tprint(colored('[Download] 开始下载媒体：','blue'),url)
            download_media(url,filename)
            a += 1

        # 准备开始上传媒体，并保存媒体id到列表
        os.chdir('media')
        media_id_list = []
        for file in os.listdir():
            tprint(colored('[Upload] 正在上传媒体：','blue'),file)
            media = api.media_upload(file) 
            tprint(colored('[Upload] 媒体ID：','blue'),media.media_id_string)
            media_id_list.append(media.media_id_string)
            os.remove(file)
            time.sleep(1) # 上传媒体间隔1秒
        
    # 发布推文到 Twitter
    tprint(colored('[Tweet] 开始发布推文到 Twitter...','cyan'))
    if long_tweet: # 长文本发布方式
        tprint(colored('[Tweet] 长推文发布模式','cyan'))
        if len(media_attachment_list) > 0: # 发布带有媒体的长推文
            tweets_list = split_toots(toot_text)
            tprint(colored('[Tweet] 主推文：','cyan'),repr(tweets_list[0]))
            result = client.create_tweet(text=tweets_list[0],media_ids=media_id_list) # 发布主推文
            tprint(colored('[Tweet] 主推文ID：','cyan'),result.data['id'])
            reply_to_id = result.data['id'] # 主推文id
            
            for i in range(1,len(tweets_list)):
                result = client.create_tweet(text=tweets_list[i],in_reply_to_tweet_id=reply_to_id)
                tprint(colored('[Tweet] 附属推文：','cyan'),repr(tweets_list[i]))

        else: # 发布不带有媒体的长推文
            tweets_list = split_toots(toot_text)
            tprint(colored('[Tweet] 主推文：','cyan'),repr(tweets_list[0]))
            result = client.create_tweet(text=tweets_list[0]) # 发布主推文
            tprint(colored('[Tweet] 主推文ID：','cyan'),result.data['id'])
            reply_to_id = result.data['id'] # 主推文id
            
            for i in range(1,len(tweets_list)):
                result = client.create_tweet(text=tweets_list[i],in_reply_to_tweet_id=reply_to_id)
                tprint(colored('[Tweet] 附属推文：','cyan'),repr(tweets_list[i]))
                time.sleep(1) # 等待1秒，防止推文错位

    else: # 短文本发布方式
        if len(media_attachment_list) > 0: # 发布带有媒体的短推文
            result = client.create_tweet(text=toot_text,media_ids=media_id_list)
        else: # 发布不带有媒体的端推文
            result = client.create_tweet(text=toot_text)

    if result.errors != []:
        tprint(colored('[Error] 推文发布失败！消息：','light_red'),result.errors)
        print()
    else:
        tprint(colored('[Tweet] 推文发布成功！','cyan'))
        print()
        # 保存嘟文id到 “已同步文件”
        os.chdir(os.path.dirname(__file__))
        synced_toots.append(toot_id)
        with open('synced_toots.pkl', 'wb') as f:
            pickle.dump(synced_toots, f)
    return 0

if __name__ == "__main__":
    tprint(colored('[Check] 同步检查间隔：','green'),SYNC_TIME,'秒')
    tprint(colored('[Check] 同步到日志文件：','green'),'是' if LOG_TO_FILE else '否')
    print()
    tprint(colored('[Check] 开始监控','green'))
    while True:
        main()
        time.sleep(SYNC_TIME)