from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .models import Empresa

DIAS_SEMANA = [
    ('seg', 'Segunda-feira'),
    ('ter', 'Terça-feira'),
    ('qua', 'Quarta-feira'),
    ('qui', 'Quinta-feira'),
    ('sex', 'Sexta-feira'),
    ('sab', 'Sábado'),
    ('dom', 'Domingo'),
]

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/login.html')

@csrf_protect
def cadastro_usuario(request):
    if request.method == 'POST':
        data = request.POST
        
        if data['senha'] != data['senha_confirma']:
            messages.error(request, "As senhas não conferem.")
            return render(request, 'core/cadastro_usuario.html')
        
        if User.objects.filter(username=data['email']).exists():
            messages.error(request, "Este e-mail já está cadastrado.")
            return render(request, 'core/cadastro_usuario.html')

        try:
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['senha'],
                first_name=data['nome_empresa']
            )
            
            Empresa.objects.create(
                dono=user,
                nome=data['nome_empresa'],
                email=data['email'],
                telefone=data['telefone'],
                cpf_cnpj=data['cpf_cnpj'],
                cep=data['cep'],
                endereco=data['endereco'],
                numero=data['numero'],
                complemento=data.get('complemento', ''),
                bairro=data['bairro'],
                cidade=data['cidade'],
                estado=data['estado']
            )

            login(request, user)
            return redirect('dashboard') 
            
        except Exception as e:
            messages.error(request, f"Erro ao cadastrar: {str(e)}")
            return render(request, 'core/cadastro_usuario.html')

    return render(request, 'core/cadastro_usuario.html')

@login_required
def dashboard(request):
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, "Usuário sem empresa vinculada.")
        return redirect('login')

    return render(request, 'core/dashboard.html', {'empresa': empresa})

@login_required
def config_empresa(request):
    # Garante que o usuário tem uma empresa
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        # 1. Dados Básicos
        empresa.nome = request.POST.get('nome')
        empresa.telefone = request.POST.get('telefone')
        empresa.email = request.POST.get('email')
        empresa.cpf_cnpj = request.POST.get('cpf_cnpj')
        
        # 2. Endereço
        empresa.cep = request.POST.get('cep')
        empresa.endereco = request.POST.get('endereco')
        empresa.numero = request.POST.get('numero')
        empresa.bairro = request.POST.get('bairro')
        empresa.cidade = request.POST.get('cidade')
        empresa.estado = request.POST.get('estado')

        empresa.template_tema = request.POST.get('template_tema', 'padrao')

        # 3. Logo (Upload)
        if request.FILES.get('logo'):
            empresa.logo = request.FILES.get('logo')

        # 4. Janela de Agendamento
        try:
            empresa.limite_agendamento_dias = int(request.POST.get('limite_agendamento', 30))
        except (ValueError, TypeError):
            empresa.limite_agendamento_dias = 30

        # 5. Lógica dos Horários (JSON)
        horarios_dict = {}
        for dia_id, _ in DIAS_SEMANA:
            is_aberto = request.POST.get(f'aberto_{dia_id}') == 'on'
            horarios_dict[dia_id] = {
                'aberto': is_aberto,
                'inicio': request.POST.get(f'inicio_{dia_id}', '08:00'),
                'fim': request.POST.get(f'fim_{dia_id}', '18:00'),
            }
        empresa.horarios_padrao = horarios_dict

        # 6. Lógica dos Diferenciais
        nomes = request.POST.getlist('dif_nome[]')
        icones = request.POST.getlist('dif_icone[]')
        
        lista_dif = []
        for nome, icone in zip(nomes, icones):
            if nome.strip():
                lista_dif.append({
                    'nome': nome.strip(),
                    'icone': icone.strip() if icone else 'fa-star'
                })
        
        empresa.diferenciais = lista_dif[:8] # Limite de 8 itens
        
        # Salva TUDO no banco de dados
        empresa.save()
        
        messages.success(request, "Configurações da empresa atualizadas com sucesso!")
        return redirect('config_empresa')

    return render(request, 'core/config_empresa.html', {
        'empresa': empresa,
        'dias_formatados': DIAS_SEMANA
    })

@login_required
def config_whatsapp(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        empresa.twilio_sid = request.POST.get('twilio_sid')
        empresa.twilio_token = request.POST.get('twilio_token')
        empresa.twilio_whatsapp_origem = request.POST.get('twilio_whatsapp_origem')
        empresa.msg_confirmacao = request.POST.get('msg_confirmacao')
        empresa.msg_cancelamento = request.POST.get('msg_cancelamento')
        empresa.save()
        messages.success(request, "Configurações de WhatsApp atualizadas!")
        return redirect('config_whatsapp')
    return render(request, 'core/config_whatsapp.html', {'empresa': empresa})