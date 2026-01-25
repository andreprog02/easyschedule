from django.db import models
from core.models import Empresa
from services.models import Servico
from professionals.models import Profissional
import uuid

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('confirmado', 'Confirmado'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField()
    
    # Dados do Cliente
    cliente_nome = models.CharField(max_length=100)
    cliente_telefone = models.CharField(max_length=20)
    
    # Controle
    codigo_autenticacao = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmado')
    observacoes = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Impede dois agendamentos EXATAMENTE iguais no banco (segurança extra)
        unique_together = ('profissional', 'data_hora_inicio')
        ordering = ['data_hora_inicio']

    def __str__(self):
        return f"{self.cliente_nome} - {self.data_hora_inicio.strftime('%d/%m %H:%M')}"