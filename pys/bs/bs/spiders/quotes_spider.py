import scrapy


class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = [
        "https://docs.scrapy.org/en/latest/intro/overview.html",
    ]

    def parse(self, response):
        with open("quotes.txt",'a',encoding="utf-8") as f:
            for quote in response.xpath("//*[@id]//h1/text()").getall():
                f.write(quote + "\n")
        next_page = response.xpath("/html/body/div/section/div/div/footer/div[1]/a[2]/@href").get()
        if next_page is not None:
            next_page = response.urljoin(next_page)
            yield scrapy.Request(next_page, callback=self.parse)
