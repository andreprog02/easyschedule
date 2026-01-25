from django.contrib import admin
from .models import Profissional, BloqueioAgenda

@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'especialidade')
    filter_horizontal = ('servicos_realizados',) # Interface bonita para selecionar muitos serviços

@admin.register(BloqueioAgenda)
class BloqueioAgendaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'profissional', 'data_inicio', 'motivo')
    list_filter = ('empresa', 'profissional')