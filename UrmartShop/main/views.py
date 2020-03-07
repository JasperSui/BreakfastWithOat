from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from main.models import Product, Shop, Order
from main.decorators import vip_required, ajax_required, stock_pcs_check
from django.db import transaction
from django.db import connection
from django.db.models import Sum
from email.mime.text import MIMEText
from datetime import datetime
from common.email import SendEmailBySendGrid
import json
import pdb
import smtplib

def Index(request):

    # 取得所有 Product, Order
    products = Product.objects.all()
    orders = Order.objects.all()
    
    # 取得 Session 中的 arrival_product_dict，若找不到就預設一個 Dictionary
    arrival_product_dict = request.session.get('arrival_product_dict', dict())

    '''
    初始化變數
        products_is_arrived_list 為型態 [<Product Model Object>, boolean] 的 List
        <Product Model Object>: 為 Product 物件
        boolean               : 用來判斷是否新貨到了
    '''
    products_is_arrived_list = list() 

    # 是否為新用戶
    is_new_user = False
    
    # 如果 Session 中的 arrival_product_dict 為預設 Dictionary
    if arrival_product_dict == dict():

        # 代表為新用戶 (第一次瀏覽該網站)
        is_new_user = True

    for product in products:

        '''
            default_product_status_dict 為 arrival_product_dict 初始化的值
            'out_of_stock'      : 該 Product 庫存是否已為 0
            'product_is_arrived': 該 Product 庫存已從上一次瀏覽網站從 0 變為大於 0
        '''
        default_product_status_dict = {'out_of_stock': False, 'product_is_arrived': False}
        
        # 如果是新用戶就把所有的 arrival_product_dict['product.id'] 初始化
        if is_new_user:

            arrival_product_dict[str(product.id)] = default_product_status_dict

        out_of_stock = arrival_product_dict[str(product.id)]['out_of_stock']
        product_is_arrived = arrival_product_dict[str(product.id)]['product_is_arrived']

        # 如果 product stock_pcs 為 0
        if product.stock_pcs == 0:

            # 將 out_of_stock 設為 True
            arrival_product_dict[str(product.id)] = {'out_of_stock': True, 'product_is_arrived': False}
            
            # 因為目前的 stock_pcs 還是 0，所以不可能有新品到貨
            products_is_arrived_list.append([product, False])

        # 如果 product stock_pcs 不為 0
        else:

            '''
                如果 out_of_stock 已經為 True，那就代表上一次瀏覽的時候庫存已經為 0，
                但現在 Product 庫存又不為 0，代表新品已經到貨了，【而且】product_is_arrived
                【還不是】 True，代表新品到貨的通知【還沒】顯示過，所以將 product_is_arrived 設為 True
            '''
            if out_of_stock and not product_is_arrived:

                arrival_product_dict[str(product.id)] = {'out_of_stock': True, 'product_is_arrived': True}

                products_is_arrived_list.append([product, True])


            # 如果 out_of_stock 已經為 True，那就代表上一次瀏覽的時候該 Product 庫存已經為 0，
            # 但現在 Product stock_pcs 又不為 0，代表新品已經到貨了，【可是】product_is_arrived 
            # 【已經是】 True，代表新品到貨的通知【已經】顯示過， 所以將 arrival_product_dict['product.id'] 初始化，
            # 回到最原始的狀態 (有貨且無任何通知)
            elif out_of_stock and product_is_arrived:

                arrival_product_dict[str(product.id)] = default_product_status_dict

                products_is_arrived_list.append([product, False])

            
            # 其他就代表 上一次的瀏覽該 Product 的庫存還不為 0，所以不用做任何的變動，
            # 並且也不可能出現 out_of_stock 為 False 但 product_is_arrived 為 True 的情況，
            # 所以直接將 arrival_product_dict['product.id'] 初始化
            
            else:
                
                arrival_product_dict[str(product.id)] = default_product_status_dict

                products_is_arrived_list.append([product, False])

    request.session['arrival_product_dict'] = arrival_product_dict

    return render(request, 'main/index.html', locals())

"""
執行順序為 @ajax_required → @vip_required → @stock_pcs_check
先檢查是否為 AJAX Request 後再進行接下來的 VIP 身分及庫存量檢查
"""
@vip_required
@stock_pcs_check
@ajax_required 
def SendOrder(request, data=None, current_product=None, *args, **kwargs):
    
    is_success = False
    
    try:

        # 作 Transaction 保持 Atomicity
        with transaction.atomic():
            
            # 以 Pessimistic 來鎖定 current row
            # 更新該 Product 的 stock_pcs
            product = Product.objects.select_for_update().get(id=current_product.id)

            product.stock_pcs -= data['number']
            product.save()

            # 新增 Order
            if data['customer_id'] in (None, ''):

                data['customer_id'] = 'Admin'

            order = Order(
                            product_id=product.id,
                            customer_id=data['customer_id'],
                            qty=data['number']
                        )
            order.save()

            is_success = True

    except Exception as e:

        Exception('Unexpected error: {}'.format(e))
    
    return JsonResponse({'status': is_success})

