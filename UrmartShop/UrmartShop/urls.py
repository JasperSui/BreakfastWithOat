from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('', views.Index, name="Index"),
    path('api/send-order/', views.SendOrder, name="SendOrder"),
    path('api/delete-order/<int:order_id>', views.DeleteOrder, name="DeleteOrder"),
    path('api/generate-each-shop-order-detail/', views.GenerateEachShopOrderDetail, name="GenerateEachShopOrderDetail"),
    path('api/get-top-three-product-detail-via-email/', views.GetTopThreeProductDetailViaEmail, name='GetTopThreeProductDetailViaEmail'),
    path('api/get-top-three-product-detail-by-ajax/', views.GetTopThreeProductDetailByAjax, name="GetTopThreeProductDetailByAjax"),
    path('admin/', admin.site.urls),
]