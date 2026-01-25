import json
from datetime import datetime, timedelta, time
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.utils.timezone import make_aware, get_current_timezone # IMPORTANTE
from django.db import transaction, models 
from django.contrib.auth.decorators import login_required

from services.models import Categoria, Servico
from professionals.models import Profissional, BloqueioAgenda
from .models import Agendamento
from core.models import Empresa

# 1. Renderiza a Tela do Wizard
@ensure_csrf_cookie
def agendamento_wizard(request):
    empresa = Empresa.objects.first() 
    if not empresa:
        return render(request, 'core/login.html')
        
    categorias = Categoria.objects.filter(empresa=empresa)
    return render(request, 'scheduling/agendamento_wizard.html', {
        'categorias': categorias,
        'empresa': empresa
    })

# 2. API: Retorna Serviços
def get_services(request):
    cat_id = request.GET.get('categoria_id')
    servicos = Servico.objects.filter(categoria_id=cat_id).values('id', 'nome', 'preco', 'tempo_execucao')
    data = [{'id': s['id'], 'nome': s['nome'], 'preco': str(s['preco']), 'tempo': s['tempo_execucao']} for s in servicos]
    return JsonResponse(data, safe=False)

# 3. API: Retorna Profissionais
def get_professionals(request):
    servico_id = request.GET.get('servico_id')
    # Filtra profissionais que realizam o serviço selecionado
    profissionais = Profissional.objects.filter(servicos_realizados__id=servico_id)
    
    data = []
    for p in profissionais:
        data.append({
            'id': p.id,
            'nome': p.nome,
            'especialidade': p.especialidade,
            'foto_url': p.foto.url if p.foto else None,
            'jornada': p.jornada_config  # <-- Essencial para o bloqueio do calendário
        })
    return JsonResponse(data, safe=False)

# 4. API: O Cérebro (Calcula Horários Livres) - CORRIGIDO
def get_slots(request):
    data_str = request.GET.get('data') 
    prof_id = request.GET.get('profissional')
    servico_id = request.GET.get('servico')

    if not all([data_str, prof_id, servico_id]):
        return JsonResponse({'slots': []})

    try:
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        profissional = Profissional.objects.get(id=prof_id)
        servico = Servico.objects.get(id=servico_id)
        empresa = profissional.empresa
        tz = get_current_timezone() # Pega America/Sao_Paulo
    except:
        return JsonResponse({'slots': []})

    dia_semana_map = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    dia_chave = dia_semana_map[data_obj.weekday()]

    config_loja = empresa.horarios_padrao.get(dia_chave, {})
    if not config_loja.get('aberto', False):
        return JsonResponse({'slots': []})

    jornada = profissional.jornada_config.get(dia_chave, {})
    if not jornada.get('entrada') or not jornada.get('saida'):
        return JsonResponse({'slots': []})

    # Busca Agendamentos e Bloqueios
    ocupados = Agendamento.objects.filter(
        profissional=profissional,
        data_hora_inicio__date=data_obj,
        status__in=['confirmado', 'pendente']
    )
    bloqueios = BloqueioAgenda.objects.filter(
        empresa=empresa,
        data_inicio__date__lte=data_obj,
        data_fim__date__gte=data_obj
    ).filter(models.Q(profissional=profissional) | models.Q(profissional__isnull=True))

    # Definimos os limites Aware
    current_time = make_aware(datetime.strptime(f"{data_str} {jornada['entrada']}", '%Y-%m-%d %H:%M'), tz)
    end_dt = make_aware(datetime.strptime(f"{data_str} {jornada['saida']}", '%Y-%m-%d %H:%M'), tz)
    
    slots = []
    tempo_servico = servico.tempo_execucao

    while current_time + timedelta(minutes=tempo_servico) <= end_dt:
        slot_fim = current_time + timedelta(minutes=tempo_servico)
        is_available = True
        
        # A. Checa contra agendamentos existentes (Comparação Aware vs Aware)
        for ag in ocupados:
            if (current_time < ag.data_hora_fim) and (slot_fim > ag.data_hora_inicio):
                is_available = False
                break
        
        # B. Checa contra bloqueios
        if is_available:
            for b in bloqueios:
                if (current_time < b.data_fim) and (slot_fim > b.data_inicio):
                    is_available = False
                    break

        # C. Checa se já passou (se for hoje)
        if is_available and data_obj == timezone.localdate():
            if current_time < timezone.localtime():
                is_available = False

        slots.append({'hora': current_time.strftime('%H:%M'), 'disponivel': is_available})
        current_time += timedelta(minutes=30) 

    return JsonResponse({'slots': slots})

# 5. API: Salvar Agendamento - CORRIGIDO PARA TIMEZONE AWARE
def confirm_booking(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tz = get_current_timezone()
            
            profissional = Profissional.objects.get(id=data['profissional_id'])
            servico = Servico.objects.get(id=data['servico_id'])
            
            # CRIANDO DATA AWARE (Com fuso horário) para o banco entender
            str_inicio = f"{data['data']} {data['hora']}"
            inicio_naive = datetime.strptime(str_inicio, '%Y-%m-%d %H:%M')
            inicio = make_aware(inicio_naive, tz)
            fim = inicio + timedelta(minutes=servico.tempo_execucao)

            with transaction.atomic():
                colisao = Agendamento.objects.select_for_update().filter(
                    profissional=profissional,
                    status__in=['confirmado', 'pendente'],
                    data_hora_inicio__lt=fim,
                    data_hora_fim__gt=inicio
                ).exists()

                if colisao:
                    return JsonResponse({'status': 'error', 'message': 'Horário ocupado!'}, status=409)

                novo = Agendamento.objects.create(
                    empresa=profissional.empresa,
                    profissional=profissional,
                    servico=servico,
                    data_hora_inicio=inicio,
                    data_hora_fim=fim,
                    cliente_nome=data['cliente_nome'],
                    cliente_telefone=data['cliente_telefone'],
                    status='confirmado'
                )

            return JsonResponse({'status': 'success', 'codigo': str(novo.codigo_autenticacao)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def gestao_agendamentos(request):
    agendamentos = Agendamento.objects.filter(
        empresa=request.user.empresa,
        data_hora_inicio__gte=timezone.now()
    ).order_by('data_hora_inicio')
    return render(request, 'scheduling/gestao_agendamentos.html', {'agendamentos': agendamentos})