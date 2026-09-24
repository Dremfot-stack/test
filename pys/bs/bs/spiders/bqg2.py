import scrapy

class BQG(scrapy.Spider):
    name = "bqg2"
    start_urls = [
            'https://www.biquh.com/678_678189/66021618_2.html'
            ]

    def parse(self, response):
        title = response.xpath("//h1/text()").get()
        content = response.xpath("//div[@id='content']/text()").getall()
        for i in range(len(content)):
            content[i] = content[i].strip("&nbsp;")
            content[i] = content[i].strip()
        for i in range(len(content)-1,-1,-1):
            if content[i] == '':
                del content[i]
        summary = ''
        for i in range(len(content)):
            summary = '\n'.join([summary,content[i]])
        result = {
                'title':title,
                'url':response.url,
                'content':summary,
                }
        yield result
        
        if response.status != 200:
            print(response)
            yield None

        next_page = response.xpath("//a[text()='下一页']/@href").get()
        next_chapter = response.xpath("//a[text()='下一章']/@href").get()
        if next_page is not None:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)
        elif next_chapter is not None:
            next_chapter = response.urljoin(next_chapter)
            yield scrapy.Request(next_chapter, callback=self.parse)
        else:
            print('\n' + '#' * 10)
            print(response)
            print('\n' + '#' * 10)
            yield {
                    'title':response.status,
                    'url':response.url,
                    'content':response.xpath("//html")
                    }

