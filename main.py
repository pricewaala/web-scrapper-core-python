import redis
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI

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
