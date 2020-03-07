from main.models import Product
from django.http import JsonResponse
import json
import pdb

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

# 檢查 Product Stock 的 Decorator
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

        # 如果庫存還夠就繼續執行 Function
        else:

            return view_func(request, data, current_product, *args, **kwargs)

    return func_wrapper

# 檢查是否為 AJAX Request 的 Decorator
def ajax_required(view_func):

    def func_wrapper(request, *args, **kwargs):

        if request.is_ajax():

            return view_func(request, *args, **kwargs)
        
        else:

            return JsonResponse({'status': False, 'errmsg': 'Something wrong.'}, status=200)
            
    return func_wrapper