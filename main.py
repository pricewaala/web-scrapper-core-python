import asyncio
import concurrent
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor

import grequests
import redis
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI,Request

import httpx
from pydantic import BaseModel

from ProductDetails import Product

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


async def getAmazonProductRatingStar(product_section):
    rating_star = product_section.find("span", class_="a-icon-alt")
    if rating_star is None:
        rating_star = "None"
    else:
        rating_star = rating_star.text
    return rating_star


async def getAmazonProductDescription(product_section):
    description = []
    description_ul_list = product_section.find("ul", class_="a-unordered-list a-vertical a-spacing-mini")
    if description_ul_list is not None:
        for li in description_ul_list.find_all("li"):
            description.append(li.text)
    return description


async def getAmazonProductExchangeAmount(right_product_section):
    exchange_amount = right_product_section.find("div", class_="a-section a-spacing-none a-padding-none show")
    if exchange_amount is None:
        exchange_amount = ""
    else:
        exchange_amount_span = exchange_amount.find("span", class_="a-color-price")
        if exchange_amount_span is not None:
            exchange_amount = exchange_amount_span.text.strip()
    return exchange_amount


async def getAmazonProductRatingCount(product_section):
    rating_count = product_section.find("span", id="acrCustomerReviewText")
    if rating_count is None:
        rating_count = ""
    else:
        rating_count = rating_count.text
    return rating_count


async def getAmazonProductTitleName(product_section):
    name = product_section.find("span", class_="a-size-large product-title-word-break")
    if name is None:
        name = None
    else:
        name = name.text.strip()
    return name


async def getAmazonProductTitleNameV2(center_product_section, left_center_product_section):
    name = center_product_section.find("span", class_="a-size-large product-title-word-break")
    if name is None:
        name1 = left_center_product_section.find("span", id="productTitle")
        if name1 is None:
            name1 = None
        else:
            name1 = name1.text.strip()
            name = name1
    else:
        name = name.text.strip()
    return name


async def getAmazonProductPrice(product_section):
    price = product_section.find("span", class_="a-price-whole")
    if price is None:
        price = 0.0
    else:
        price = float(price.text.replace(",", ""))
    return price


@app.get("/v1/amazon/{search_query}")
async def say_hello(search_query: str):
    products = []
    links_list = []
    url = f"https://www.amazon.in/s?k={search_query}"
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list:
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                break

    return products


