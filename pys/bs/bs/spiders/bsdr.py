import scrapy

class bsdr(scrapy.Spider):
    name = "bsdr"
    start_urls = [
            "https://bilibili.com"
            ]
    
    def parse(self, response):
        content = response.xpath("//img")
        image = content.xpath("./@src").getall()
        title = content.xpath("./@alt").getall()
        with open("videos.txt",'w',encoding="utf-8") as f:
            for t in title:
                f.write(t + '\n')
        for idx,img in enumerate(image):
            if img:
                url = response.urljoin(img)
                yield scrapy.Request(
                        url,
                        callback=self.save_image,
                        cb_kwargs={"idx":idx}
                    )

    def save_image(self, response, idx):
        with open("image" + str(idx) + ".jpg","wb") as f:
            f.write(response.body)

