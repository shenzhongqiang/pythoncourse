import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import math
import re
from lxml import etree
import time
import json
import pymongo
import requests

DB = "house"
base_url = "https://sh.lianjia.com"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36"}


def get_disctricts():
    url = base_url + "/ershoufang/"
    r = requests.get(url, headers=headers, verify=False)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    distr_nodes = root.xpath('.//div[@class="m-filter"]//div[@data-role="ershoufang"]/div/a')
    result = []
    for node in distr_nodes:
        rel_url = node.attrib["href"]
        distr_url = ""
        if re.match(r'https://', rel_url):
            distr_url = rel_url
        else:
            distr_url = base_url + rel_url
        distr_name = node.text
        result.append([distr_name, distr_url])
    return result

def get_sub_districts():
    districts = get_disctricts()
    result = []
    client = pymongo.MongoClient()
    db = client[DB]
    for item in districts:
        distr_name = item[0]
        distr_url = item[1]
        r = requests.get(distr_url, headers=headers, verify=False)
        content = r.content.decode("utf-8")
        root = etree.HTML(content)
        subdistr_nodes = root.xpath('.//div[@class="m-filter"]//div[@data-role="ershoufang"]/div')[1].xpath('./a')
        for node in subdistr_nodes:
            sub_distr_name = node.text
            sub_distr_url = base_url + node.attrib["href"]
            db.sub_districts.insert_one({
                "district": distr_name,
                "sub_district": sub_distr_name,
                "url": sub_distr_url,
            })

def get_item_num(entry_url):
    r = requests.get(entry_url, headers=headers, verify=False)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    num_nodes = root.xpath('.//div[@class="content "]//h2[contains(@class, "total")]/span')
    if len(num_nodes) == 0:
        raise Exception("no total number for {}".format(entry_url))
    num_str = num_nodes[0].text.strip()
    return int(num_str)

def get_houses_by_sub_district(sub_distr_id, distr_name, sub_distr_name, entry_url):
    url_patt = entry_url + "pg{}/"

    total_num = get_item_num(entry_url)
    last_page = math.ceil(total_num/30)
    i = 1
    client = pymongo.MongoClient()
    db = client[DB]
    for i in range(1, last_page+1, 1):
        url = url_patt.format(i)
        r = requests.get(url, headers=headers, verify=False)
        content = r.content.decode("utf-8")
        root = etree.HTML(content)
        content_node = root.find('.//div[@class="content "]')
        if content_node is None:
            r = requests.get(url, headers=headers, verify=False)
            content = r.content.decode("utf-8")
            root = etree.HTML(content)
            ul_node = root.find('.//div[@class="content "]')

        ul_node = root.xpath('.//ul[contains(@class, "sellListContent")]')
        if len(ul_node) == 0:
            print(etree.tostring(root))

        div_info = ul_node[0].xpath('.//div[contains(@class, "info")]')
        for div_node in div_info:
            title_nodes = div_node.xpath('./div[@class="title"]/a[@data-el="ershoufang"]')
            if len(title_nodes) == 0:
                print("title not found")
                continue
            title_node = title_nodes[0]
            title = title_node.text
            housecode = title_node.attrib["data-housecode"]
            url = title_node.attrib["href"]

            info_nodes = div_node.xpath('./div[@class="address"]/div[@class="houseInfo"]/span')
            size = 0
            build_year = 0
            house_info = ""
            building_info = ""
            huxing = ""
            zhuangxiu = ""
            if len(info_nodes) > 0:
                print(etree.tostring(info_nodes[0]))
                house_info = info_nodes[0].tail
                parts = house_info.split("|")
                size_text = parts[1]
                matched = re.search(r'(.*)平米', size_text)
                if matched:
                    size = float(matched.group(1))
                    print(size)

                year_text = parts[5]
                matched = re.search(r'(.*)年建', year_text)
                if matched:
                    build_year = int(matched.group(1))
                    print(build_year)
                print(house_info)

                building_info = parts[4]
                huxing = parts[0]
                zhuangxiu = parts[3]

            xiaoqu_nodes = div_node.xpath('./div[@class="flood"]/div[@class="positionInfo"]/a')
            xiaoqu_name = ""
            if len(xiaoqu_nodes) > 0:
                xiaoqu_node = xiaoqu_nodes[0]
                xiaoqu_name = xiaoqu_node.text

            follow_nodes = div_node.xpath('./div[@class="followInfo"]/span')
            follow_info = ""
            if len(follow_nodes) > 0:
                follow_node = follow_nodes[0]
                follow_info = follow_node.tail

            subway_nodes = div_node.xpath('./div[@class="tag"]/span[@class="subway"]')
            subway_info = ""
            if len(subway_nodes) > 0:
                subway_node = subway_nodes[0]
                subway_info = subway_node.text

            tax_nodes = div_node.xpath('./div[@class="tag"]/span[@class="five"]')
            tax_info = ""
            if len(tax_nodes) > 0:
                tax_node = tax_nodes[0]
                tax_info = tax_node.text

            price_nodes = div_node.xpath('./div[@class="priceInfo"]/div[@class="totalPrice"]/span')
            price_num = 0
            price_unit = ""
            if len(price_nodes) > 0:
                price_node = price_nodes[0]
                price_num = float(price_node.text)
                price_unit = price_node.tail

            up_nodes = div_node.xpath('./div[@class="priceInfo"]/div[@class="unitPrice"]')
            unit_price = 0
            if len(up_nodes) > 0:
                up_node = up_nodes[0]
                unit_price = float(up_node.attrib["data-price"])

            item = {
                "item_id": housecode,
                "sub_distr_id": sub_distr_id,
                "distr_name": distr_name,
                "sub_distr_name": sub_distr_name,
                "title": title,
                "url": url,
                "house_info": house_info,
                "xiaoqu_name": xiaoqu_name,
                "huxing": huxing,
                "zhuangxiu": zhuangxiu,
                "building_info": building_info,
                "size": size,
                "build_year": build_year,
                "follow_info": follow_info,
                "subway_info": subway_info,
                "tax_info": tax_info,
                "price_num": price_num,
                "price_unit": price_unit,
                "unit_price": unit_price,
            }
            db.house.insert_one(item)
        i += 1

def get_all_houses():
    client = pymongo.MongoClient()
    db = client[DB]
    sub_distr_rows = db.sub_districts.find()
    start = True
    for sub_distr in sub_distr_rows:
        entry_url = sub_distr["url"]
        sub_distr_id = sub_distr["_id"]
        distr_name = sub_distr["district"]
        sub_distr_name = sub_distr["sub_district"]
        print(distr_name, sub_distr_name)
        if distr_name == "杨浦" and sub_distr_name == "五角场":
            start = True
        if start:
            get_houses_by_sub_district(sub_distr_id, distr_name, sub_distr_name, entry_url)

if __name__ == "__main__":
    get_all_houses()

