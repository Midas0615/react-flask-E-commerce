from app.models import *
from pymongo import MongoClient
from app import webapp
from flask import render_template
from app import mail
import random
import re
from app.scripts.related_items import getRelatedItems


def upsellEmail(order_id):
    order_info = Order(order_id).getOrderInfo()
    client = MongoClient(webapp.config['MONGO_DB'])
    db = client.ostrich
    
    related_items_cursor = db.related_item_ids.find({'_id': order_info['item_id']})
    related_item_ids = [_ for _ in related_items_cursor]
    print related_item_ids
    if not related_item_ids:
        print "here"
        getRelatedItems(int(order_info['item_id']))
        related_items_cursor = db.related_item_ids.find({'_id': order_info['item_id']})
        related_item_ids = [_ for _ in related_items_cursor]
    
    related_item_ids = related_item_ids[0]['item_ids']

    trending_items_cursor = db.trending_item_ids.find()
    trending_item_ids = [_ for _ in trending_items_cursor][0]['item_ids']
    trending_item_ids = pickRandom(trending_item_ids)

    items = getItemDetails(related_item_ids)
    curated_items = getItemDetails(trending_item_ids)

    # TODO fetch random quote
    quote = "So many books, so little time."
    quote_author = "Frank Zappa"

    data = {
            "user": User(order_info['user_id']),
            "items": items[:4], 
            "curated_items": curated_items,
            "quote": quote, 
            "quote_author": quote_author
            }

    Mailer.sendUpsellEmail(data)
    return True
   

def getItemDetails(item_ids):
    items = []
    for item_id in item_ids:
        item = Item(item_id).getObj()
        item["item_name"] = re.sub("\(.*\)","",item["item_name"])
        if item["img_small"]:
            item["img_small"] = webapp.config["S3_HOST"]+item["img_small"]
            items.append(item)
    return items


def pickRandom(iterator):
    K = 4
    result = []
    N = 0

    for item in iterator:
        N += 1
        if len( result ) < K:
            result.append( item )
        else:
            s = int(random.random() * N)
            if s < K:
                result[ s ] = item

    return result
