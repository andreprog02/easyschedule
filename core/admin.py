from django.contrib import admin
from .models import Empresa, HorarioEspecial

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'telefone', 'email')
    search_fields = ('nome', 'email')

@admin.register(HorarioEspecial)
class HorarioEspecialAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'data', 'abertura', 'fechamento', 'fechado')
    list_filter = ('empresa', 'fechado')