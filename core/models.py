from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid

class Empresa(models.Model):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa')
    nome = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(unique=True, help_text="Identificador único para a URL (ex: barbearia-do-ze)")
    
    # Configurações Visuais e de Contato
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    telefone = models.CharField(max_length=20, help_text="Formato: (24) 9 9216-4962")
    email = models.EmailField()
    cpf_cnpj = models.CharField(max_length=20, verbose_name="CPF/CNPJ")
    
    cor_tema = models.CharField(max_length=7, default="#333333", help_text="Cor principal do agendamento (Hex)")

    # Horários Padrão da Loja (JSON facilita salvar estruturas complexas)
    # Ex: {'seg': {'aberto': True, 'inicio': '08:00', 'fim': '18:00'}, ...}
    horarios_padrao = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.nome

class HorarioEspecial(models.Model):
    """Para dias específicos (ex: Sábado véspera de Natal abre até mais tarde)"""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    data = models.DateField()
    abertura = models.TimeField()
    fechamento = models.TimeField()
    fechado = models.BooleanField(default=False, help_text="Se marcado, a loja não abre neste dia")

    def __str__(self):
        return f"{self.data} - {self.empresa.nome}"
    
class Empresa(models.Model):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa')
    nome = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(unique=True, blank=True)
    
    # Contato e Identificação
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField()
    cpf_cnpj = models.CharField(max_length=20, verbose_name="CPF/CNPJ")
    
    # Endereço Completo
    cep = models.CharField(max_length=10, blank=True)
    endereco = models.CharField(max_length=255, verbose_name="Logradouro", blank=True)
    numero = models.CharField(max_length=20, verbose_name="Número", blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, verbose_name="UF", blank=True)

    # Configurações do Sistema
    cor_tema = models.CharField(max_length=7, default="#333333")
    horarios_padrao = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        # Gera o slug automaticamente se não existir (ex: barbearia-top -> barbearia-top-a1b2)
        if not self.slug:
            uid = str(uuid.uuid4())[:4]
            self.slug = slugify(f"{self.nome}-{uid}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

class HorarioEspecial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    data = models.DateField()
    abertura = models.TimeField()
    fechamento = models.TimeField()
    fechado = models.BooleanField(default=False)