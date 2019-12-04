import re
from lxml import etree
import requests
import pymongo
import math

# 设置User-Agent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"}

# 获取所有区的信息
def get_districts():
    url = "https://sh.lianjia.com/ershoufang"
    r = requests.get(url, headers=headers)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    # 获取所有区所在的div
    div_nodes = root.xpath('//div[@data-role="ershoufang"]')
    # div_nodes中只有一个元素，讲这个元素拿出来存到div_node中
    div_node = div_nodes[0]
    # 获取div_node下所有的a节点
    a_nodes = div_node.xpath('./div/a')
    # result用来存放所有的区的信息
    result = []
    for a_node in a_nodes:
        # 获取区的名字
        district_name = a_node.text
        # 获取区的URL
        district_url = "https://sh.lianjia.com" + a_node.attrib["href"]
        # 讲区的名字和区的URL添加到result中
        result.append([district_name, district_url])
        print(district_name)
    return result

# 获取所有板块的信息
def get_sub_districts():
    # 获取所有的区的信息
    districts = get_districts()
    # 创建一个到MongoDB的链接
    client = pymongo.MongoClient()
    # 我们的数据存在名字叫house的数据库里
    db = client["house"]
    for district in districts:
        # 拿到区的名字
        district_name = district[0]
        # 拿到区的URL
        district_url = district[1]
        # 往区的URL发送请求
        r = requests.get(district_url, headers=headers)
        # 得到返回的页面内容
        content = r.content.decode("utf-8")
        # 将页面的HTML代码转成root节点
        root = etree.HTML(content)
        # 使用xpath获取所有的包含板块信息的节点，存到a_nodes里面
        a_nodes = root.xpath('//div[@data-role="ershoufang"]/div[2]/a')
        for a_node in a_nodes:
            # 获取板块的名字
            sub_district_name = a_node.text
            # 获取板块的URL
            sub_district_url = "https://sh.lianjia.com" + a_node.attrib["href"]
            # 将区名、板块名和板块URL存到MongoDB
            db.subdistricts.insert({"district_name": district_name, "sub_district_name": sub_district_name,
                                    "sub_district_url": sub_district_url})

# 获取一共多少套房源
def get_page_num(sub_district_url):
    # 获取某一板块页面的HTML内容
    r = requests.get(sub_district_url, headers=headers)
    content = r.content.decode("utf-8")
    root = etree.HTML(content)
    # 通过xpath获取包含房源数量的节点
    span_node = root.xpath('//h2[contains(@class, "total")]/span')[0]
    # 将字符串形式的数字转成整数类型
    num = int(span_node.text)
    return num

