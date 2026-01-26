from django.urls import path
from . import views

urlpatterns = [
    path('gerenciar/', views.gestao_equipe, name='gestao_equipe'),
    path('folgas/', views.gestao_folgas, name='gestao_folgas'),
    
    # APIs
    path('api/get/<int:prof_id>/', views.api_get_profissional, name='api_get_profissional'),
    path('api/add/', views.api_add_profissional, name='api_add_profissional'),
    path('api/edit/<int:prof_id>/', views.api_edit_profissional, name='api_edit_profissional'),
    path('api/add-folga/', views.api_add_folga, name='api_add_folga'),
    path('api/delete/<int:prof_id>/', views.api_delete_profissional, name='api_delete_profissional'),
]