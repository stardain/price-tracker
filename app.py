"""
gives all the necessary information about the product you're tracking
"""

import json
from fastapi import FastAPI, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from bs4 import BeautifulSoup as bs
import requests
from pymongo.mongo_client import MongoClient

# pylint: disable=missing-timeout, bare-except, broad-exception-raised, broad-exception-caught, unused-variable, line-too-long, trailing-whitespace, invalid-name

#===========================================================================================================

app = FastAPI()

user = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

class Item:
    """
    товарный класс
    """
    def __init__(self, name, brand, price, link, avail):
        self.name = name
        self.brand = brand
        self.price = price
        self.link = link
        self.avail = avail

# COMPLETE: main screen
@app.get("/")
def root():
    """
    just a root
    """
    return FileResponse("index.html")

# ALMOST COMPLETE: create a new tracked entry
@app.post("/")
def new_track(raw = Body(), option=0):
    """
    1. takes a goldapple.com link and bottle size in ml (an option available in the store)
    2. option_check ensures the choosen bottle size exists (if not entered, basic size is 0, which returns the smallest or, if so, the only available option)
    3. get_name returns lowercase name and brand
    4. get_price_and_avail returns the price for choosen bottle size and its availability at the moment
    """

    link = raw["info"]
    option = raw["size"]

    # parser
    responce = requests.get(link, headers=user)
    soup = bs(responce.text, "lxml")
    head_insides = soup.find("html").find("head").contents
    correct_script = head_insides[-1]
    product_card = str(correct_script).split(';</script')[-2].split("\'productCard\']=")[-1]
    card = json.loads(product_card) # < essential information

    # reusable in two functions
    sizes_count = len(card['data']['variants'])

    def get_name(card):

        brand = card['data']['brand']
        name = card['data']['productType']
        return name.strip(), brand

    def option_check(option):

        allowed_sizes = [card['data']['variants'][count]['attributesValue']['units'] for count in range(sizes_count)]
        how_much = [count for count in range(len(allowed_sizes))]
        final = dict(map(lambda i, j : (i, j), allowed_sizes, how_much))

        if option != 0 and str(option) not in allowed_sizes:
            raise Exception('No such bottle size')
        
        return final[str(option)]

    option_choice = option_check(option)

    def get_price_and_avail(card):

        if option == 0:
            try:
                price = card['data']['variants'][-1]['price']['discount']['amount']
            except:
                price = card['data']['variants'][-1]['price']['loyalty']['amount']
            finally:
                avail = card['data']['variants'][-1]['inStock']
        else:
            for size in range(sizes_count):
                if card['data']['variants'][option_choice]['attributesValue']['units'] == str(option): 
                    try:
                        price = card['data']['variants'][option_choice]['price']['loyalty']['amount']
                    except:
                        price = card['data']['variants'][option_choice]['price']['discount']['amount']
                    finally:
                        avail = card['data']['variants'][option_choice]['inStock']
        
        return price, avail

    name, brand = get_name(card)
    price, avail = get_price_and_avail(card)

    #===========================================================================================================

    uri = "mongodb+srv://stardain:vn6iFbtaBwHpTUFj@pricetracker.jikbguc.mongodb.net/?appName=pricetracker"
    client = MongoClient(uri)

    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    # pricetracker cluster - trial db - products collection

    db = client["trial"]
    col = db["products"]

    col.insert_one({"name": name.lower(), "brand": brand.lower(), "price": price, "link": link, "avail": avail})

    return {"url": f"ok done! {name.lower()} от {brand.lower()} за {price} хихихих"}

@app.get("/api")
def get_old_tracks():

    uri = "mongodb+srv://stardain:vn6iFbtaBwHpTUFj@pricetracker.jikbguc.mongodb.net/?appName=pricetracker"
    client = MongoClient(uri)

    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    # pricetracker cluster - trial db - products collection

    db = client["trial"]
    col = db["products"]

    all_items = [Item(name=i['name'], brand=i['brand'], price=i['price'], link=i['link'], avail=i['avail']) for i in col.find()]

    return all_items


app.mount("/", StaticFiles(directory="/", html=True))

#===========================================================================================================
