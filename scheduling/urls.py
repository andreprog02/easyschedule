from django.urls import path
from . import views

urlpatterns = [
    # --- APIs Públicas (Mantidas no topo para não confundir com o slug) ---
    path('api/get_services/', views.get_services, name='api_get_services'),
    path('api/get_professionals/', views.get_professionals, name='api_get_professionals'),
    path('api/get_slots/', views.get_slots, name='api_get_slots'),
    path('api/confirm_booking/', views.confirm_booking, name='api_confirm_booking'),
    
    # --- Área Administrativa ---
    path('gestao/', views.gestao_agendamentos, name='gestao_agendamentos'),
    path('gestao/api/delete/<int:ag_id>/', views.api_delete_agendamento, name='api_delete_agendamento'),
    path('gestao/api/edit/<int:ag_id>/', views.api_edit_agendamento, name='api_edit_agendamento'),

    # --- PÁGINA DE AGENDAMENTO DA EMPRESA (O Slug identifica qual empresa é) ---
    # Antes era: path('', views.agendamento_wizard, ...)
    path('<slug:empresa_slug>/', views.agendamento_wizard, name='agendamento_publico'),
]