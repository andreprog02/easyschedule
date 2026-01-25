from django.contrib import admin
from .models import Agendamento

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente_nome', 'data_hora_inicio', 'profissional', 'servico', 'status')
    list_filter = ('status', 'data_hora_inicio', 'profissional')
    search_fields = ('cliente_nome', 'cliente_telefone')
    readonly_fields = ('codigo_autenticacao',) # Ninguém pode editar o código gerado