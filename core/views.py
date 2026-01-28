from django.shortcuts import render, redirect
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
    # Se o usuário já estiver logado, manda pro dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/login.html')

@csrf_protect
def cadastro_usuario(request):
    if request.method == 'POST':
        data = request.POST
        
        # Validar Senhas
        if data['senha'] != data['senha_confirma']:
            messages.error(request, "As senhas não conferem.")
            return render(request, 'core/cadastro_usuario.html')
        
        # Validar se email já existe
        if User.objects.filter(username=data['email']).exists():
            messages.error(request, "Este e-mail já está cadastrado.")
            return render(request, 'core/cadastro_usuario.html')

        try:
            # 1. Cria o Usuário de Login
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['senha'],
                first_name=data['nome_empresa']
            )
            
            # 2. Cria a Empresa vinculada ao Usuário
            Empresa.objects.create(
                dono=user,
                nome=data['nome_empresa'],
                email=data['email'],
                telefone=data['telefone'],
                cpf_cnpj=data['cpf_cnpj'],
                cep=data['cep'],
                endereco=data['endereco'],
                numero=data['numero'],
                complemento=data['complemento'],
                bairro=data['bairro'],
                cidade=data['cidade'],
                estado=data['estado']
            )

            # 3. Loga o usuário e redireciona para o DASHBOARD (Correção aqui)
            login(request, user)
            return redirect('dashboard') 
            
        except Exception as e:
            messages.error(request, f"Erro ao cadastrar: {str(e)}")
            return render(request, 'core/cadastro_usuario.html')

    return render(request, 'core/cadastro_usuario.html')

@login_required
def dashboard(request):
    # Pega a empresa vinculada ao usuário logado
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, "Usuário sem empresa vinculada.")
        return redirect('login')

    return render(request, 'core/dashboard.html', {'empresa': empresa})


@login_required
def config_empresa(request):
    empresa = request.user.empresa
    dias_formatados = [
        ('seg', 'Segunda-feira'), ('ter', 'Terça-feira'), ('qua', 'Quarta-feira'),
        ('qui', 'Quinta-feira'), ('sex', 'Sexta-feira'), ('sab', 'Sábado'), ('dom', 'Domingo')
    ]

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

        # 3. Logo (Upload)
        if request.FILES.get('logo'):
            empresa.logo = request.FILES.get('logo')

        # 4. Lógica dos Horários (Onde a mágica do filtro acontece)
        horarios_dict = {}
        for dia_id, _ in dias_formatados:
            # Verifica se o checkbox "aberto" foi marcado para aquele dia
            is_aberto = request.POST.get(f'aberto_{dia_id}') == 'on'
            horarios_dict[dia_id] = {
                'aberto': is_aberto,
                'inicio': request.POST.get(f'inicio_{dia_id}', '08:00'),
                'fim': request.POST.get(f'fim_{dia_id}', '18:00'),
            }
        
        empresa.horarios_padrao = horarios_dict
        empresa.save()
        
        messages.success(request, "Configurações da empresa atualizadas com sucesso!")
        return redirect('config_empresa')

    return render(request, 'core/config_empresa.html', {
        'empresa': empresa,
        'dias_formatados': dias_formatados
    })

@login_required
def config_empresa(request):
    # Garante que o usuário tem uma empresa criada
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        # Se não tiver, cria uma padrão ou redireciona
        return redirect('dashboard') 

    # Lógica de Salvamento (POST)
    if request.method == 'POST':
        # 1. Dados Básicos
        empresa.nome = request.POST.get('nome')
        empresa.telefone = request.POST.get('telefone')
        empresa.email = request.POST.get('email')
        empresa.cpf_cnpj = request.POST.get('cpf_cnpj')
        
        # 2. Upload de Logo
        if request.FILES.get('logo'):
            empresa.logo = request.FILES.get('logo')

        # 3. Endereço
        empresa.cep = request.POST.get('cep')
        empresa.endereco = request.POST.get('endereco')
        empresa.numero = request.POST.get('numero')
        empresa.bairro = request.POST.get('bairro')
        empresa.cidade = request.POST.get('cidade')
        empresa.estado = request.POST.get('estado')

        # 4. Configuração de Agendamento (NOVO CAMPO)
        try:
            empresa.limite_agendamento_dias = int(request.POST.get('limite_agendamento', 30))
        except ValueError:
            empresa.limite_agendamento_dias = 30

        # 5. Horários de Funcionamento (JSON)
        horarios = {}
        # Mapeamento dos códigos dos dias (seg, ter...)
        codigos_dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
        
        for dia in codigos_dias:
            aberto = request.POST.get(f'aberto_{dia}') == 'on'
            inicio = request.POST.get(f'inicio_{dia}')
            fim = request.POST.get(f'fim_{dia}')
            
            horarios[dia] = {
                'aberto': aberto,
                'inicio': inicio,
                'fim': fim
            }
        
        empresa.horarios_padrao = horarios
        empresa.save()
        
        messages.success(request, "Configurações atualizadas com sucesso!")
        return redirect('config_empresa')

    # Lógica de Exibição (GET) - IMPORTANTE: Esta parte deve estar FORA do 'if POST'
    
    # Prepara a lista de dias para o template
    dias_formatados = DIAS_SEMANA
    
    return render(request, 'core/config_empresa.html', {
        'empresa': empresa,
        'dias_formatados': dias_formatados
    })