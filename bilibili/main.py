import sys
import time
import math
import jieba
import requests
import operator
from collections import defaultdict
from icecream import ic
from jsonpath import jsonpath
import re

# 词云
import stylecloud
import csv
import pandas as pd
import numpy as np
from PIL import Image
import urllib3

class GetCommentData():
    #  爬取评论数据 GET
    def __init__(self):
        self.baseurl = "https://api.bilibili.com/x/v2/reply/main?csrf=937b43fa3584b5246df0703188fad3e9&mode=3&next={}&oid=387445654&plat=1&seek_rpid=&type=1"
        self.detail_url = "https://api.bilibili.com/x/v2/reply/reply?csrf=937b43fa3584b5246df0703188fad3e9&oid=216879663&pn={}&ps=10&root={}&type=1"
        self.page_maxOffset = 100 # 默认100为无穷大 3375=20*75+(2)=76页 page_maxOffset
        self.detail_maxOffset = 20  # 默认20为无穷大
        self.headers = {
            'user-agent': ' ',
            'referer': ' '
        }
        self.comment_path = 'data/comment_test.csv' # 文件保存位置
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  #不显示HTTPS认证报错

    def get_comment_data(self,url):
        '''
        视频页滚动url调用 + 多人回复详情页调用
        :param url:
        :return:
        '''
        try:
            time.sleep(0.8)
            response = requests.get(url, timeout=90, headers=self.headers).json()
            print('URL:' + url + ' ，状态码：{}'.format(response['code']))
            message_list = response['data']['replies']
            return message_list
        except Exception as e:
            print("\033[1;31m数据处理发生异常~~ URL:\033[0m" + url)
            print(e)

    def comment_xpath(self, url, message_list):
        try:
            content_list = []
            for item in message_list:
                item_dist = {}

                rpid = item['rpid']
                item_dist['评论ID'] = rpid

                t = item['ctime']
                timeArray = time.localtime(t)
                comment_time = time.strftime("%Y%m%d", timeArray)
                item_dist['评论时间'] = comment_time

                like = item['like']
                item_dist['点赞数'] = like

                UID = item['member']['mid']
                item_dist['UID'] = UID

                name = item['member']['uname']
                item_dist['昵称'] = name

                sex = item['member']['sex']
                item_dist['性别'] = sex

                level = item['member']['level_info']['current_level']
                item_dist['用户等级'] = level

                message = item['content']['message']
                item_dist['评论内容'] = message

                # location = item['reply_control']['location']
                # item_dist['IP归属地'] = location

                content_list.append(item_dist)
            return content_list
        except Exception as e:
            print("\033[1;31m数据处理发生异常~~ URL:\033[0m" + url)
            print(e)

    def file_save(self,data_list):
        f = open(self.comment_path, 'w', encoding='utf-8-sig', newline='')  # newline=''防止空行
        csv_write = csv.writer(f)
        csv_write.writerow(['评论ID', '评论时间', '点赞数', 'UID', '昵称', '性别', '用户等级', '评论内容'])
        try:
            for detail in data_list:
                csv_write.writerow([detail['评论ID'],detail['评论时间'], detail['点赞数'], detail['UID'], detail['昵称'],detail['性别'], detail['用户等级'], detail['评论内容']])
            print(self.comment_path + " 文件保存成功")
        except Exception as e:
            print("\033[1;31m文件保存出错:\033[0m" + self.comment_path)
            print(e)

    def CommentMain(self):
        total_message_list = []
        for offset_value in range(0, self.page_maxOffset, 1):
            # 视频页URL拼接
            url = self.baseurl.format(offset_value)
            # 请求视频页数据
            response = self.get_comment_data(url)
            if (response != None):
                # 解析视频页数据
                per_message_list = self.comment_xpath(url, response)
                # 数据整合
                for item in per_message_list:
                    total_message_list.append(item)
                # 多人回复调用
                detail_list = self.GetMoreComment(per_message_list,offset_value)
                # 将多人回复页数据一页的List分别加入total_message_list
                for i in detail_list:
                    total_message_list.append(i)
        self.file_save(total_message_list)

    def GetMoreComment(self,per_message_list,offset_value):
        count = 0
        res_list = []
        # 解析多人回复详情页调用
        for item in per_message_list:
            # 多人回复的翻页 数量： i*10
            for i in range(0, self.detail_maxOffset):
                # 评论ID作父ID，查找子元素
                url = self.detail_url.format(i, item['评论ID'])
                print('[正在请求]  第 {} 大页 \t 第 {}/19 楼层 \t 多人回复第 {} 页'.format(offset_value, count, i))
                # 请求数据
                response = self.get_comment_data(url)
                if (response != None):
                    # 解析多人回复页数据，返回一页的List
                    try:
                        per_message_list_list = self.comment_xpath(url, response)
                        for per_message_list in per_message_list_list:
                            res_list.append(per_message_list)
                    except Exception as e:
                        print("\033[1;31m数据处理发生异常~~ URL:\033[0m" + url)
                        break
                else:
                    print("\033[1;34m该楼层数据已请求结束\033[0m")
                    break
            count += 1
        return res_list


