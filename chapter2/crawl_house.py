import re
from lxml import etree
import requests
import pymongo
import math

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"}

def get_districts():
    url = "https://sh.lianjia.com/ershoufang"
    r = requests.get(url, headers=headers)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    div_nodes = root.xpath('//div[@data-role="ershoufang"]')
    div_node = div_nodes[0]
    a_nodes = div_node.xpath('./div/a')
    result = []
    for a_node in a_nodes:
        district_name = a_node.text
        district_url = "https://sh.lianjia.com" + a_node.attrib["href"]
        result.append([district_name, district_url])
        print(district_name)
    return result

def get_sub_districts():
    districts = get_districts()
    client = pymongo.MongoClient()
    db = client["house"]
    for district in districts:
        district_name = district[0]
        district_url = district[1]
        r = requests.get(district_url, headers=headers)
        content = r.content.decode("utf-8")
        root = etree.HTML(content)
        a_nodes = root.xpath('//div[@data-role="ershoufang"]/div[2]/a')
        for a_node in a_nodes:
            sub_district_name = a_node.text
            sub_district_url = "https://sh.lianjia.com" + a_node.attrib["href"]
            db.subdistricts.insert({"district_name": district_name, "sub_district_name": sub_district_name,
                                    "sub_district_url": sub_district_url})

def get_page_num(sub_district_url):
    r = requests.get(sub_district_url, headers=headers)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    span_node = root.xpath('//h2[contains(@class, "total")]/span')[0]
    num = int(span_node.text)
    return num

def get_houses_by_sub_district(district_name, sub_district_name, sub_district_url):
    house_num = get_page_num(sub_district_url)
    page_num = math.ceil(house_num/30)
    client = pymongo.MongoClient()
    db = client["house"]
    for i in range(1, page_num+1, 1):
        url_patt = sub_district_url + "pg{}"
        url = url_patt.format(i)
        r = requests.get(url, headers=headers)
        content = r.content.decode("utf-8")
        root = etree.HTML(content)
        li_nodes = root.xpath('//ul[@class="sellListContent"]/li')
        for li_node in li_nodes:
            title = li_node.xpath('.//div[@class="title"]/a')[0].text
            info_nodes = li_node.xpath('.//div[@class="address"]/div[@class="houseInfo"]/span')
            xiaoqu_nodes = li_node.xpath('.//div[@class="flood"]/div[@class="positionInfo"]/a')
            price_nodes = li_node.xpath('.//div[@class="priceInfo"]/div[@class="totalPrice"]/span')
            up_nodes = li_node.xpath('.//div[@class="priceInfo"]/div[@class="unitPrice"]/span')
            price = 0
            if len(price_nodes) > 0:
                price = float(price_nodes[0].text)

            up_price = 0
            if len(up_nodes) > 0:
                up_text = up_nodes[0].text
                matched = re.search(r'单价(.*)元/平米', up_text)
                if matched:
                    up_price = float(matched.group(1))

            xiaoqu_name = ""
            if len(xiaoqu_nodes) > 0:
                xiaoqu_node = xiaoqu_nodes[0]
                xiaoqu_name = xiaoqu_node.text

            size = 0
            buildyear = 0
            huxing = ""
            chaoxiang = ""
            zhuangxiu = ""
            cenggao = ""
            louxing = ""
            if len(info_nodes) > 0:
                info_text = info_nodes[0].tail
                parts = info_text.split("|")
                size_text = parts[1]
                buildyear_text = parts[5]
                matched = re.search(r'([\d\.]+)平米', size_text)
                if matched:
                    size = float(matched.group(1))

                matched = re.search(r'(\d+)年建', buildyear_text)
                if matched:
                    buildyear = int(matched.group(1))
                    huxing = parts[0]
                    chaoxiang = parts[2]
                    zhuangxiu = parts[3]
                    cenggao = parts[4]
                    louxing = parts[6]

            house = {
                "title": title,
                "price": price,
                "up_price": up_price,
                "xiaoqu_name": xiaoqu_name,
                "size": size,
                "buildyear": buildyear,
                "huxing": huxing,
                "chaoxiang": chaoxiang,
                "zhuangxiu": zhuangxiu,
                "cenggao": cenggao,
                "louxing": louxing,
                "district_name": district_name,
                "sub_district_name": sub_district_name,
            }
            db.house.insert(house)

def get_all_houses():
    client = pymongo.MongoClient()
    db = client["house"]
    cursor = db.subdistricts.find()
    start = False
    for item in cursor:
        district_name = item["district_name"]
        sub_district_name = item["sub_district_name"]
        sub_district_url = item["sub_district_url"]
        # skip crawled district and sub district
        if district_name == "杨浦" and sub_district_name == "控江路":
            start = True
        if start:
            print(district_name, sub_district_name)
            get_houses_by_sub_district(district_name, sub_district_name, sub_district_url)

if __name__ == "__main__":
    get_all_houses()

