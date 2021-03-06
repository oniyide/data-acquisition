import scrapy
from scrapy.http import HtmlResponse
import logging
import json
import matplotlib.pyplot as plt
import numpy as np
import w3lib.html
import nltk
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
plt.rcdefaults()
nltk.download('punkt')


class OpinionsSpider(scrapy.Spider):
    name = 'debate_crawler'
    allowed_domains = ['debate.org']
    base_url = 'https://www.debate.org'
    start_urls = [
        'https://www.debate.org/opinions/?sort=popular',
    ]
    custom_settings = {'ROBOTSTXT_OBEY': False,
                       'FEED_FORMAT': 'json',
                       'FEED_URI': 'data.json'
                       }
    ajax_url = 'https://www.debate.org/opinions/~services/opinions.asmx/GetDebateArgumentPage'
    headers = {
        'Host': 'www.debate.org',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': 'https://www.debate.org',
        # 'Referer': 'https://www.debate.org/opinions/will-your-answer-to-this-question-be-no',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7',
        'Cookie': '_ga=GA1.2.282588858.1619694587; _gid=GA1.2.2080027860.1619694587; DDOSession=d2ce97c1-e1e1-4143-b20e-d986937b2353; ASP.NET_SessionId=aot2zr1pcig025iqcn0qzeo2'
    }
    pro_arguments = []
    con_arguments = []
    topic = ''
    category = ''
    popular_urls = []
    stats = []
    category_stats = []
    token_counts = []

    @staticmethod
    def construct_json_str(index, debateId):
        return '{"debateId":"' + \
               debateId + \
               '","itemsPerPage":"10","nsort":"5","pageNumber":' + \
               str(index) + \
               ',"ysort":"5"}'

    def start_requests(self):
        open('./data.json', 'w').close()
        page = 'https://www.debate.org/opinions/?sort=popular'
        yield scrapy.http.Request(page, callback=self.parse_1)

    def parse_1(self, response):
        for x in range(5):
            url = response.css("a.a-image-contain")[x].attrib['href']
            self.popular_urls.append(self.base_url + url)
            yield scrapy.http.Request(self.base_url + url, callback=self.parse)

    def parse(self, response):
        topic = response.css('span.q-title::text').get()
        category = response.css('div#breadcrumb a::text')[2].get()
        debateId = response.css('div#voting').attrib['did']
        index = 1  # or 2?
        data = self.construct_json_str(index, debateId)
        logging.info(f"data is {data}")
        yield scrapy.http.Request(self.ajax_url,
                                  callback=self.parse_detail,
                                  method='POST',
                                  body=data,
                                  headers=self.headers,
                                  meta={
                                      'debateId': debateId,
                                      'index': index,
                                      'topic': topic,
                                      'category': category,
                                      'pro_arguments': [],
                                      'con_arguments': [],
                                      'pro_arg_count': 0,
                                      'con_arg_count': 0,
                                  })

    def parse_detail(self, response):
        loaded_data = json.loads(response.body)
        d = loaded_data['d']
        if d != "{ddo.split}{ddo.split}finished":
            logging.info(f"d {d}")
            arguments = d.split("{ddo.split}")
            pro_html = arguments[0]
            con_html = arguments[1]
            pro_html_res = HtmlResponse(url="pro arguments", body=pro_html, encoding='utf-8')
            con_html_res = HtmlResponse(url="con arguments", body=con_html, encoding='utf-8')

            if bool(pro_html_res):
                response.meta['pro_arg_count'] += len(pro_html_res.css('li.hasData'))
                for pro_htm in pro_html_res.css('li.hasData'):
                    title = pro_htm.css('h2::text').get()
                    if title is None:
                        title = pro_htm.css('h2 a::text').get()
                    raw_body = pro_htm.css('li.hasData p').get()
                    body = w3lib.html.remove_tags(raw_body)
                    self.token_counts.append(len(nltk.word_tokenize(body)))
                    response.meta['pro_arguments'].append({
                        'title': title,
                        'body': body })
            if bool(con_html_res):
                response.meta['con_arg_count'] += len(con_html_res.css('li.hasData'))
                for con_htm in con_html_res.css('li.hasData'):
                    title = con_htm.css('h2::text').get()
                    if title is None:
                        title = con_htm.css('h2 a::text').get()
                    raw_body = con_htm.css('li.hasData p').get()
                    body = w3lib.html.remove_tags(raw_body)
                    self.token_counts.append(len(nltk.word_tokenize(body)))
                    response.meta['con_arguments'].append({
                        'title': title,
                        'body': body})
            previous_index = response.meta['index']
            index = previous_index + 1
            debateId = response.meta['debateId']
            data = self.construct_json_str(index, debateId)
            yield scrapy.http.Request(self.ajax_url,
                                      callback=self.parse_detail,
                                      method='POST',
                                      body=data,
                                      headers=self.headers,
                                      dont_filter=True,
                                      meta={
                                          'debateId': debateId,
                                          'index': index,
                                          'topic': response.meta['topic'],
                                          'category': response.meta['category'],
                                          'pro_arguments': response.meta['pro_arguments'],
                                          'con_arguments': response.meta['con_arguments'],
                                          'pro_arg_count': response.meta['pro_arg_count'],
                                          'con_arg_count': response.meta['con_arg_count']})
        else:
            yield {
                'topic': response.meta['topic'],
                'category': response.meta['category'],
                'pro_arguments': response.meta['pro_arguments'],
                'con_arguments': response.meta['con_arguments']
            }
            self.stats.append({
                'topic': response.meta['topic'],
                'category': response.meta['category'],
                'pro_arg_count': response.meta['pro_arg_count'],
                'con_arg_count': response.meta['con_arg_count']
            })
            if len(self.category_stats) == 0:
                self.category_stats.append({
                    'category': response.meta['category'],
                    'pro_arg_count': response.meta['pro_arg_count'],
                    'con_arg_count': response.meta['con_arg_count'], })
            else:
                if not any(x['category'] == response.meta['category'] for x in self.category_stats):
                    self.category_stats.append({
                        'category': response.meta['category'],
                        'pro_arg_count': response.meta['pro_arg_count'],
                        'con_arg_count': response.meta['con_arg_count'], })
                else:
                    for x in range(len(self.category_stats)):
                        if self.category_stats[x]['category'] == response.meta['category']:
                            self.category_stats[x]['pro_arg_count'] += response.meta['pro_arg_count']
                            self.category_stats[x]['con_arg_count'] += response.meta['con_arg_count']
                            break
            self.pro_arguments.clear()
            self.con_arguments.clear()

    def closed(self, reason):
        print(self.stats)
        timestamp = datetime.now().strftime("%Y_%m_%d-%I:%M:%S_%p").replace(":", "")
        with PdfPages('./rendered_stats-' + timestamp + '.pdf') as pdf:

            plt.hist(self.token_counts, bins=10, edgecolor='black')
            plt.title('Histogram of argument lengths')
            plt.xlabel('Length of arguments (as number of tokens)')
            plt.ylabel('Number of arguments')
            plt.tight_layout()
            pdf.savefig()
            plt.close()

            ########
            # histogram of arguments
            topics = [''.join([x[0] for x in o['topic'].split()])[0:10] for o in self.stats]
            y_pos = np.arange(len(topics))
            arg_lengths = [o['pro_arg_count'] + o['con_arg_count'] for o in self.stats]
            plt.bar(y_pos, arg_lengths, align='center', alpha=0.5)
            plt.xticks(y_pos, topics)
            plt.ylabel('Argument Count')
            plt.xlabel('Topics')
            plt.rc('xtick', labelsize=6)  # fontsize of the tick labels
            plt.title('Bar chart of argument counts')
            pdf.savefig()
            plt.close()

            ########
            # barchart of number of pro/con argument per topic
            labels = [''.join([x[0] for x in o['topic'].split()])[0:10] for o in self.stats]
            pro_counts = [o['pro_arg_count'] for o in self.stats]
            con_counts = [o['con_arg_count'] for o in self.stats]
            x = np.arange(len(labels))  # the label locations
            width = 0.35  # the width of the bars
            fig, ax = plt.subplots()
            rects1 = ax.bar(x - width / 2, pro_counts, width, label='Pro Arguments')
            rects2 = ax.bar(x + width / 2, con_counts, width, label='Con Arguments')
            ax.set_ylabel('Number of Arguments')
            ax.set_xlabel('Topics')
            ax.set_title('Bar chart of number of pro/con argument per topic')
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()
            ax.bar_label(rects1, padding=3)
            ax.bar_label(rects2, padding=3)
            fig.tight_layout()
            pdf.savefig()
            plt.close()

            ########
            # barchart of number of pro/con argument per Category
            labels = [o['category'] for o in self.category_stats]
            pro_counts = [o['pro_arg_count'] for o in self.category_stats]
            con_counts = [o['con_arg_count'] for o in self.category_stats]
            x = np.arange(len(labels))  # the label locations
            width = 0.35  # the width of the bars
            fig, ax = plt.subplots()
            rects1 = ax.bar(x - width / 2, pro_counts, width, label='Pro Arguments')
            rects2 = ax.bar(x + width / 2, con_counts, width, label='Con Arguments')
            # Add some text for labels, title and custom x-axis tick labels, etc.
            ax.set_ylabel('Number of Arguments')
            ax.set_xlabel('Category')
            ax.set_title('Bar chart of number of pro/con argument per category')
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.legend()
            ax.bar_label(rects1, padding=3)
            ax.bar_label(rects2, padding=3)
            pdf.savefig()
            plt.close()

            d = pdf.infodict()
            d['Title'] = 'Multipage PDF Example'
            d['Author'] = u'OnKaLaNa\xe4nen'
            d['Subject'] = 'Preliminary Statistics - Perform preliminary statistics to learn about the crawled data'
            d['Keywords'] = 'Data Crawling'
