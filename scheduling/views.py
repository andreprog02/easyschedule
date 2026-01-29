import json
from datetime import datetime, timedelta
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

# --- WIZARD E APIS DE CONSULTA ---

@ensure_csrf_cookie
def agendamento_wizard(request):
    # Mantive sua lógica de pegar a primeira empresa
    empresa = Empresa.objects.first() 
    if not empresa:
        # Sugestão: Redirecionar para dashboard ou criar página de erro
        return render(request, 'core/login.html')
        
    # Busca as categorias (já trazendo os ícones se existirem)
    categorias = Categoria.objects.filter(empresa=empresa)
    
    return render(request, 'scheduling/agendamento_wizard.html', {
        'categorias': categorias,
        'empresa': empresa
    })

def get_services(request):
    cat_id = request.GET.get('categoria_id')
    # Filtra serviços pela categoria
    servicos = Servico.objects.filter(categoria_id=cat_id)
    
    data = []
    for s in servicos:
        data.append({
            'id': s.id, 
            'nome': s.nome, 
            'preco': str(s.preco), 
            'tempo': s.tempo_execucao,
            # --- AQUI ESTÁ A CHAVE ---
            # Envia a URL completa da imagem para o Frontend
            'icone_url': s.icone.url if s.icone else None
        })
        
    return JsonResponse(data, safe=False)

def get_professionals(request):
    servico_id = request.GET.get('servico_id')
    
    # O filtro continua respeitando o serviço selecionado, 
    # mas o order_by('?') adiciona a aleatoriedade na resposta do banco de dados.
    profissionais = Profissional.objects.filter(
        servicos_realizados__id=servico_id
    ).order_by('?') 
    
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

# --- LÓGICA DE HORÁRIOS (MANTIDA SUA LÓGICA ROBUSTA) ---

def get_slots(request):
    data_str = request.GET.get('data') 
    prof_id = request.GET.get('profissional')
    servico_id = request.GET.get('servico')

    if not all([data_str, prof_id, servico_id]):
        return JsonResponse({'slots': []})

    try:
        # 1. Carregar Objetos
        profissional = Profissional.objects.get(id=prof_id)
        servico = Servico.objects.get(id=servico_id)
        empresa = profissional.empresa
        
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        tz = get_current_timezone()

        # 2. Validação de Segurança (Limite de Dias)
        hoje = timezone.localdate()
        # Garante fallback de 30 dias se o campo não existir
        dias_limite = getattr(empresa, 'limite_agendamento_dias', 30)
        data_limite = hoje + timedelta(days=dias_limite)
        
        if data_obj > data_limite:
            return JsonResponse({
                'slots': [], 
                'message': f'Agendamentos permitidos apenas até {data_limite.strftime("%d/%m")}'
            }, status=400)

    except Exception as e:
        return JsonResponse({'slots': []})

    # 3. Horário da Loja
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

    # 4. Jornada do Profissional
    dia_semana_prof = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'][data_obj.weekday()]
    jornada = profissional.jornada_config.get(dia_semana_prof, {})
    
    if not jornada.get('entrada') or not jornada.get('saida'):
        return JsonResponse({'slots': []})

    try:
        prof_entrada = datetime.strptime(jornada['entrada'], '%H:%M').time()
        prof_saida = datetime.strptime(jornada['saida'], '%H:%M').time()
    except:
        return JsonResponse({'slots': []})

    # --- Cálculo do Intervalo (Almoço) ---
    intervalo_inicio = None
    intervalo_fim = None
    
    if jornada.get('intervalo_inicio') and jornada.get('intervalo_fim'):
        try:
            int_ini_time = datetime.strptime(jornada['intervalo_inicio'], '%H:%M').time()
            int_fim_time = datetime.strptime(jornada['intervalo_fim'], '%H:%M').time()
            
            intervalo_inicio = make_aware(datetime.combine(data_obj, int_ini_time), tz)
            intervalo_fim = make_aware(datetime.combine(data_obj, int_fim_time), tz)
        except:
            pass 

    # 5. Intersecção
    inicio_efetivo = max(loja_abertura, prof_entrada)
    fim_efetivo = min(loja_fechamento, prof_saida)

    current_dt = make_aware(datetime.combine(data_obj, inicio_efetivo), tz)
    end_dt = make_aware(datetime.combine(data_obj, fim_efetivo), tz)

    # 6. Carregar Ocupações
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

    # 7. Loop
    while current_dt + timedelta(minutes=tempo_servico) <= end_dt:
        slot_fim = current_dt + timedelta(minutes=tempo_servico)
        is_available = True
        
        # Filtro 1: Intervalo
        if intervalo_inicio and intervalo_fim:
            if (current_dt < intervalo_fim) and (slot_fim > intervalo_inicio):
                is_available = False

        # Filtro 2: Agendamentos
        if is_available:
            for ag in ocupados:
                if (current_dt < ag.data_hora_fim) and (slot_fim > ag.data_hora_inicio):
                    is_available = False
                    break
        
        # Filtro 3: Bloqueios
        if is_available:
            for b in bloqueios:
                if (current_dt < b.data_fim) and (slot_fim > b.data_inicio):
                    is_available = False
                    break

        # Filtro 4: Horário Passado
        if is_available and data_obj == timezone.localdate():
            if current_dt < timezone.localtime():
                is_available = False

        slots.append({'hora': current_dt.strftime('%H:%M'), 'disponivel': is_available})
        current_dt += timedelta(minutes=30) 

    return JsonResponse({'slots': slots})


# --- API DE CONFIRMAÇÃO (MANTIDA) ---

@require_POST
def confirm_booking(request):
    try:
        data = json.loads(request.body)
        tz = get_current_timezone()
        
        profissional = Profissional.objects.get(id=data['profissional_id'])
        servico = Servico.objects.get(id=data['servico_id'])
        
        str_inicio = f"{data['data']} {data['hora']}"
        inicio_naive = datetime.strptime(str_inicio, '%Y-%m-%d %H:%M')
        inicio = make_aware(inicio_naive, tz)
        fim = inicio + timedelta(minutes=servico.tempo_execucao)

        # Validação de Segurança do Intervalo
        dia_semana = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'][inicio.weekday()]
        jornada = profissional.jornada_config.get(dia_semana, {})
        
        if jornada.get('intervalo_inicio') and jornada.get('intervalo_fim'):
            int_ini = make_aware(datetime.combine(inicio.date(), datetime.strptime(jornada['intervalo_inicio'], '%H:%M').time()), tz)
            int_fim = make_aware(datetime.combine(inicio.date(), datetime.strptime(jornada['intervalo_fim'], '%H:%M').time()), tz)
            
            if (inicio < int_fim) and (fim > int_ini):
                    return JsonResponse({'status': 'error', 'message': 'Horário indisponível (Intervalo).'}, status=409)

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


# --- FUNÇÕES DE GESTÃO ---

@login_required
def gestao_agendamentos(request):
    agendamentos = Agendamento.objects.filter(
        empresa=request.user.empresa,
        data_hora_inicio__gte=timezone.now() - timedelta(days=1)
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