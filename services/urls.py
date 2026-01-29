from django.urls import path
from . import views

urlpatterns = [
    path('gerenciar/', views.config_servicos, name='config_servicos'),
    
    # APIs para o Javascript
    path('api/add_categoria/', views.add_categoria, name='api_add_categoria'),
    path('api/delete_categoria/<int:cat_id>/', views.delete_categoria, name='api_delete_categoria'),

    path('api/edit_categoria/<int:cat_id>/', views.edit_categoria, name='api_edit_categoria'),
    
    path('api/add_service/', views.add_service, name='api_add_service'),
    path('api/edit_service/<int:service_id>/', views.edit_service, name='api_edit_service'),
    path('api/delete_service/<int:service_id>/', views.delete_service, name='api_delete_service'),
]