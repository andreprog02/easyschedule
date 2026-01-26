import json
from datetime import datetime, timedelta, time
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.utils.timezone import make_aware, get_current_timezone
from django.db import transaction, models 
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from core.models import Empresa, HorarioEspecial
from services.models import Categoria, Servico
from professionals.models import Profissional, BloqueioAgenda
from .models import Agendamento

# ... (Mantenha agendamento_wizard, get_services, get_professionals iguais) ...
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

def get_services(request):
    cat_id = request.GET.get('categoria_id')
    servicos = Servico.objects.filter(categoria_id=cat_id).values('id', 'nome', 'preco', 'tempo_execucao')
    data = [{'id': s['id'], 'nome': s['nome'], 'preco': str(s['preco']), 'tempo': s['tempo_execucao']} for s in servicos]
    return JsonResponse(data, safe=False)

def get_professionals(request):
    servico_id = request.GET.get('servico_id')
    profissionais = Profissional.objects.filter(servicos_realizados__id=servico_id)
    data = []
    for p in profissionais:
        data.append({
            'id': p.id,
            'nome': p.nome,
            'especialidade': p.especialidade,
            'foto_url': p.foto.url if p.foto else None,
            'jornada': p.jornada_config
        })
    return JsonResponse(data, safe=False)


# --- LÓGICA CORRIGIDA DOS HORÁRIOS ---
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
        tz = get_current_timezone()
    except Exception:
        return JsonResponse({'slots': []})

    # 1. Horário da Loja (Empresa)
    horario_especial = HorarioEspecial.objects.filter(empresa=empresa, data=data_obj).first()
    loja_abertura = None
    loja_fechamento = None

    if horario_especial:
        if horario_especial.fechado:
            return JsonResponse({'slots': []})
        loja_abertura = horario_especial.abertura
        loja_fechamento = horario_especial.fechamento
    else:
        dia_semana_map = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
        dia_chave = dia_semana_map[data_obj.weekday()]
        config_loja = empresa.horarios_padrao.get(dia_chave, {})
        
        if not config_loja.get('aberto', False):
            return JsonResponse({'slots': []})
            
        try:
            loja_abertura = datetime.strptime(config_loja['inicio'], '%H:%M').time()
            loja_fechamento = datetime.strptime(config_loja['fim'], '%H:%M').time()
        except:
            return JsonResponse({'slots': []})

    # 2. Jornada do Profissional
    dia_semana_prof = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'][data_obj.weekday()]
    jornada = profissional.jornada_config.get(dia_semana_prof, {})
    
    if not jornada.get('entrada') or not jornada.get('saida'):
        return JsonResponse({'slots': []})

    prof_entrada = datetime.strptime(jornada['entrada'], '%H:%M').time()
    prof_saida = datetime.strptime(jornada['saida'], '%H:%M').time()

    # Intersecção de horários
    inicio_efetivo = max(loja_abertura, prof_entrada)
    fim_efetivo = min(loja_fechamento, prof_saida)

    current_dt = make_aware(datetime.combine(data_obj, inicio_efetivo), tz)
    end_dt = make_aware(datetime.combine(data_obj, fim_efetivo), tz)

    # --- CORREÇÃO SOLICITADA: Forçar alinhamento em :00 ou :30 ---
    # Se o horário calculado for 08:15, avança para 08:30. Se for 08:40, avança para 09:00.
    minute = current_dt.minute
    if minute != 0 and minute != 30:
        if minute < 30:
            current_dt = current_dt.replace(minute=30, second=0, microsecond=0)
        else:
            current_dt = (current_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    # Carrega ocupações
    ocupados = Agendamento.objects.filter(
        profissional=profissional,
        data_hora_inicio__date=data_obj,
        status__in=['confirmado', 'pendente']
    )
    
    bloqueios = BloqueioAgenda.objects.filter(
        empresa=empresa,
        data_inicio__lte=end_dt, 
        data_fim__gte=current_dt
    ).filter(models.Q(profissional=profissional) | models.Q(profissional__isnull=True))

    slots = []
    tempo_servico = servico.tempo_execucao

    # Loop principal (incremento fixo de 30 min)
    while current_dt + timedelta(minutes=tempo_servico) <= end_dt:
        slot_fim = current_dt + timedelta(minutes=tempo_servico)
        is_available = True
        
        # Validações
        for ag in ocupados:
            if (current_dt < ag.data_hora_fim) and (slot_fim > ag.data_hora_inicio):
                is_available = False
                break
        
        if is_available:
            for b in bloqueios:
                if (current_dt < b.data_fim) and (slot_fim > b.data_inicio):
                    is_available = False
                    break

        if is_available and data_obj == timezone.localdate():
            if current_dt < timezone.localtime():
                is_available = False

        slots.append({'hora': current_dt.strftime('%H:%M'), 'disponivel': is_available})
        
        # Incremento fixo de 30 minutos conforme solicitado
        current_dt += timedelta(minutes=30) 

    return JsonResponse({'slots': slots})

def confirm_booking(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tz = get_current_timezone()
            
            profissional = Profissional.objects.get(id=data['profissional_id'])
            servico = Servico.objects.get(id=data['servico_id'])
            
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


# --- FUNÇÕES DE GESTÃO (EDITAR E EXCLUIR) ---

@login_required
def gestao_agendamentos(request):
    agendamentos = Agendamento.objects.filter(
        empresa=request.user.empresa,
        data_hora_inicio__gte=timezone.now() - timedelta(days=1) # Mostra tb o dia anterior por segurança
    ).order_by('data_hora_inicio')
    return render(request, 'scheduling/gestao_agendamentos.html', {'agendamentos': agendamentos})

@login_required
@require_POST
def api_delete_agendamento(request, ag_id):
    agendamento = get_object_or_404(Agendamento, id=ag_id, empresa=request.user.empresa)
    agendamento.delete()
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def api_edit_agendamento(request, ag_id):
    agendamento = get_object_or_404(Agendamento, id=ag_id, empresa=request.user.empresa)
    try:
        data = json.loads(request.body)
        if 'status' in data:
            agendamento.status = data['status']
        if 'cliente_nome' in data:
            agendamento.cliente_nome = data['cliente_nome']
        agendamento.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})