from django.urls import path
from . import views

urlpatterns = [
    # Página Principal (Wizard)
    path('', views.agendamento_wizard, name='agendamento_home'),

    # APIs Públicas (Wizard)
    path('api/get_services/', views.get_services, name='api_get_services'),
    path('api/get_professionals/', views.get_professionals, name='api_get_professionals'),
    path('api/get_slots/', views.get_slots, name='api_get_slots'),
    path('api/confirm_booking/', views.confirm_booking, name='api_confirm_booking'),
    
    # Área Administrativa
    path('gestao/', views.gestao_agendamentos, name='gestao_agendamentos'),
    
    # NOVAS ROTAS (Correção para Edição e Exclusão)
    path('gestao/api/delete/<int:ag_id>/', views.api_delete_agendamento, name='api_delete_agendamento'),
    path('gestao/api/edit/<int:ag_id>/', views.api_edit_agendamento, name='api_edit_agendamento'),
]