from django.contrib import admin
from .models import Categoria, Servico

class ServicoInline(admin.TabularInline):
    model = Servico
    extra = 1

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa')
    list_filter = ('empresa',)
    inlines = [ServicoInline] # Permite criar serviços dentro da tela de categoria

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco', 'tempo_execucao')
    list_filter = ('categoria__empresa',)