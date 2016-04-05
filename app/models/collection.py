from app import mysql
from app.models import Prototype, Utils, Search
import json

class Collection(Prototype):
    def __init__(self, collection_id):
        self.getData(collection_id)
    
    def getData(self, collection_id):
        cursor = mysql.connect().cursor()
        cursor.execute("""SELECT c.*, 
            (select group_concat(ci.item_id separator ',') from collections_items ci 
            where ci.collection_id = c.collection_id) as item_ids,
            (select group_concat(concat(cm.meta_key,":",cm.meta_value) separator '&') from collections_metadata cm 
            where cm.collection_id = c.collection_id) as metadata
            FROM collections c WHERE c.collection_id = %s""", (collection_id,))
        self.data = Utils.fetchOneAssoc(cursor)

        if self.data['metadata']:
            collections_metadata_raw = self.data['metadata']
            self.data['metadata'] = {}
            for props in collections_metadata_raw.split('&'):
                props_formatted = props.split(':')
                self.data['metadata'][props_formatted[0]] = props_formatted[1]
        if not self.data:
            self.data = {}
  
    def getExpandedObj(self):
        collection_object = self.getObj()
        if collection_object['item_ids']:
            collection_object['item_ids'] = [int(_) for _ in collection_object['item_ids'].split(',')]
            collection_object['items'] = Search().getById(collection_object['item_ids']) 
        else:
            collection_object['items'] = []
        return collection_object

    @staticmethod
    def getByCategory():
        cursor = mysql.connect().cursor()
        cursor.execute("""SELECT cc.*, c.collection_id
            FROM collections_category cc INNER JOIN collections c 
            ON c.category_id = cc.category_id""")
        collections_category = {}
        for coll in cursor.fetchall():
            if coll[1] not in collections_category:
                collections_category[coll[1]] = []
            collections_category[coll[1]].append(Collection(int(coll[2])).getExpandedObj())
        return collections_category

    @staticmethod
    def getPreview():
        cursor = mysql.connect().cursor()
        cursor.execute("""SELECT collection_id, name FROM collections WHERE active = 1""")
        num_rows = cursor.rowcount
        collections = []
        for i in range(num_rows):
            collections.append(Utils.fetchOneAssoc(cursor))
        return collections

    @staticmethod
    def getByItemId(item_id):
        cursor = mysql.connect().cursor()
        cursor.execute("""SELECT c.price FROM collections c INNER JOIN 
            collections_items ci ON ci.collection_id = c.collection_id
            WHERE ci.item_id = %s""", (item_id,))
        rental_price = cursor.fetchone()
        if rental_price:
            rental_price = int(rental_price[0])
        return rental_price 

    @staticmethod
    def saveCollectionData(data):
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("""UPDATE collections SET name = %s, description = %s,
            price = %s, return_days = %s, date_edited = CURRENT_TIMESTAMP
            WHERE collection_id = %s""", (
                data['name'],
                data['description'],
                data['price'],
                data['return_days'],
                data['collection_id'])) 
        conn.commit()

        cursor.execute("""DELETE FROM collections_metadata WHERE collection_id = %s""",
                (data['collection_id'],))
        conn.commit()

        metadata_pairs = []
        for meta in data['metadata'].split(";"):
            key, value = meta.split(":")
            metadata_pairs.append(tuple([data['collection_id'], key, value]))
        cursor.executemany("""INSERT INTO collections_metadata (collection_id, meta_key, meta_value) 
                VALUES (%s, %s, %s)""", metadata_pairs)
        conn.commit()

        item_order = []
        item_ids = []
        for item in data['items'].split(";"):
            key, value = item.split(":")
            item_ids.append(key)
            item_order.append(tuple([value, data['collection_id'], key]))
        cursor.executemany("""UPDATE collections_items SET sort_order = %s, 
            date_edited = CURRENT_TIMESTAMP WHERE collection_id = %s AND item_id = %s""",
            item_order)
        conn.commit()
        
        format_chars = ",".join(["%s"] * len(item_ids))
        cursor.execute("""DELETE FROM collections_items 
            WHERE collection_id = %s AND item_id NOT IN ("""+format_chars+""")""", 
            (tuple([data['collection_id']]) + tuple(item_ids)))
        conn.commit()
        return True

    @staticmethod
    def removeCollection(collection_id):
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("""UPDATE collections SET active = 0, date_edited = CURRENT_TIMESTAMP
            WHERE collection_id = %s""", (collection_id))
        conn.commit()
        return True
            
