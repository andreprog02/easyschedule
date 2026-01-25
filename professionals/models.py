from django.db import models
from core.models import Empresa
from services.models import Servico

class Profissional(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='profissionais/', blank=True, null=True)
    especialidade = models.CharField(max_length=100, blank=True)
    
    # Quais serviços esse profissional realiza?
    servicos_realizados = models.ManyToManyField(Servico, related_name='profissionais', blank=True)
    
    # Configuração de Jornada Semanal (JSON)
    # Ex: {'seg': {'entrada': '09:00', 'saida': '18:00', 'almoco_ini': '12:00', 'almoco_fim': '13:00'}}
    jornada_config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.nome

class BloqueioAgenda(models.Model):
    """Gerencia Folgas Individuais e Coletivas"""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    # Se profissional for NULL, é uma folga COLETIVA (todos param)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, null=True, blank=True)
    
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    motivo = models.CharField(max_length=200, blank=True)
    
    def is_coletiva(self):
        return self.profissional is None