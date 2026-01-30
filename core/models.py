from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid

class Empresa(models.Model):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa')
    nome = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField()
    cpf_cnpj = models.CharField(max_length=20, verbose_name="CPF/CNPJ")
    cep = models.CharField(max_length=10, blank=True)
    endereco = models.CharField(max_length=255, verbose_name="Logradouro", blank=True)
    numero = models.CharField(max_length=20, verbose_name="Número", blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, verbose_name="UF", blank=True)
    cor_tema = models.CharField(max_length=7, default="#3b82f6")
    horarios_padrao = models.JSONField(default=dict, blank=True)
    diferenciais = models.JSONField(default=list, blank=True)
    
    # Novo campo adicionado corretamente
    limite_agendamento_dias = models.PositiveIntegerField(default=30, verbose_name="Janela de Agendamento (dias)")

    # Adicione este campo:
    TEMAS_CHOICES = [
        ('padrao', 'Padrão (Azul/Clean)'),
        ('feminino', 'Feminino (Bordô/Pastel)'),
        ('barber_dark', 'Barbearia (Dark/Gold)'), # <--- ADICIONE ISSO
    ]
    template_tema = models.CharField(max_length=20, choices=TEMAS_CHOICES, default='padrao')


    # Credenciais Twilio
    twilio_sid = models.CharField(max_length=100, blank=True, null=True)
    twilio_token = models.CharField(max_length=100, blank=True, null=True)
    twilio_whatsapp_origem = models.CharField(max_length=30, blank=True, null=True, help_text="Ex: whatsapp:+14155238886")

    # Mensagens Personalizadas
    msg_confirmacao = models.TextField(
        default="Olá {cliente}, seu horário na {empresa} foi confirmado: {data} às {hora}. Profissional: {profissional}."
    )
    msg_cancelamento = models.TextField(
        default="Olá {cliente}, infelizmente o seu agendamento na {empresa} para o dia {data} às {hora} foi cancelado."
    )

    def save(self, *args, **kwargs):
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


    