class AnalyseCommentData():
    #  爬取评论数据 GET
    def __init__(self):
        self.comment_path = 'data/comment.csv' # 文件保存位置

    def file_read(self):
        data_list = []
        try:
            # 字典
            with open(self.comment_path, 'r', encoding='utf-8-sig') as fp:
                reader = csv.DictReader(fp)
                for item in reader:
                    data_list.append(item['评论内容'])
            return data_list
        except Exception as e:
            print("\033[1;31m文件读取出错:\033[0m" + self.comment_path)
            print(e)

    def readwords_list(self, filepath):
        '''
        读取文件函数，以行的形式读取词表，返回列表
        :param filepath: 路径地址
        :return:
        '''
        wordslist = [line.strip() for line in open(filepath, 'r', encoding='utf-8').readlines()]
        return wordslist

    def readwords_dict(self, filepath):
        '''
        读取文件函数，返回字典
        :param filepath: 路径地址
        :return:
        '''
        wordslist = [line.strip() for line in open(filepath, 'r', encoding='utf-8').readlines()]
        result_dict = defaultdict()
        # 读取字典文件每一行内容，将其转换为字典对象，key为情感词，value为对应的分值
        for s in wordslist:
            if s != '':
                # 每一行内容根据空格分割，索引0是词，索引1是分值
                if '\t' in s:
                    result_dict[s.split('\t')[0]] = s.split('\t')[1]  # 以\t分割
                else:
                    result_dict[s.split(' ')[0]] = s.split(' ')[1]  # 以空格分割
        return result_dict

    def cutsentences(self, sentences):
        '''
        分词的实现
        :param sentences:
        :return:
        '''
        # print('\n' + '原句子为：' + sentences)
        cut_result_list = jieba.lcut(sentences.strip())  # 精确模式
        # print('分词后：' + "/ ".join(cut_result_list))
        return cut_result_list

    def stopword_sentence(self, cut_result_list, stop_words):
        '''
        删去停用词
        :param cut_result_sentence: 分词后的结果
        :param stop_words:
        :return:
        '''
        stop_result_sentence = []
        for word in cut_result_list:  # for循环遍历分词后的每个词语
            if word not in stop_words and word != ' ' and word != '\n':  # 判断分词后的词语是否在停用词表内
                stop_result_sentence.append(word)
                # stop_result_sentence += "/"
        # print('删去停用词后：' + stop_result_sentence + '\n')
        return stop_result_sentence

    # 特征选择：TF-IDF算法
    def feature_select(self, list_words):
        # 总词频统计，即计算一共有多少词
        doc_frequency = defaultdict(int)
        for list_word in list_words:
            for i in list_word:
                doc_frequency[i] += 1

        #  计算每个词的词频即TF值：出现次数/总次数
        word_tf = {}
        for i in doc_frequency:
            word_tf[i] = doc_frequency[i] / sum(doc_frequency.values())

        #   计算逆文档频率 IDF：Log(语料库的文档总数/（包含该词的文档数+1）)，
        #   IDF大概为丑化因子，用来区别在多少文档出现，权重小即区分度大。在word_idf数值中已经做丑化，所以直接相乘
        word_idf = {}
        doc_num = len(list_words)  # 总文章数
        word_doc = defaultdict(int)  # 包含该词的文章数
        for i in doc_frequency:
            for j in list_words:
                if i in j:
                    word_doc[i] += 1
        for i in doc_frequency:
            word_idf[i] = math.log(doc_num / (word_doc[i] + 1))

        # 计算每个词的 tf * idf
        word_tf_idf = {}
        for i in doc_frequency:
            word_tf_idf[i] = word_tf[i] * word_idf[i]

        #   提取多少特征，需要先对字典由大到小排序
        dict_feature_select = sorted(word_tf_idf.items(), key=operator.itemgetter(1), reverse=True)
        return dict_feature_select

    def AlalyseMain(self):
        # 读取停用词文件
        stopwords_filepath = 'data/stopwords_1208.txt'
        stop_list = self.readwords_list(stopwords_filepath)

        sentence_cuted = []
        sentences_list = self.file_read()

        for sentence in sentences_list:
            # 1. 分词
            cut_results_list = self.cutsentences(sentence)
            # 2. 去掉停用词，过滤掉某些字或词
            stoped_results = self.stopword_sentence(cut_results_list, stop_list)
            sentence_cuted.append(stoped_results)
        features = self.feature_select(sentence_cuted)
        print('TF-TDF分析结果为：')
        print(features[:15])

class Menu():
    def __init__(self):
        self.choices = {
            "1": GetCommentData().CommentMain,
            "2": AnalyseCommentData().AlalyseMain,
            # "3": self.thing.Analyse,
            "4": self.quit
        }

    def display_menu(self):
        print("""
操作菜单:
1. 爬取数据
2. 评论分析(TF-TDF)
3. 评论分析
4. 退出
""")

    def run(self):
        while True:
            self.display_menu()
            try:
                choice = input("键入选项: ")
            except Exception as e:
                print("\033[1;31m输入无效\033[0m")
                continue

            choice = str(choice).strip()
            action = self.choices.get(choice)
            if action:
                action()
            else:
                print("{0} 不是有效选择".format(choice))

    def quit(self):
        print("\n感谢使用!\n")
        sys.exit(0)

if __name__ == '__main__':
    Menu().run()