# 获取板块内的所有房源
def get_houses_by_sub_district(district_name, sub_district_name, sub_district_url):
    # 获取板块内一共有多少套房源
    house_num = get_page_num(sub_district_url)
    # 每页有30套房源，计算一共有几页内容，也就是有几页要爬
    page_num = math.ceil(house_num/30)
    # 建立一个到MongoDB的链接
    client = pymongo.MongoClient()
    # 我们的房源数据存到一个叫house的数据库里
    db = client["house"]
    for i in range(1, page_num+1, 1):
        # url_patt用来定义板块内每一页的URL格式
        url_patt = sub_district_url + "pg{}"
        # 传入页码，将url_patt转成一个url
        url = url_patt.format(i)
        # 发送请求获取该页的HTML
        r = requests.get(url, headers=headers)
        content = r.content.decode("utf-8")
        # 将HTML转成root节点
        root = etree.HTML(content)
        # 通过xpath定位到包含房源信息的节点，存到li_nodes
        li_nodes = root.xpath('//ul[@class="sellListContent"]/li')
        for li_node in li_nodes:
            # 获取房源的描述
            title = li_node.xpath('.//div[@class="title"]/a')[0].text
            # 获取包含户型、面积、朝向等房源信息的节点
            info_nodes = li_node.xpath('.//div[@class="address"]/div[@class="houseInfo"]/span')
            # 获取包含小区信息的节点
            xiaoqu_nodes = li_node.xpath('.//div[@class="flood"]/div[@class="positionInfo"]/a')
            # 获取包含总价信息的节点
            price_nodes = li_node.xpath('.//div[@class="priceInfo"]/div[@class="totalPrice"]/span')
            # 获取包含房源单价的节点
            up_nodes = li_node.xpath('.//div[@class="priceInfo"]/div[@class="unitPrice"]/span')
            # 将总价初始化为0
            price = 0
            if len(price_nodes) > 0:
                # 获取房源的总价，并将它转成浮点数
                price = float(price_nodes[0].text)

            # 将单价初始化为0
            up_price = 0
            if len(up_nodes) > 0:
                # 获取包含房源单价的文本
                up_text = up_nodes[0].text
                # 用正则匹配获取其中的单价数字
                matched = re.search(r'单价(.*)元/平米', up_text)
                if matched:
                    # 将字符串形式的单价转成浮点数类型
                    up_price = float(matched.group(1))

            # 初始化小区名字
            xiaoqu_name = ""
            if len(xiaoqu_nodes) > 0:
                # 获取小区的名字
                xiaoqu_node = xiaoqu_nodes[0]
                xiaoqu_name = xiaoqu_node.text

            # 初始化面积
            size = 0
            # 初始化建造年代
            buildyear = 0
            # 初始化户型
            huxing = ""
            # 初始化朝向
            chaoxiang = ""
            # 初始化装修风格
            zhuangxiu = ""
            # 初始化层高
            cenggao = ""
            # 初始化楼型
            louxing = ""
            if len(info_nodes) > 0:
                # 获取包含面积、户型、朝向等信息的文本, 这个文本是类似这样的形式
                # 2室1厅 | 55.69平米 | 南 | 精装 | 高楼层(共6层) | 1996年建 | 板楼
                info_text = info_nodes[0].tail
                # 将这个文本按照 | 做分割
                parts = info_text.split("|")
                # 获取包含面积信息的文本，也就是下标为1的这一个元素
                size_text = parts[1]
                # 获取包含建造年代的文本，也就是下标为5的这一个元素
                buildyear_text = parts[5]
                # 用正则匹配获取面积数字
                matched = re.search(r'([\d\.]+)平米', size_text)
                if matched:
                    # 将字符串形式的面积转成浮点数类型
                    size = float(matched.group(1))

                # 用正则匹配获取建造年代
                matched = re.search(r'(\d+)年建', buildyear_text)
                if matched:
                    # 将字符串形式的建造年代转成整数类型
                    buildyear = int(matched.group(1))
                    # 获取户型信息，也就是parts里面下标为0的这一个元素
                    huxing = parts[0]
                    # 获取朝向，也就是parts里面下标为2的这一个元素
                    chaoxiang = parts[2]
                    # 获取装修风格，也就是parts里面下标为3的这一个元素
                    zhuangxiu = parts[3]
                    # 获取层高，也就是parts里面下标为4的这一个元素
                    cenggao = parts[4]
                    # 获取楼型，也就是parts里面下标为6的这一个元素
                    louxing = parts[6]

            # 将房源信息写入MongoDB
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

# 获取所有区所有板块内的房源
def get_all_houses():
    # 建立一个到MongoDB的链接
    client = pymongo.MongoClient()
    # 我们的数据存在一个叫house的数据库里
    db = client["house"]
    # 从MongoDB里读取所有的区和板块信息
    cursor = db.subdistricts.find()
    # 设置开始爬取标志位，只有当标志位为True的时候才开始爬
    # 通过标志位，可以实现断点续爬的功能
    start = False
    for item in cursor:
        # 拿到区的名字
        district_name = item["district_name"]
        # 拿到板块的名字
        sub_district_name = item["sub_district_name"]
        # 拿到板块的URL
        sub_district_url = item["sub_district_url"]
        # 跳过爬过的区和板块，只有当下面的判断为真的时候，才把标志位start设成True
        if district_name == "杨浦" and sub_district_name == "控江路":
            start = True
        # 检查标志位，当标志位为True的时候，才开始爬
        if start:
            print(district_name, sub_district_name)
            get_houses_by_sub_district(district_name, sub_district_name, sub_district_url)

if __name__ == "__main__":
    # 调用的时候分两步
    # 先调用 get_sub_districts 获取所有板块信息
    # 然后调用 get_all_houses 获取所有房源

    # get_sub_districts()
    get_all_houses()

