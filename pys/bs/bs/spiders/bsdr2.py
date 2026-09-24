import scrapy

class bsdr2(scrapy.Spider):
    name = 'bsdr2'
    start_urls = [
            "https://www.bilibili.com",
            ]

    def parse(self, response):
        divs = response.xpath("//div[@class='bili-video-card__wrap']")
        for i in divs:
            yield {
                    "title" : i.xpath(".//a/text()").get(),
                    "hrefs" : i.xpath(".//a/@href").get(),
                    "srcs"  : response.urljoin(i.xpath(".//img/@src").get()),
                    }