@app.get("/v2/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30):
    products = []
    links_list = []
    updated_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    print(start_index)
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list[start_index:start_index + page_size]:
        updated_list.append(link)

    for link in updated_list:
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                break

    return products


@app.get("/v3/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30):
    products = []
    links_list = []
    updated_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    print(start_index)
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list[start_index:start_index + page_size]:
        updated_list.append(link)

    # Define an async helper function to fetch the product data from the Amazon product page
    async def fetch_product_data(link):
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                print(product)
                break

    # Create a thread pool and submit the fetch_product_data coroutine for each link in updated_list
    with ThreadPoolExecutor(max_workers=23) as executor:
        futures = [executor.submit(asyncio.run, fetch_product_data(link)) for link in updated_list]
        for future in futures:
            future.result()

    return products


@app.get("/v4/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30):
    products = []
    links_list = []
    updated_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    print(start_index)
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list[start_index:start_index + page_size]:
        updated_list.append(link)

    # Define an async helper function to fetch the product data from the Amazon product page
    async def fetch_product_data(link):
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                print(product)
                break

    # Determine the number of links to be processed
    num_links = len(updated_list)

    # Calculate the optimal number of workers based on the number of links to be processed
    num_workers = min(num_links, 23)

    # Create a thread pool and submit the fetch_product_data coroutine for each link in updated_list
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(asyncio.run, fetch_product_data(link)) for link in updated_list]
        for future in futures:
            future.result()

    return products


@app.get("/v5/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30):
    products = []
    links_list = []
    updated_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    print(start_index)
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list:
        updated_list.append(link)

    links_list = []

    url1 = f"https://www.amazon.in/s?k={search_query}&page=2"
    while not links_list:
        response = requests.get(url1)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list:
        updated_list.append(link)

    # Define an async helper function to fetch the product data from the Amazon product page
    async def fetch_product_data(link):
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                print(product)
                break

        # Determine the number of links to be processed

    num_links = len(updated_list)

    # Calculate the optimal number of workers based on the number of links to be processed
    num_workers = min(num_links, 23)

    # Create a thread pool and submit the fetch_product_data coroutine for each link in updated_list
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(asyncio.run, fetch_product_data(link)) for link in updated_list]
        for future in futures:
            future.result()

    return products


import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import asyncio
import requests
from bs4 import BeautifulSoup


@app.get("/v6/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30):
    products = []
    links_list = []
    updated_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    print(start_index)
    while not links_list:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list:
        updated_list.append(link)

    links_list = []

    url1 = f"https://www.amazon.in/s?k={search_query}&page=2"
    while not links_list:
        response = requests.get(url1)
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    for link in links_list:
        updated_list.append(link)

    # Define an async helper function to fetch the product data from the Amazon product page
    async def fetch_product_data(link):
        url = f"https://www.amazon.in{link}"
        while True:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "lxml")
            all_product_section = soup.find("div", id="dp-container")
            if all_product_section:
                center_product_section = all_product_section.find("div", class_="centerColAlign")
                right_product_section = all_product_section.find("div", id="rightCol")
                left_product_section = all_product_section.find("div", id="leftCol")
                name = await getAmazonProductTitleName(center_product_section)
                price = await getAmazonProductPrice(center_product_section)
                rating_star = await getAmazonProductRatingStar(center_product_section)
                rating_count = await getAmazonProductRatingCount(center_product_section)
                description = await getAmazonProductDescription(center_product_section)
                exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
                image = left_product_section.find("ul",
                                                  class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
                images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                          li.find_all('img') if n.get('src') is not None] if image else []
                product = Product(name=name, description=description, ratingStar=rating_star,
                                  ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                                  link=link)
                products.append(product)
                print(product)
                break

        # Determine the number of links to be processed

    num_links = len(updated_list)

    # Calculate the optimal number of workers based on the number of available CPU cores
    num_workers_system = multiprocessing.cpu_count()

    num_workers = min(num_links, num_workers_system)
    print(num_links)
    print(num_workers_system)
    print(num_workers)

    # Create a thread pool and submit the fetch_product_data coroutine for each link in updated_list
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(asyncio.run, fetch_product_data(link)) for link in updated_list]
        for future in futures:
            future.result()

    return products


def callLinkAmazonV4(process_response, updated_list):
    requests_list = [
        grequests.get(f"https://www.amazon.in{link}", hooks={'response': process_response}, kwargs={'link': link}) for
        link in updated_list]
    return requests_list


async def fetch_product_data(session, link):
    # Fetch the product page
    r = await session.get(f"https://www.amazon.in{link}")
    await r.html.arender()

    # Extract product data from the rendered page
    center_product_section = r.html.find("#centerCol")[0]
    right_product_section = r.html.find("#rightCol")[0]
    left_product_section = r.html.find("#leftCol")[0]

    name = center_product_section.find("#productTitle", first=True).text.strip()
    price = center_product_section.find("#priceblock_ourprice, #priceblock_dealprice", first=True).text.strip()
    rating_star = center_product_section.find("span.a-icon-alt", first=True).text.strip().split()[0]
    rating_count = center_product_section.find("#acrCustomerReviewText", first=True).text.strip().split()[0]
    description = center_product_section.find("#productDescription", first=True).text.strip()
    exchange_offer = right_product_section.find(".a-box-group.a-spacing-base", first=True).text.strip()
    images = [img.attrs["src"] for img in left_product_section.find("#altImages img")]

    product = Product(name=name, description=description, ratingStar=rating_star,
                      ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                      link=link)

    return product

async def fetch_product_data_v2(link):
    url = f"https://www.amazon.in{link}"
    while True:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        all_product_section = soup.find("div", id="dp-container")
        if all_product_section:
            center_product_section = all_product_section.find("div", class_="centerColAlign")
            right_product_section = all_product_section.find("div", id="rightCol")
            left_product_section = all_product_section.find("div", id="leftCol")
            name = await getAmazonProductTitleName(center_product_section)
            price = await getAmazonProductPrice(center_product_section)
            rating_star = await getAmazonProductRatingStar(center_product_section)
            rating_count = await getAmazonProductRatingCount(center_product_section)
            description = await getAmazonProductDescription(center_product_section)
            exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
            image = left_product_section.find("ul",
                                              class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
            images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                      li.find_all('img') if n.get('src') is not None] if image else []
            product = Product(name=name, description=description, ratingStar=rating_star,
                              ratingCount=rating_count, price=price, exchange=exchange_offer, image=images,
                              link=link)
            print(product)
            return product

# async def update_redis_cache(redis_url, products):
#     redis = await aioredis.create_redis_pool(redis_url)
#     for product in products:
#         await redis.hmset(product.link, {
#             'name': product.name,
#             'description': product.description,
#             'ratingStar': product.ratingStar,
#             'ratingCount': product.ratingCount,
#             'price': product.price,
#             'exchange': product.exchange,
#             'image': ','.join(product.image),
#         })
#     redis.close()
#     await redis.wait_closed()
#
# @app.post("/v2/amazon/{search_query}/update_cache")
# async def update_amazon_cache(search_query: str, redis_url: str = "redis://default:LzwBDIEMPTPC3WSf29nOuER5itpalbsJ@redis-12457.c93.us-east-1-3.ec2.cloud.redislabs.com:12457"):
#     products = await search_amazon_products(search_query)
#     asyncio.create_task(update_redis_cache(redis_url, products))
#     return {"message": "Cache update initiated in the background."}
#


async def update_redis_cache(redis_url, products):
    # Create a Redis client
    redis_client = redis.Redis.from_url(redis_url)

    # Iterate over each product
    for product in products:
        # Join the image URLs into a comma-separated string
        image_str = ','.join(product.image)

        # Create a dictionary of product data
        product_data = {
            'name': product.name,
            'description': product.description,
            'ratingStar': product.ratingStar,
            'ratingCount': product.ratingCount,
            'price': product.price,
            'exchange': product.exchange,
            'image': image_str,
        }

        # Set the product data as a string value in Redis
        redis_client.set(product.link, str(product_data))


@app.post("/v2/amazon/{search_query}/update_cache")
async def update_amazon_cache(search_query: str,
                              redis_url: str = "redis://default:LzwBDIEMPTPC3WSf29nOuER5itpalbsJ@redis-12457.c93.us-east-1-3.ec2.cloud.redislabs.com:12457"):
    products = await search_amazon_products(search_query)
    await update_redis_cache(redis_url, products)
    return {"message": "Cache update complete."}


import aiohttp
import asyncio
import async_timeout
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import urljoin

from fastapi import FastAPI


async def get_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(10):
            async with session.get(url) as response:
                return await response.text()


async def get_html_v2(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text


async def fetch_product_data_v2(link: str) -> dict:
    url = urljoin('https://www.amazon.in', link)
    html = await get_html_v2(url)
    soup = BeautifulSoup(html, "html.parser")
    all_product_section = soup.find("div", id="dp-container")
    while all_product_section is None:
        # Retry fetching the HTML page up to 3 times
        html = await get_html_v2(url)
        soup = BeautifulSoup(html, "html.parser")
        all_product_section = soup.find("div", id="dp-container")
    if all_product_section:
        center_product_section = all_product_section.find("div", id="centerCol")
        right_product_section = all_product_section.find("div", id="rightCol")
        left_product_section = all_product_section.find("div", id="leftCol")
        left_center_product_section = all_product_section.find("div", id="leftCol")
        name = None
        if left_center_product_section is not None:
            name = await getAmazonProductTitleNameV2(center_product_section, left_center_product_section)
        price = await getAmazonProductPrice(center_product_section)
        rating_star = await getAmazonProductRatingStar(center_product_section)
        rating_count = await getAmazonProductRatingCount(center_product_section)
        description = await getAmazonProductDescription(center_product_section)
        exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
        image = left_product_section.find("ul",
                                          class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
        images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                  li.find_all('img') if n.get('src') is not None] if image else []
        return {'name': name, 'description': description, 'ratingStar': rating_star,
                'ratingCount': rating_count, 'price': price, 'exchange': exchange_offer, 'image': images,
                'link': link}


async def fetch_product_data_v3(link: str) -> dict:
    url = urljoin('https://www.amazon.in', link)
    html = await get_html_v2(url)
    soup = BeautifulSoup(html, "html.parser")
    all_product_section = soup.select_one("#dp-container")
    while all_product_section is None:
        # Retry fetching the HTML page up to 3 times
        html = await get_html_v2(url)
        soup = BeautifulSoup(html, "html.parser")
        all_product_section = soup.select_one("#dp-container")
    if all_product_section:
        center_product_section = all_product_section.select_one(".centerColAlign")
        right_product_section = all_product_section.select_one("#rightCol")
        left_product_section = all_product_section.select_one("#leftCol")
        name = await getAmazonProductTitleName(center_product_section)
        price = await getAmazonProductPrice(center_product_section)
        rating_star = await getAmazonProductRatingStar(center_product_section)
        rating_count = await getAmazonProductRatingCount(center_product_section)
        description = await getAmazonProductDescription(center_product_section)
        exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
        image = left_product_section.select_one(".regularAltImageViewLayout img[src]")
        images = [img["src"] for img in left_product_section.select(".regularImageLayout img[src]")]
        return {
            "name": name,
            "description": description,
            "ratingStar": rating_star,
            "ratingCount": rating_count,
            "price": price,
            "exchange": exchange_offer,
            "image": [image["src"]] + images if image else images,
            "link": link,
        }


async def fetch_product_data(link: str) -> dict:
    url = urljoin('https://www.amazon.in', link)
    html = await get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    all_product_section = soup.find("div", id="dp-container")
    while all_product_section is None:
        # Retry fetching the HTML page up to 3 times
        html = await get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        all_product_section = soup.find("div", id="dp-container")
        if all_product_section:
            center_product_section = all_product_section.find("div", class_="centerColAlign")
            right_product_section = all_product_section.find("div", id="rightCol")
            left_product_section = all_product_section.find("div", id="leftCol")
            name = await getAmazonProductTitleName(center_product_section)
            price = await getAmazonProductPrice(center_product_section)
            rating_star = await getAmazonProductRatingStar(center_product_section)
            rating_count = await getAmazonProductRatingCount(center_product_section)
            description = await getAmazonProductDescription(center_product_section)
            exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
            image = left_product_section.find("ul",
                                              class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
            images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                      li.find_all('img') if n.get('src') is not None] if image else []
            return {'name': name, 'description': description, 'ratingStar': rating_star,
                    'ratingCount': rating_count, 'price': price, 'exchange': exchange_offer, 'image': images,
                    'link': link}


@app.get("/v9/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30) -> List[dict]:
    start_time = time.time()
    products = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    links_list = []
    while not links_list:
        html = await get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    updated_list = links_list[start_index:start_index + page_size]

    # Create a task for each link and run them concurrently using asyncio.wait
    tasks = [fetch_product_data(link) for link in updated_list]
    done, _ = await asyncio.wait(tasks)

    # Retrieve the results of all the completed tasks
    for task in done:
        result = task.result()
        if result is not None:
            products.append(result)
    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    print(f"Total time taken: {total_time_ms} ms")
    return products


@app.get("/v10/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30) -> List[dict]:
    start_time = time.time()
    products = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", class_="a-link-normal s-no-outline")
    links_list = [link.get("href") for link in links]

    # Retry fetching the links up to 3 times until the links_list is populated
    while not links_list:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    updated_list = links_list[start_index:start_index + page_size]

    # Create a task for each link and run them concurrently using asyncio.wait
    tasks = [fetch_product_data_v2(link) for link in updated_list]
    done, _ = await asyncio.wait(tasks)

    # Retrieve the results of all the completed tasks
    for task in done:
        result = task.result()
        if result is not None:
            products.append(result)
    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    print(f"Total time taken: {total_time_ms} ms")
    return products


@app.get("/v11/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30) -> List[dict]:
    start_time = time.time()
    products = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", class_="a-link-normal s-no-outline")
    links_list = [link.get("href") for link in links]

    # Retry fetching the links up to 3 times until the links_list is populated
    while not links_list:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    updated_list = links_list[start_index:start_index + page_size]

    # Create a task for each link and run them concurrently using asyncio.wait
    tasks = [fetch_product_data_v3(link) for link in updated_list]
    done, _ = await asyncio.wait(tasks)

    # Retrieve the results of all the completed tasks
    for task in done:
        result = task.result()
        if result is not None:
            products.append(result)
    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    print(f"Total time taken: {total_time_ms} ms")
    return products


## getlistoflinks



from typing import Optional
import asyncio
import aiohttp
import async_timeout
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

class ProductLink(BaseModel):
    link: str

# define the async function
async def fetch_product_data(link: str) -> dict:
    url = urljoin('https://www.amazon.in', link)
    html = await get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    all_product_section = soup.find("div", id="dp-container")
    while all_product_section is None:
        # Retry fetching the HTML page up to 3 times
        html = await get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        all_product_section = soup.find("div", id="dp-container")

        if all_product_section:
            center_product_section = all_product_section.find("div", class_="centerColAlign")
            right_product_section = all_product_section.find("div", id="rightCol")
            left_product_section = all_product_section.find("div", id="leftCol")
            name = await getAmazonProductTitleName(center_product_section)
            price = await getAmazonProductPrice(center_product_section)
            rating_star = await getAmazonProductRatingStar(center_product_section)
            rating_count = await getAmazonProductRatingCount(center_product_section)
            description = await getAmazonProductDescription(center_product_section)
            exchange_offer = await getAmazonProductExchangeAmount(right_product_section)
            image = left_product_section.find("ul",
                                              class_="a-unordered-list a-nostyle a-button-list a-vertical a-spacing-top-extra-large regularAltImageViewLayout")
            images = [n.get('src') for li in image.findAll("span", class_="a-button-inner") for n in
                      li.find_all('img') if n.get('src') is not None] if image else []
            return {'name': name, 'description': description, 'ratingStar': rating_star,
                    'ratingCount': rating_count, 'price': price, 'exchange': exchange_offer, 'image': images,
                    'link': link}

@app.get("/detail/amazon/{search_query}")
async def search_amazon_products(search_query: str, page: int = 1, page_size: int = 30) -> List[str]:
    start_time = time.time()
    links_list = []
    start_index = (page - 1) * page_size
    url = f"https://www.amazon.in/s?k={search_query}&page={page}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", class_="a-link-normal s-no-outline")
    links_list = [link.get("href") for link in links]

    # Retry fetching the links up to 3 times until the links_list is populated
    while not links_list:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", class_="a-link-normal s-no-outline")
        links_list = [link.get("href") for link in links]

    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    print(f"Total time taken: {total_time_ms} ms")
    return links_list
# define the endpoint
@app.post("/product-data")
async def get_product_data(link: ProductLink):
    data = await fetch_product_data_v2(link.link)
    return data


