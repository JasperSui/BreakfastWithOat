## 早餐吃麥片/運動喝乳清/UrMart 面試測驗繳交 - 睢洋(suiyang03@gmail.com)

Demo link: [https://jaspersui.xyz/](https://jaspersui.xyz/)

此次測驗撰寫功能部分共耗時約 6 小時，架設 Docker 部分第一次使用耗時 4 小時。

下面會將題目搭配圖片解說，方便主管審核，非常感謝您撥冗查閱！

## 開發環境

```
// UrmartShop\requirements.txt

Django==2.2.5
mysqlclient==1.4.6
uWSGI==2.0.18
django-mysql==3.3.0
```

※ 若是以本地環境想要執行此專案，可以將 SQL 檔 Import 至 MySQL資料庫

SQL 檔路徑: ```UrmartShop\Dump20200307.sql```

預設的 Django port 為 8000，直接執行 python manage.py runserver 即可

## 測驗需求

#### 1. 依據提供的資料(商品資料)建立一Django專案

   (a) 畫面呈現
   
   ![image](https://i.imgur.com/O5s6CKu.jpg)

我是以 Bootstrap 4 + SweetAlert 2來完成前端畫面的，

搭配 Ajax 來完成下訂單、刪除訂單、取得前三名產品……等等功能實作。

```Html 路徑: UrmartShop\templates\index.html```
   

   (b) 請設計以下API功能

* #### 加入訂單,訂單成立需檢查是否符合vip身份,並確認商品庫存數量(身份和庫存檢查限用decorator實作)
 
  加入訂單以接收前端 AJAX Request 來實作，依照需求作了三個裝飾器，
  
  這三個裝飾器分別為 `@ajax_required`, `@stock_pcs_check`, `@vip_required`
  
  `@ajax_required`  : 檢查該 Request 是否為 Ajax
  
  ```python
    #main\decorators.py
    #Line 68
    #檢查是否為 AJAX Request 的 Decorator
    def ajax_required(view_func):

        def func_wrapper(request, *args, **kwargs):

            if request.is_ajax():

                return view_func(request, *args, **kwargs)

            else:

                return JsonResponse({'status': False, 'errmsg': 'Something wrong.'}, status=200)

        return func_wrapper
  ```
  <br>
  
  `@stock_pcs_check`: 檢查該 Request 內的 Product 庫存是否足夠
  
   ```python
    #main\decorators.py
    #Line 39
    #檢查 Product Stock 的 Decorator
    def stock_pcs_check(view_func):

        def func_wrapper(request, *args, **kwargs):

            # 讀取 AJAX POST 過來的 DATA
            data = json.loads(request.body)

            # 取得目前 product_id 的 <Product Model Object>
            current_product = Product.objects.get(id=data['product_id'])

            # 如果該會員要買的數量大於庫存
            if data['number'] > current_product.stock_pcs:

                # 回傳失敗 JSON
                return JsonResponse({'status': False, 'errmsg': 'Out of stock.'}, status=200)

            # 如果該會員要買的數量為負數
            if data['number'] <= 0:

                # 回傳失敗 JSON
                return JsonResponse({'status': False, 'errmsg': 'Please enter positive quantity.'})

            # 如果庫存還夠就繼續執行 Function
            else:

                return view_func(request, data, current_product, *args, **kwargs)

        return func_wrapper
  ```
  <br>
  
  `@vip_required`: 檢查該 Request 內的 VIP 是否為 True
  
  ```python
    #main\decorators.py
    #Line 7
    # 檢查 VIP 身分的 Decorator
    def vip_required(view_func):

        def func_wrapper(request, *args, **kwargs):

            # 讀取 AJAX POST 過來的 DATA
            data = json.loads(request.body)

            # 取得目前 product_id 的 <Product Model Object>
            current_product = Product.objects.get(id=data['product_id'])

            # 如果該 product 需要 VIP 身分才能購買
            if current_product.vip:

                # 又如果該會員沒有 VIP 身分
                if not data['vip']:

                    # 回傳失敗 JSON
                    return JsonResponse({'status': False, 'errmsg': 'Not vip.'}, status=200)

                # 如果會員有 VIP 身分就繼續執行 Function
                else:

                    return view_func(request, data, current_product, *args, **kwargs)

            # 如果該 product 不需要 VIP 身分就能購買，就不檢查
            else:

                return view_func(request, data, current_product, *args, **kwargs)

        return func_wrapper
  ```
  
  以下為【加入訂單】功能實作的 Code：
  
  ```python
  #main\views.py
  #Line 115
  
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
  
              if data['number'] <= 0 or data['number'] > product.stock_pcs:

                  return JsonResponse({'status': is_success, 'errmsg': 'Something wrong.'})

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
  ```
 
* #### 刪除訂單

  以下為【刪除訂單】功能實作的 Code：
  
  ```python
    #main/views.py
    #Line 152
    
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
  ```

* #### 加入訂單時,若小於可購買量,前端需提示貨源不足 / 刪除訂單,庫存從0變回有值則提示商品到貨 

  #### 【加入訂單時,若小於可購買量,前端需提示貨源不足】

  `@stock_pcs_check` 裝飾器裡面有判斷訂單購買量小於庫存時，會傳回對應的 JSON 給前端判斷
  
  ```python
  # 如果該會員要買的數量大於庫存
  if data['number'] > current_product.stock_pcs:

      # 回傳失敗 JSON
      return JsonResponse({'status': False, 'errmsg': 'Out of stock.'}, status=200)
  ```
  前端收到後會再用 SweetAlert 彈出錯誤訊息（如下圖）。
  
  ![image](https://i.imgur.com/sM7bBv1.jpg)
  <br>
  #### 【刪除訂單,庫存從0變回有值則提示商品到貨 】
  
  這邊主要是用後端搭配 Session 來判斷並新增 Product 狀態，
  
  前端只是根據資料來輔助顯示 Product 是否為新品到貨，
  
  簡易流程圖如下（可對應流程圖後的成果圖）：
  
  ![image](https://i.imgur.com/GcHttRI.jpg)<br>
  ![image](https://i.imgur.com/rLQ3wF1.jpg)
  
  **（圖1）**
  ![image](https://i.imgur.com/KRRgNt1.jpg)
  
  **（圖2）**
  ![image](https://i.imgur.com/zm4J4mx.jpg)
  
  **（圖3）**
  ![image](https://i.imgur.com/75ly2w5.jpg)
  
  而狀態判斷在 `main/views.py` 的 Index(request) 中實作：
  
  ```python
  #main/views.py
  #Line 16
  
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

              '''
                  如果 out_of_stock 已經為 True，那就代表上一次瀏覽的時候該 Product 庫存已經為 0，
                  但現在 Product stock_pcs 又不為 0，代表新品已經到貨了，【可是】product_is_arrived 
                  【已經是】 True，代表新品到貨的通知【已經】顯示過， 所以將 arrival_product_dict['product.id'] 初始化，
                  回到最原始的狀態 (有貨且無任何通知)
              '''
              elif out_of_stock and product_is_arrived:

                  arrival_product_dict[str(product.id)] = default_product_status_dict

                  products_is_arrived_list.append([product, False])
  
              '''
                  其他就代表 上一次的瀏覽該 Product 的庫存還不為 0，所以不用做任何的變動，
                  並且也不可能出現 out_of_stock 為 False 但 product_is_arrived 為 True 的情況，
                  所以直接將 arrival_product_dict['product.id'] 初始化
              '''
              else:
                
                  arrival_product_dict[str(product.id)] = default_product_status_dict

                  products_is_arrived_list.append([product, False])

      request.session['arrival_product_dict'] = arrival_product_dict

      return render(request, 'main/index.html', locals())

  ```
  

* #### 請設計一排程,根據訂單記錄算出各個館別的1.總銷售金額 2.總銷售數量 3.總訂單數量 

  這邊我利用串接 SendGrid API 來寄信通知指定的 Email 收件人，
  
  發送 POST 到接口 `api/generate-each-shop-order-detail/` 即可寄信。
  
  ![image](https://i.imgur.com/mekiUnZ.jpg)
  
  
  ![image](https://i.imgur.com/mHu4ND7.jpg)
  
  
  實作如下：
  
  ```python
  #main/views.py
  #Line 183
  
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
  
  ```


* #### 根據訂單記錄計算出最受用戶歡迎的商品前三名(根據商品銷售量)

  這邊我實作出兩個方法：
  
  1.    Call API 寄出 Email
  2.    前端按下 Button 後 AJAX 更新表格

  **(1) Call API 寄出 Email**
  
  發送 POST 到接口 `api/get-top-three-product-detail-via-email/` 即可寄信。
  
  ![image](https://i.imgur.com/YW3WhPq.jpg)
  
  ![image](https://i.imgur.com/oqkcJmn.jpg)
  
  ```python
  #main/views.py
  #Line 234
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

        # 只取前三個
        product_rank_list = product_rank_list[0:3]

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
  ```
  
  **(2) 前端按下 Button 後 AJAX 更新表格**
  
  ![image](https://i.imgur.com/z7zFNTI.jpg)
  
  ```python
  #main/views.py
  #Line 279
  
  @ajax_required 
  def GetTopThreeProductDetailByAjax(request):

      # 取得 Grouping 後的 Product 資料
      product_rank_list = Order.objects.values('product_id').annotate(sum_qty=Sum('qty')).order_by('-sum_qty')

      # 只取前三個
      product_rank_list = product_rank_list[0:3]

      first_product = product_rank_list[0] if len(product_rank_list) > 0 else None
      second_product = product_rank_list[1] if len(product_rank_list) > 1 else None
      third_product = product_rank_list[2] if len(product_rank_list) > 2 else None

    return JsonResponse({'first_product': first_product, 'second_product': second_product, 'third_product': third_product})
  ```
  
  ```javascript
  // templates/main/index.html
  // Line 237
  
  $("#btn-get-top-three").click(function(){
        $.ajax({
            url: "/api/get-top-three-product-detail-by-ajax/",
            method: "POST",
            data: {},
            success: function(data) {
                var first_product = data['first_product'];
                var second_product = data['second_product'];
                var third_product = data['third_product'];
                if (first_product == null){
                    first_product = {};
                    first_product['product_id'] = "(從缺)";
                    first_product['sum_qty'] = "(從缺)";
                }
                if (second_product == null){
                    second_product = {};
                    second_product['product_id'] = "(從缺)";
                    second_product['sum_qty'] = "(從缺)";
                }
                if (third_product == null){
                    third_product = {};
                    third_product['product_id'] = "(從缺)";
                    third_product['sum_qty'] = "(從缺)";
                }

                var temp_new_table = String.format(
                    `
                    <table class="table table-striped">
                        <thead>
                        <tr>
                            <th scope="col">Rank</th>
                            <th scope="col">Product ID</th>
                            <th scope="col">Total Qty</th>
                        </tr>
                        </thead>
                        <tbody>
                        <tr>
                            <th scope="row">1st</th>
                            <td>{0}</td>
                            <td>{1}</td>
                        </tr>
                        <tr>
                            <th scope="row">2nd</th>
                            <td>{2}</td>
                            <td>{3}</td>
                        </tr>
                        <tr>
                            <th scope="row">3rd</th>
                            <td>{4}</td>
                            <td>{5}</td>
                        </tr>
                        </tbody>
                    </table>
                    `
                    , first_product['product_id'], first_product['sum_qty']
                    , second_product['product_id'], second_product['sum_qty']
                    , third_product['product_id'], third_product['sum_qty']
                )
                $("#top-three-div").append(temp_new_table);
                $("#btn-get-top-three").attr('disabled', 'true');
                console.log(data);

            }
        });
    }); 
  ```
   
   (c) 資料說明 (Model):
   
   ```python
   #main/models.py
   #Line 114
   
   class Order(models.Model):
       product = models.ForeignKey('Product', models.DO_NOTHING) #Foreign Key <Product Model Object> 
       customer_id = models.CharField(max_length=255) 
       qty = models.IntegerField()

       class Meta:
           managed = False
           db_table = 'order'


   class Product(models.Model):
       shop = models.ForeignKey('Shop', models.DO_NOTHING) #Foreign Key <Shop Model Object> 
       stock_pcs = models.IntegerField()
       price = models.IntegerField()
       vip = Bit1BooleanField(default=True)

       class Meta:
           managed = False
           db_table = 'product'


   class Shop(models.Model):
       name = models.CharField(max_length=50)

       class Meta:
           managed = False
           db_table = 'shop'
   ```
   
   (d) Bonus:
   
   #### 1. 使用 Docker 架設 (Done)
   
   使用 Docker 部署在 DigitalOcean 的 Ubuntu Droplet 上，
   
   執行指令:
   
   `docker-compose build`
   `docker-compose up -d`
   
   加上修改 `main/settings.py` 內的 `Database['HOST']` 即可部署完成。
   
   #### 2. 部署至雲端服務 (Done)
   
   （同上，暫略）
