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
os.system('color')

SYNC_TIME = 60 # 多少秒检查一次有没有更新

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
bearer_token = ''

last_toot_id = "xxx" # 上一次的嘟文id

# 授权访问 API ,创建 API 对象
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
client = tweepy.Client(bearer_token, consumer_key, consumer_secret, access_token, access_token_secret)
api = tweepy.API(auth)

user = mastodon.account_verify_credentials()
user_id = user['id']

def get_media_url_from_media_attachment(media_attachment) -> list: 
    # 从Mastodon获取媒体链接，返回媒体url列表以便下载
    url_list = []
    for item in media_attachment:
        url_list.append(item['url'])
    return url_list 

@retry(stop_max_attempt_number=5, wait_fixed = 60 * 1000) # 重试5次，每次间隔60秒
def get_latest_toot() -> dict:
    # 读取最新的嘟文，返回一个字典
    # 包含嘟文id、嘟文内容和媒体url列表

    toots = mastodon.account_statuses(user_id, limit=1)
    latest_toot_content = toots[0]['content']
    # 嘟文id
    latest_toot_id = toots[0]['id']
    # 处理HTML标签
    latest_toot_text = process_html_tags(latest_toot_content)
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

def process_html_tags(content : str):
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
        # print('[Check] 已同步的嘟文：',synced_toots)
    except:
        synced_toots = []
    return synced_toots
    
@retry(stop_max_attempt_number=5, wait_fixed = 60 * 1000) # 重试5次，每次间隔60秒
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

@retry(stop_max_attempt_number=2, wait_fixed = 60 * 1000) # 重试2次，每次间隔60秒
def main():
    global last_toot_id
    # 主流程
    long_tweet : bool = False # 长推文标记
    os.chdir(os.path.dirname(__file__)) # 前往工作目录
    synced_toots : list = load_synced_toots() # 读取已经同步的嘟文，返回一个列表
    toot : dict = get_latest_toot() # 读取最新的嘟文
    toot_id : str = toot['toot_id'] # 嘟文id
    
    if last_toot_id == toot_id: # 监控到的嘟文和上次的嘟文id一致，不需要再在控制台重复显示了
        return 0
    
    toot_text : str = toot['text'] # 嘟文内容
    media_attachment_list : list = toot['media_attachment_url'] # 嘟文媒体列表

    # 判断是否是已经同步过的推文，若是，则结束本次循环
    if toot_id in synced_toots:
        print(colored('[Check] 最新的嘟文ID：','green'),toot_id)
        print(colored('[Check] 最新的推文已经同步过，继续监控...','green'))
        return 0
    
    print() # 换行
    print(colored('[Check] 嘟文ID：','green'),toot['toot_id'])
    print(colored('[Check] 嘟文文本：','green'),toot['text_raw'])
    print(colored('[Check] 嘟文媒体：','green'),len(media_attachment_list))

    # 处理特殊情况
    if len(media_attachment_list) >= 5:
        print(colored('[Warning] 媒体数量超过4，超过Twitter最大展示量，只会展示4条媒体','yellow'))
    if len(toot_text) > 140:
        print(colored('[Warning] 嘟文过长！单篇推文最多支持140字','yellow'))
        print(colored('[Warning] 将以回复方式同步剩余的内容','yellow'))
        long_tweet : bool = True # 长推文标记
    if toot_text.find('u-url mention') != -1 or toot_text.startswith('@'):
        print(colored('[Check] 最新的嘟文为回复/引用，跳过...','green'))
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
            print(colored('[Download] 开始下载媒体：','blue'),url)
            download_media(url,filename)
            a += 1

        # 准备开始上传媒体，并保存媒体id到列表
        os.chdir('media')
        media_id_list = []
        for file in os.listdir():
            print(colored('[Upload] 正在上传媒体：','blue'),file)
            media = api.media_upload(file) 
            print(colored('[Upload] 媒体ID：','blue'),media.media_id_string)
            media_id_list.append(media.media_id_string)
            os.remove(file)
        
    # 发布推文到 Twitter
    print(colored('[Tweet] 开始发布推文到 Twitter...','cyan'))
    if long_tweet: # 长文本发布方式
        print(colored('[Tweet] 长推文发布模式','cyan'))
        if len(media_attachment_list) > 0: # 发布带有媒体的长推文
            tweets_list = split_toots(toot_text)
            print(colored('[Tweet] 主推文：','cyan'),repr(tweets_list[0]))
            result = client.create_tweet(text=tweets_list[0],media_ids=media_id_list) # 发布主推文
            print(colored('[Tweet] 主推文ID：','cyan'),result.data['id'])
            reply_to_id = result.data['id'] # 主推文id
            
            for i in range(1,len(tweets_list)):
                result = client.create_tweet(text=tweets_list[i],in_reply_to_tweet_id=reply_to_id)
                print(colored('[Tweet] 附属推文：','cyan'),repr(tweets_list[i]))

        else: # 发布不带有媒体的长推文
            tweets_list = split_toots(toot_text)
            print(colored('[Tweet] 主推文：','cyan'),repr(tweets_list[0]))
            result = client.create_tweet(text=tweets_list[0]) # 发布主推文
            print(colored('[Tweet] 主推文ID：','cyan'),result.data['id'])
            reply_to_id = result.data['id'] # 主推文id
            
            for i in range(1,len(tweets_list)):
                result = client.create_tweet(text=tweets_list[i],in_reply_to_tweet_id=reply_to_id)
                print(colored('[Tweet] 附属推文：','cyan'),repr(tweets_list[i]))
                time.sleep(1) # 等待1秒，防止推文错位

    else: # 短文本发布方式
        if len(media_attachment_list) > 0: # 发布带有媒体的短推文
            result = client.create_tweet(text=toot_text,media_ids=media_id_list)
        else: # 发布不带有媒体的端推文
            result = client.create_tweet(text=toot_text)

    if result.errors != []:
        print(colored('[Tweet] 推文发布失败！消息：','light_red'),result.errors)
        print()
    else:
        print(colored('[Tweet] 推文发布成功！','cyan'))
        print()
        # 保存嘟文id到 “已同步文件”
        os.chdir(os.path.dirname(__file__))
        synced_toots.append(toot_id)
        with open('synced_toots.pkl', 'wb') as f:
            pickle.dump(synced_toots, f)
    return 0

if __name__ == "__main__":
    print(colored('[Check] 开始监控','green'))
    while True:
        main()
        time.sleep(SYNC_TIME)
