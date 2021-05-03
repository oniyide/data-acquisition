import scrapy
from scrapy.http import HtmlResponse
import logging
import json
from ..items import DataAcquisitionItem


class OpinionsSpider(scrapy.Spider):
    name = 'opinions'
    allowed_domains = ['debate.org']
    base_url = 'https://www.debate.org'
    start_urls = [
        'https://www.debate.org/opinions/?sort=popular',
        'https://www.debate.org/opinions/kirk-will-always-be-better-than-picard',
        'https://www.debate.org/opinions/opinions/do-you-agree-with-the-black-lives-matter-movement-1',
        'https://www.debate.org/opinions/opinions/we-should-institute-a-death-penalty-for-homophiles-and-transexualists',
        'https://www.debate.org/opinions/do-you-agree-with-the-derek-chauvin-guilty-verdict-announced-on-april-20-2021',
        'https://www.debate.org/opinions/is-lgbtq-wrong',
    ]
    custom_settings = {'ROBOTSTXT_OBEY': False}
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
    items = DataAcquisitionItem()
    pro_arguments = []
    con_arguments = []
    topic = ''
    category = ''

    @staticmethod
    def construct_json_str(index, debateId):
        return '{"debateId":"' + \
               debateId + \
               '","itemsPerPage":"10","nsort":"5","pageNumber":' + \
               str(index) + \
               ',"ysort":"5"}'

    '''
    def __init__(self, *args, **kwargs):
        super(OpinionsSpider, self).__init__(*args, **kwargs)
        self.start_urls = [kwargs.get('start_url')]
    '''

    def start_requests(self):
        for x in range(6):
            if x == 0:
                yield scrapy.Request(url='https://www.debate.org/opinions/?sort=popular', callback=self.parse)
            else:
                yield scrapy.Request(url=self.start_urls[x], callback=self.parse)
    '''
    def start_requests(self):
        for url in self.start_urls:
            if url == 'https://www.debate.org/opinions/?sort=popular':
                yield scrapy.Request(url=url, callback=self.parse)
            else:
                yield scrapy.Request(url=self.url, callback=self.parse)
    '''

    def parse(self, response):
        page = response.url
        if page == 'https://www.debate.org/opinions/?sort=popular':
            for x in range(5):
                url = response.css("a.a-image-contain")[x].attrib['href']
                self.start_urls.append(self.base_url + url)
        else:
            topic = response.css('span.q-title::text').get()
            category = category = response.css('div#breadcrumb a::text')[2].get()
            self.items['topic'] = self.topic
            self.items['category'] = self.category

            debateId = response.css('div#voting').attrib['did']
            index = 1  # or 2?
            data = self.construct_json_str(index, debateId)
            logging.info(f"data is {data}")
            # x = requests.post(self.ajax_url, data, headers=self.headers)
            # print(x.content)
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
                                            })

    def parse_detail(self, response):
        loaded_data = json.loads(response.body)
        d = loaded_data['d']
        if d != "{ddo.split}{ddo.split}finished":
            logging.info(f"d {d}")
            arguments = d.split("{ddo.split}")
            pro_html = arguments[0]
            con_html = arguments[1]
            # html = d[:-19]
            pro_html_res = HtmlResponse(url="pro arguments", body=pro_html, encoding='utf-8')
            con_html_res = HtmlResponse(url="con arguments", body=con_html, encoding='utf-8')

            if bool(pro_html_res):
                for pro_htm in pro_html_res.css('li.hasData'):
                    title = pro_htm.css('h2::text').get()
                    if title is None:
                        title = pro_htm.css('h2 a::text').get()
                    raw_body = pro_htm.css('li.hasData p')

                    body = ''
                    for txt in raw_body:
                        body += txt.css('::text').get() + " "
                    # body.replace("\r", "")
                    response.meta['pro_arguments'].append({
                        'title': title,
                        'body': body
                    })

            if bool(con_html_res):
                for con_htm in con_html_res.css('li.hasData'):
                    title = con_htm.css('h2::text').get()
                    if title is None:
                        title = con_htm.css('h2 a::text').get()
                    raw_body = con_htm.css('li.hasData p')
                    body = ''
                    for txt in raw_body:
                        body += txt.css('::text').get() + "\\n"
                    response.meta['con_arguments'].append({
                        'title': title,
                        'body': body
                    })
            previous_index = response.meta['index']
            # res = HtmlResponse(url="my HTML string", body=html, encoding='utf-8')
            index = previous_index + 1
            # data = self.data
            debateId = response.meta['debateId']
            # debateId = pro_html_res.css('li.hasData')[0].attrib['did']
            data = self.construct_json_str(index, debateId)
            # yield scrapy.http.Request(self.ajax_url,
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
                                          'con_arguments': response.meta['con_arguments']
                                      })
        else:
            print("I'm here" + d)
            yield {
                'topic': response.meta['topic'],
                'category': response.meta['category'],
                'pro_arguments': response.meta['pro_arguments'],
                'con_arguments': response.meta['con_arguments']
            }
            self.pro_arguments.clear()
            self.con_arguments.clear()