@ajax_required 
def DeleteOrder(request, order_id, *args, **kwargs):
    
    is_success = False

    try:

        order = Order.objects.get(id=order_id)
        product = Product.objects.get(id=order.product_id)

        # 作 Transaction 保持 Atomicity
        with transaction.atomic():
            
            # 刪除該 Order
            order.delete()

            # 補回庫存
            product.stock_pcs += order.qty
            product.save()

            is_success = True

    except Order.DoesNotExist:

        return JsonResponse({'status': is_success, 'errmsg': 'Order is not exist.'})

    except Product.DoesNotExist:

        return JsonResponse({'status': is_success, 'errmsg': 'Product is not exist.'})
    
    return JsonResponse({'status': is_success})

def GenerateEachShopOrderDetail(request):
    
    if request.method == "POST":

        # 寄件人
        sender_ac = 'jaspersui06@gmail.com'

        # 收件人
        recipient = json.loads(request.body)['recipient']

        # 目前時間
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 主旨
        subject = '【Urmart Shop 最受用戶歡迎的商品前三名】 %s' % current_time
        
        # 執行 Raw SQL
        cursor = connection.cursor()
        cursor.execute("""
                            SELECT `shop`.`name` AS `shop_name`,
                            SUM(`product`.`price`*`order`.`qty`) AS `total_amount`,
                            SUM(`order`.`qty`) AS `total_qty`,
                            COUNT(1) AS `total_order_qty`
                            FROM `order`
                            RIGHT JOIN `product`
                            ON `order`.`product_id` = `product`.`id`
                            RIGHT JOIN `shop`
                            ON `product`.`shop_id` = `shop`.`id`
                            GROUP BY `shop`.`name`
                         """)
        query_result = cursor.fetchall()
        content = 'Hello,<br><br>以下為各館別截至 ' + current_time  + ' 的訂單詳情：<br><br>'

        # 帶入資料產生 Email 內文
        for row in query_result:

            shop_name = row[0]
            total_amount = int(row[1])
            total_qty = int(row[2])
            total_order_qty = row[3]
            
            content += '商店【%s】的總銷售金額：%d, 總銷售數量：%d, 總訂單數量：%d<br>' % (shop_name, total_amount, total_qty, total_order_qty)
        
        content += '<br>謝謝您的使用！'

        if SendEmailBySendGrid(sender_ac, recipient, subject, content):

            return JsonResponse({'status': True})

    return JsonResponse({'status': False})

def GetTopThreeProductDetailViaEmail(request):

    if request.method == "POST":

        # 寄件人
        sender_ac = 'jaspersui06@gmail.com'

        # 收件人
        recipient = json.loads(request.body)['recipient']

        # 目前時間
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 主旨
        subject = '【Urmart Shop 最受用戶歡迎的商品前三名】 %s' % current_time
        
        # 取得 Grouping 後的 Product 資料
        product_rank_list = Order.objects.values('product_id').annotate(sum_qty=Sum('qty')).order_by('-sum_qty')

        # 帶入資料產生 Email 內文
        counter = 1
        content = 'Hello,<br><br>以下為目前截至 ' + current_time  + ' 的最受用戶歡迎的商品前三名：<br><br>'

        for product in product_rank_list:

            content = content + '第 %d 名的Product ID為: %d, 總商品銷售量為: %d <br>' % (counter, product['product_id'], product['sum_qty'])
            counter += 1

        for i in range(1, 4):
            if i > len(product_rank_list):
                content += '第 %d 名: (從缺)<br>' % i

        content += '<br><br>謝謝您的使用！'

        # Call SendGrid API 來寄信
        if SendEmailBySendGrid(sender_ac, recipient, subject, content):

            return JsonResponse({'status': True})

    return JsonResponse({'status': False})

@ajax_required 
def GetTopThreeProductDetailByAjax(request):

    product_rank_list = Order.objects.values('product_id').annotate(sum_qty=Sum('qty')).order_by('-sum_qty')

    first_product = product_rank_list[0] if len(product_rank_list) > 0 else None
    second_product = product_rank_list[1] if len(product_rank_list) > 1 else None
    third_product = product_rank_list[2] if len(product_rank_list) > 2 else None

    return JsonResponse({'first_product': first_product, 'second_product': second_product, 'third_product': third_product})