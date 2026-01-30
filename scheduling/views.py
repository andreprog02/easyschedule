import json
import threading
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.utils.timezone import make_aware, get_current_timezone
from django.db import transaction, models 
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from twilio.rest import Client 

from core.models import Empresa, HorarioEspecial
from services.models import Categoria, Servico
from professionals.models import Profissional, BloqueioAgenda
from .models import Agendamento

# --- FUNÇÃO DE ENVIO DE WHATSAPP (Centralizada) ---
def disparar_whatsapp_thread(agendamento_id, tipo='confirmacao'):
    """
    Envia WhatsApp em segundo plano.
    tipo: 'confirmacao' ou 'cancelamento'
    """
    try:
        from .models import Agendamento
        # Re-busca o objeto para garantir dados atualizados
        agendamento = Agendamento.objects.get(id=agendamento_id)
        empresa = agendamento.empresa
        
        # 1. Valida credenciais
        if not empresa.twilio_sid or not empresa.twilio_token:
            return

        client = Client(empresa.twilio_sid, empresa.twilio_token)
        
        # 2. Seleciona o Template Correto
        if tipo == 'cancelamento':
            template = empresa.msg_cancelamento
        else:
            template = empresa.msg_confirmacao

        msg = template.format(
            cliente=agendamento.cliente_nome,
            empresa=empresa.nome,
            data=agendamento.data_hora_inicio.strftime('%d/%m/%Y'),
            hora=agendamento.data_hora_inicio.strftime('%H:%M'),
            profissional=agendamento.profissional.nome
        )
        
        # 3. Tratamento do Telefone do Cliente (DESTINO)
        tel_destino = ''.join(filter(str.isdigit, agendamento.cliente_telefone))
        if len(tel_destino) <= 11: 
            tel_destino = "55" + tel_destino
        destino_final = f"whatsapp:+{tel_destino}"

        # 4. Tratamento do Telefone da Empresa (ORIGEM)
        origem_numeros = ''.join(filter(str.isdigit, empresa.twilio_whatsapp_origem))
        origem_final = f"whatsapp:+{origem_numeros}"

        # 5. Envio
        client.messages.create(
            from_=origem_final,
            body=msg,
            to=destino_final
        )
        print(f"WhatsApp ({tipo}) enviado de {origem_final} para {agendamento.cliente_nome}")
        
    except Exception as e:
        print(f"Erro ao enviar WhatsApp ({tipo}): {e}")


# --- WIZARD E APIS DE CONSULTA ---

@ensure_csrf_cookie
def agendamento_wizard(request):
    # 1. Busca a empresa
    empresa = Empresa.objects.first() 
    
    if not empresa:
        return render(request, 'core/login.html')
        
    # 2. Busca categorias
    categorias = Categoria.objects.filter(empresa=empresa)
    
    # --- Lógica de Seleção de Tema ---
    
    # Recupera o tema escolhido (com fallback para 'padrao' se o campo não existir ainda)
    tema = getattr(empresa, 'template_tema', 'padrao')
    
    if tema == 'feminino':
        nome_template = 'scheduling/agendamento_feminino.html'
    elif tema == 'barber_dark':
        nome_template = 'scheduling/agendamento_barber_dark.html'
    else:
        # Tema Padrão (Azul)
        nome_template = 'scheduling/agendamento_wizard.html'
    
    # 3. Renderiza o template decidido acima
    return render(request, nome_template, {
        'categorias': categorias,
        'empresa': empresa
    })


def get_services(request):
    cat_id = request.GET.get('categoria_id')
    servicos = Servico.objects.filter(categoria_id=cat_id)
    data = []
    for s in servicos:
        data.append({
            'id': s.id, 
            'nome': s.nome, 
            'preco': str(s.preco), 
            'tempo': s.tempo_execucao,
            'icone_url': s.icone.url if s.icone else None
        })
    return JsonResponse(data, safe=False)

def get_professionals(request):
    servico_id = request.GET.get('servico_id')
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


# --- LÓGICA DE HORÁRIOS ---

def get_slots(request):
    data_str = request.GET.get('data') 
    prof_id = request.GET.get('profissional')
    servico_id = request.GET.get('servico')

    if not all([data_str, prof_id, servico_id]):
        return JsonResponse({'slots': []})

    try:
        profissional = Profissional.objects.get(id=prof_id)
        servico = Servico.objects.get(id=servico_id)
        empresa = profissional.empresa
        
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        tz = get_current_timezone()

        hoje = timezone.localdate()
        dias_limite = getattr(empresa, 'limite_agendamento_dias', 30)
        data_limite = hoje + timedelta(days=dias_limite)
        
        if data_obj > data_limite:
            return JsonResponse({
                'slots': [], 
                'message': f'Agendamentos permitidos apenas até {data_limite.strftime("%d/%m")}'
            }, status=400)

    except Exception:
        return JsonResponse({'slots': []})

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

    dia_semana_prof = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'][data_obj.weekday()]
    jornada = profissional.jornada_config.get(dia_semana_prof, {})
    
    if not jornada.get('entrada') or not jornada.get('saida'):
        return JsonResponse({'slots': []})

    try:
        prof_entrada = datetime.strptime(jornada['entrada'], '%H:%M').time()
        prof_saida = datetime.strptime(jornada['saida'], '%H:%M').time()
    except:
        return JsonResponse({'slots': []})

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

    inicio_efetivo = max(loja_abertura, prof_entrada)
    fim_efetivo = min(loja_fechamento, prof_saida)

    current_dt = make_aware(datetime.combine(data_obj, inicio_efetivo), tz)
    end_dt = make_aware(datetime.combine(data_obj, fim_efetivo), tz)

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

    while current_dt + timedelta(minutes=tempo_servico) <= end_dt:
        slot_fim = current_dt + timedelta(minutes=tempo_servico)
        is_available = True
        
        if intervalo_inicio and intervalo_fim:
            if (current_dt < intervalo_fim) and (slot_fim > intervalo_inicio):
                is_available = False

        if is_available:
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
        current_dt += timedelta(minutes=30) 

    return JsonResponse({'slots': slots})


# --- API DE CONFIRMAÇÃO ---

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

        # Validação do Intervalo
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
            
            # --- ENVIO DE CONFIRMAÇÃO ---
            t = threading.Thread(target=disparar_whatsapp_thread, args=(novo.id, 'confirmacao'))
            t.start()

        return JsonResponse({'status': 'success', 'codigo': str(novo.codigo_autenticacao)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# --- FUNÇÕES DE GESTÃO (ATUALIZADO) ---

@login_required
def gestao_agendamentos(request):
    # Mostra apenas o que NÃO está cancelado para não poluir
    agendamentos = Agendamento.objects.filter(
        empresa=request.user.empresa,
        data_hora_inicio__gte=timezone.now() - timedelta(days=1)
    ).exclude(status='cancelado').order_by('data_hora_inicio') # <-- Filtro Novo
    
    return render(request, 'scheduling/gestao_agendamentos.html', {'agendamentos': agendamentos})

@login_required
@require_POST
def api_delete_agendamento(request, ag_id):
    """
    Agora faz SOFT DELETE e envia WhatsApp de Cancelamento
    """
    agendamento = get_object_or_404(Agendamento, id=ag_id, empresa=request.user.empresa)
    
    # Atualiza status em vez de deletar
    agendamento.status = 'cancelado'
    agendamento.save()
    
    # Dispara aviso de cancelamento
    t = threading.Thread(target=disparar_whatsapp_thread, args=(agendamento.id, 'cancelamento'))
    t.start()
    
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