import scrapy

class BQG(scrapy.Spider):
    name = "bqg"
    start_urls = [
            'https://www.biquh.com/678_678189/65638385.html#top'
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
        result = {
                'title':title,
                }
        for i in range(len(content)):
            result['content'+str(i)] = content[i]
        yield result

        next_page = response.xpath("//a[text()='下一页']/@href").get()
        if next_page is not None:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)
        else:
            next_page = response.xpath("//a[text()='下一章']/@href").get()
            if next_page is not None:
                next_page = response.urljoin(next_page)
                yield scrapy.Request(next_page, callback=self.parse)
