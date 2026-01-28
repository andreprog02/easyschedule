from django.db import models
from core.models import Empresa

class Categoria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    icone = models.ImageField(upload_to='icones_categorias/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"

class Servico(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='servicos', on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço (R$)")
    tempo_execucao = models.PositiveIntegerField(help_text="Tempo em minutos (ex: 30)")
    descricao = models.TextField(blank=True, null=True)
    icone = models.ImageField(upload_to='icones_servicos/', blank=True, null=True)

    def __str__(self):
        return self.nome