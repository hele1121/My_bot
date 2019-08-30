import re
from random import randint

import pymongo
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC, ui
from time import sleep
from pyquery import PyQuery as pq
from My_bot.淘宝商品爬虫.tb_config import *


class Taobao_info:
    def __init__(self):
        self.url = 'https://login.taobao.com/member/login.jhtml'

        options = webdriver.ChromeOptions()  # 配置浏览器选项
        options.add_argument('lang=zh_CH.UTF-8')
        options.add_argument('--disable-extensions')  # 禁用扩展
        options.add_argument("--incognito")  # 无痕模式
        options.add_argument('--start-maximized')  # 最大化运行（全屏窗口）,不设置，取元素可能会报错
        # options.add_argument('--blink-settings=imagesEnabled=false')  # 不加载图片
        options.add_argument('--disable-infobars')  # 禁用浏览器正在被自动化程序控制的提示
        options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置开发者模式，防止浏览器驱动检测自动

        # 其他可设置的配置：
        # chrome_options.add_argument('--user-agent=""')  # 设置请求头的User-Agent
        # chrome_options.add_argument('--profile-directory=Default')  # ??? 配置目录 = 默认
        # chrome_options.add_argument('--window-size=1280x1024')  # 设置浏览器分辨率（窗口大小）
        # chrome_options.add_argument('--hide-scrollbars')  # 隐藏滚动条, 应对一些特殊页面
        # chrome_options.add_argument('--disable-javascript')  # 禁用javascript
        # chrome_options.add_argument('--headless')  # 无头模式
        # chrome_options.add_argument('--ignore-certificate-errors')  # 禁用扩展插件并实现窗口最大化
        # chrome_options.add_argument('--disable-gpu')  # 禁用GPU加速

        self.browser = webdriver.Chrome(options=options)  # 实例化浏览器
        self.wait = ui.WebDriverWait(self.browser, 10)  # 超时10s
        client = pymongo.MongoClient(MONGO_URL, connect=False)
        self.db = client[MONGO_DB]

    def code(self):
        self.browser.find_element_by_id('TPL_password_1').clear() # 清空密码
        self.browser.find_element_by_id('TPL_password_1').send_keys(PASSWORD)  # 在输入一次密码
        ActionChains(self.browser).click_and_hold(
            on_element=self.browser.find_element_by_id('nc_1_n1z')).perform()
        sleep(0.5)
        ActionChains(self.browser).move_by_offset(xoffset=300, yoffset=0).perform()  # 移动滑块
        ActionChains(self.browser).release().perform()
        sleep(0.5)
        return



    def login(self):  # 登录
        self.browser.get(self.url)
        self.browser.find_element_by_id('J_Quick2Static').click()  # 获取到登录框
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'ph-label')))
        self.browser.find_element_by_id('TPL_username_1').send_keys(USER)
        self.browser.find_element_by_id('TPL_password_1').send_keys(PASSWORD)
        self.browser.find_element_by_id('J_SubmitStatic').submit()
        print(PASSWORD)

        sleep(0.5)  # 等待滑动验证码
        if self.browser.find_element_by_id('nc_1_n1z'):
            self.code() # 处理滑动验证码
            if self.browser.find_element_by_css_selector('#nocaptcha > div > span > a'): # 当出现刷新 在执行一次验证码处理
                self.browser.find_element_by_css_selector('#nocaptcha > div > span > a').click()
                self.code()
                self.browser.find_element_by_id('J_SubmitStatic').submit()
            else:
                self.browser.find_element_by_id('J_SubmitStatic').submit()  # 提交登录
            if self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,
                                                                    '#J_SiteNavLogin > div.site-nav-menu-hd > div.site-nav-user > a.site-nav-login-info-nick'))):
                return
            else:
                print('登录失败。')

    def roll_down(self):  # 模拟随机滚动屏幕
        roll_size = 5000  # 设置页面滚动条高度
        roll_num = randint(3, 5)  # 随机滚动3 - 5 次
        while roll_num >= 0:
            js = "var q=document.documentElement.scrollTop={}".format(randint(1, roll_size))
            self.browser.execute_script(js)
            roll_num -= 1
            sleep(0.5)  # 设置延迟
        js = "var q=document.documentElement.scrollTop={}".format(randint(roll_size - 500, roll_size))
        self.browser.execute_script(js)  # 滚动到翻页处
        print('ok')
        return

    def get_goods_page(self):  # 获取页面数量
        self.browser.get('http://www.taobao.com')
        search_box = self.wait.until(EC.presence_of_element_located((By.ID, 'q')))
        search_box.send_keys(KEY_WORD)
        self.browser.find_element_by_css_selector('#J_TSearchForm > div.search-button > button').submit()  # 提交搜索
        total = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))  # 获取页数
        total = int(re.compile('(\d+)').search(total.text).group(1))  # 得到商品页数
        return total

    def get_next_page(self, next_page):
        try:
            input = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')))
            submit = self.wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
            input.clear()
            input.send_keys(next_page)
            submit.click()
            self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span')))  # 判断翻页是否成功
        except TimeoutError:

            self.get_next_page(next_page)

    def save_to_mongo(self, tb_msg):
        try:
            if self.db[MONGO_TABLE].insert(tb_msg):
                print('存储到数据库成功。')
        except:
            print('存储到数据库失败。')

    def get_goods_msg(self):  # 爬取想要的信息。
        self.roll_down()  # 滚动页面 使得页面内容加载完全
        self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#mainsrp-itemlist > div > div > div:nth-child(1)')))
        html = self.browser.page_source  # 获取页面源码
        doc = pq(html)
        items = doc('#mainsrp-itemlist > div > div > div:nth-child(1) > .item').items()
        print()
        for item in items:
            goods_msg = {  # 提取信息
                'image': item.find('.pic .img').attr('src'),
                'price': item.find('.price').text(),
                'pay': item.find('.deal-cnt').text()[:-3],
                'title': item.find('.title').text(),
                'shop': item.find('.shop').text(),
                'location': item.find('.location').text(),
            }
            self.save_to_mongo(goods_msg)

    def main(self):
        self.login()
        total = self.get_goods_page()
        for i in range(2, total + 1):
            self.get_goods_msg()
            self.get_next_page(i) # 获取下一页


if __name__ == '__main__':
    tb = Taobao_info()
    tb.main()
