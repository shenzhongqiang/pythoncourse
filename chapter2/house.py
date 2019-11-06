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

def get_houses_by_sub_district(sub_distr_id, entry_url):
    url_patt = entry_url + "pg{}/"

    total_num = get_item_num(entry_url)
    last_page = math.ceil(total_num/30)
    i = 1
    client = pymongo.MongoClient()
    db = client[DB]
    for i in range(1, last_page+1, 1):
        url = url_patt.format(i)
        print(url)
        r = requests.get(url, headers=headers, verify=False)
        content = r.content.decode("utf-8")
        root = etree.HTML(content)
        content_node = root.find('.//div[@class="content "]')
        if content_node is None:
            print(url)
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

            xiaoqu_nodes = div_node.xpath('./div[@class="address"]/div[@class="houseInfo"]/a')
            xiaoqu_name = ""
            house_info = ""
            if len(xiaoqu_nodes) > 0:
                xiaoqu_name = xiaoqu_nodes[0].text
                house_info = xiaoqu_nodes[0].tail

            pos_nodes = div_node.xpath('./div[@class="flood"]/div[@class="positionInfo"]/span')
            building_info = ""
            if len(pos_nodes) > 0:
                building_info = pos_nodes[0].tail
                if building_info:
                    matched = re.search(r'(.*)\s+-\s+$', building_info)
                    if matched:
                        building_info = matched.group(1)

            area_nodes = div_node.xpath('./div[@class="flood"]/div[@class="positionInfo"]/a')
            area = ""
            if len(area_nodes) > 0:
                area_node = area_nodes[0]
                area = area_node.text

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

            tax_nodes = div_node.xpath('./div[@class="tag"]/span[@class="taxfree"]')
            tax_info = ""
            if len(tax_nodes) > 0:
                tax_node = tax_nodes[0]
                tax_info = tax_node.text

            price_nodes = div_node.xpath('./div[@class="priceInfo"]/div[@class="totalPrice"]/span')
            price_num = 0
            price_unit = ""
            if len(price_nodes) > 0:
                price_node = price_nodes[0]
                price_num = price_node.text
                price_unit = price_node.tail

            up_nodes = div_node.xpath('./div[@class="priceInfo"]/div[@class="unitPrice"]')
            unit_price = 0
            if len(up_nodes) > 0:
                up_node = up_nodes[0]
                unit_price = up_node.attrib["data-price"]

            item = {
                "item_id": housecode,
                "sub_distr_id": sub_distr_id,
                "title": title,
                "url": url,
                "house_info": house_info,
                "xiaoqu_name": xiaoqu_name,
                "building_info": building_info,
                "area": area,
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
    start = False
    for sub_distr in sub_distr_rows:
        entry_url = sub_distr["url"]
        sub_distr_id = sub_distr["_id"]
        distr_name = sub_distr["district"]
        sub_distr_name = sub_distr["sub_district"]
        print(distr_name, sub_distr_name)
        if distr_name == "浦东" and sub_distr_name == "川沙":
            start = True
        if start:
            get_houses_by_sub_district(sub_distr_id, entry_url)


if __name__ == "__main__":
    #get_sub_districts()
    get_all_houses()
