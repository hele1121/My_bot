import html
import json
import os
import re
from multiprocessing import Pool
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import pymongo
from hashlib import md5

from My_bot.toutiao.tt_config import *

client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]


def get_index_page(offset, keyword):  # 请求索引页
    headers = {
        'cookie': 'tt_webid=6726341173404042763; WEATHER_CITY=%E5%8C%97%E4%BA%AC; s_v_web_id=dbdbe83be549bdb0e27c241ff5e169d1;'
                  ' csrftoken=75d849e4a8014bd2a0aeee68d568a620; tt_webid=6726341173404042763',
    }
    params = (
        ('aid', '24'),
        ('app_name', 'web_search'),
        ('offset', offset),
        ('format', 'json'),
        ('keyword', keyword),
        ('autoload', 'true'),
        ('count', '20'),
        ('en_qc', '1'),
        ('cur_tab', '1'),
        ('from', 'search_tab'),
        ('pd', 'synthesis'),
        ('timestamp', '1566107143656'),
    )

    try:
        response = requests.get('https://www.toutiao.com/api/search/content/', headers=headers, params=params)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错。')
        return None


def parse_page_index(html):  # 解析索引页
    data = json.loads(html)
    print(data)
    if data and 'data' in data.keys() and data['data']:  # 判断data 存在 和 'data' 存在 'data' 不为空
        for item in data.get('data'):
            if item.get('article_url'):
                yield item.get('article_url')


def get_page_detail(url):  # 请求详情页
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 UBrowser/6.2.4098.3 Safari/537.36',
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错。')
        return None


def parse_page_detail(html_1, url):  # 解析详情页链接
    soup = BeautifulSoup(html_1, 'lxml')
    title = soup.select('title')[0].get_text()
    reg = re.compile(r"content: '(.*?)'\.slice\(6, -6\)", re.S)
    result = re.search(reg, html_1)
    if result:
        html_result = (html.unescape(result.group(1))).encode().decode('unicode-escape')
        img_urls = re.findall('<img src="(.*?)"', html_result)
        if img_urls:
            for img in img_urls: get_img(img)
            return {
                'title': title,
                'url': url,
                'image_urls': [img_url for img_url in img_urls]
            }


def save_to_mongo(result):
    if db[MONGO_DB].insert(result):
        print('插入到数据库成功。')


def get_img(url):  # 请求图片内容
    print('正在下载', url)
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 UBrowser/6.2.4098.3 Safari/537.36',
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            save_img(response.content)
        return None
    except RequestException:
        print('请求图片出错')
        return None


def save_img(content):  # 保存图片到本地
    file_path = '{0}\img\{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    if not os.path.exists('{0}\img'.format(os.getcwd())):
        os.makedirs('{0}\img'.format(os.getcwd()))
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()
            print('保存完毕。')


def main(offset):  # 主流程
    html_index = get_index_page(offset, KEYWORD)
    for url in parse_page_index(html_index):
        detail_html = get_page_detail(url)
        if detail_html:
            result = parse_page_detail(detail_html, url)
            if result: save_to_mongo(result)


if __name__ == '__main__':
    groups = [x * 20 for x in (GROUP_START, GROUP_END + 1)]
    pool = Pool()
    pool.map(main, groups)
