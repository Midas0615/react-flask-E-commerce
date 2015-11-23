from app import mysql
from app.models import User, Item, Utils, Wallet
import datetime

class Order():
    def __init__(self, order_id):
        self.order_id = order_id

    @staticmethod
    def placeOrder(order_data):
       
        order_fields = ['item_id', 'user_id', 'address_id']
        for key in order_data:
            if key not in order_fields:
                return {'message': 'Required params missing'}
            elif not (order_data[key] and isinstance(order_data[key], int)):
                return {'message': 'Wrong param value'}
            else:
                order_data[key] = int(order_data[key])
        
        payment_mode = order_data['payment_mode'] if 'payment_mode' in order_data else 'cash'
        order_placed = Utils.getCurrentTimestamp()
        order_return = order_data['order_return'] if 'order_return' in order_data else Utils.getDefaultReturnTimestamp()

        #TODO calc total amount
        order_amount = 0 

        #check user validity
        #check order validity

        if payment_mode == 'wallet':
            user = User(user_id, 'user_id')
            if user.wallet_balance < order_amount:
                return {'message': 'Not enough balance in wallet'}
        
        connect = mysql.connect() 
        insert_data_cursor = connect.cursor()
        insert_data_cursor.execute("INSERT INTO orders (user_id, address_id, \
                order_placed, order_return, payment_mode) VALUES(%d, %d, '%s', '%s', '%s')" % \
                (user_id, address_id, order_placed, order_return, payment_mode))
        connect.commit()
        order_id = insert_data_cursor.lastrowid
        insert_data_cursor.close()
        response = {'order_id': order_id}

        order = Order(order_id)
        order.updateInventoryPostOrder(item_ids)

        if payment_mode == 'wallet':
            Wallet.debitTransaction(user.wallet_id, user.user_id, 'order', order_id, order_amount) 

        #TODO call roadrunnr api
        #TODO send user order confirmation notification

        return response 
    

    def updateInventoryPostOrder(self, item_ids):
        #NOTE this part is supported for multiple items in same order. PlaceOrder function isnt
        inventory_ids = self.getInventoryIds(item_ids) 

        #update order_history and clear stock in inventory
        connect = mysql.connect()
        for inventory_item in inventory_ids:
            order_history_cursor = connect.cursor()
            order_history_cursor.execute("INSERT INTO order_history (inventory_id, \
                    order_id) VALUES (%d, %d)" %(inventory_item['inventory_id'], self.order_id))
            connect.commit()
            order_history_cursor.close()


            update_stock_cursor = connect.cursor()
            update_stock_cursor.execute("UPDATE inventory SET in_stock = 0 WHERE \
                    inventory_id = %d" % (inventory_item['inventory_id']))
            connect.commit()
            update_stock_cursor.close()

            

            '''
            #add credits to lender
            #TODO credits based on business logic
            item_credits = 0
            add_credit_cursor = connect.cursor()
            add_credit_cursor.execute("INSERT INTO lender_credits (lender_id, \
                    order_id, inventory_id, credits, redeemed) VALUES (%d, %d, \
                    %d, %d, %d)" %(inventory_item['lender_id'], self.order_id, \
                    inventory_item['inventory_id'], item_credits, 0))
            connect.commit()
            add_credit_cursor.close()
            '''

            #TODO send notification to lender

             

    def getInventoryIds(self, item_ids):
        
        inventory_ids = []
        for item_id in item_ids:
            item_check_cursor = mysql.connect().cursor()
            item_check_cursor.execute("SELECT inventory_id, lender_id FROM inventory \
                    WHERE item_id = %d AND in_stock = 1 ORDER BY date_added" % (item_id))
            inv_items = item_check_cursor.fetchall()
            item_check_cursor.close()

            if inv_items: 
                # check if a lender's item is present,
                # else return the inventory item
                item_selected = list(inv_items[0])
                for item in inv_items:
                    if item[1]:
                        item_selected = item
                        break

                inventory_ids.append({
                    'inventory_id': item_selected[0],
                    'lender_id': item_selected[1]
                    })
            else:
                #TODO change this logic once we stop incremental inventory
                connect = mysql.connect()
                insert_inv_item = connect.cursor()
                insert_inv_item.execute("INSERT INTO inventory (item_id) VALUES ('%s')" %(item_id))
                connect.commit()
                new_inv_id = insert_inv_item.lastrowid
                insert_inv_item.close()

                inventory_ids.append({
                    'inventory_id': new_inv_id,
                    'lender_id': 0
                    })

        return inventory_ids

    def getStatus(self, user_id):
        get_status_cursor = mysql.connect().cursor()
        get_status_cursor.execute("SELECT o.order_status, i.item_id FROM orders o \
                INNER JOIN order_history i \
                ON o.order_id = i.order_id \
                WHERE o.order_id = %d \
                AND o.user_id = %d" 
                % (self.order_id, user_id))

        status = get_status_cursor.fetchone()
        if status:
            status_id = int(status[0])
        else:
            return False

        order_info = {}
        if status_id:
            order_info['status_details'] = Order.getStatusDetails(status_id)
            order_info['item'] = Item(int(status[1])).getObj()

        return order_info

    @staticmethod
    def lendItem(lend_data):

        # TODO get this from incentive slab
        lend_data['delivery_date'] = '2020-02-02 20:20:20'
        conn = mysql.connect()
        set_lend_cursor = conn.cursor()
        
        set_lend_cursor.execute("INSERT INTO inventory (item_id, lender_id, date_added, \
                date_removed, in_stock, pickup_slot, delivery_slot, item_condition) VALUES \
                (%d, %d, '%s', '%s', %d, %d, %d, '%s')" % \
                (int(lend_data['item_id']), \
                 int(lend_data['user_id']), \
                 str(lend_data['pickup_date']), \
                 str(lend_data['delivery_date']), \
                 0, \
                 int(lend_data['pickup_slot']), \
                 int(lend_data['delivery_slot']), \
                 str(lend_data['item_condition']) \
                ))
        conn.commit()
        inv_id = set_lend_cursor.lastrowid
        set_lend_cursor.close()

        return inv_id

    @staticmethod    
    def getTimeSlot():
        time_slot_cursor = mysql.connect().cursor()
        time_slot_cursor.execute("SELECT * FROM time_slots")
        num_slots = time_slot_cursor.rowcount

        time_slots = []
        for slot in range(num_slots):
            time_slots.append(Utils.fetchOneAssoc(time_slot_cursor))

        time_slot_cursor.close()
        return time_slots


    @staticmethod
    def getStatusDetails(status_id):
        status_info = {
                1: {
                    "Status": "Order placed",
                    "Description": "The user has confirmed the order"
                    },
                2: {
                    "Status": "Picked up",
                    "Description": "Order has been picked up for delivery"
                    },
                3: {
                    "Status": "Enroute",
                    "Description": "Order is on the way, with the delivery guy"
                    },
                4: {
                    "Status": "Delivered",
                    "Description": "Order has been delivered to the user"
                    },
                5: {
                    "Status": "Picked up",
                    "Description": "Order has been picked up from the user for return"
                    },
                6: {
                    "Status": "Returned",
                    "Description": "Order has been retured to the inventory"
                    }
                }
        
        if status_id in status_info:
            return status_info[status_id]
        else:
            return False


