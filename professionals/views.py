import json
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.timezone import make_aware

from core.models import Empresa
from services.models import Servico 
from .models import Profissional, BloqueioAgenda 

# --- TELAS ---

@login_required
def gestao_equipe(request):
    empresa = request.user.empresa
    profissionais = Profissional.objects.filter(empresa=empresa)
    
    # --- CORREÇÃO DO ERRO AQUI ---
    # O serviço é ligado à categoria, e a categoria à empresa.
    # Usamos categoria__empresa para filtrar corretamente.
    servicos = Servico.objects.filter(categoria__empresa=empresa)
    
    return render(request, 'professionals/gestao_equipe.html', {
        'profissionais': profissionais,
        'servicos': servicos,
        'empresa': empresa 
    })

@login_required
def gestao_folgas(request):
    empresa = request.user.empresa
    profissionais = Profissional.objects.filter(empresa=empresa)
    folgas = BloqueioAgenda.objects.filter(empresa=empresa).order_by('-data_inicio')
    return render(request, 'professionals/gestao_folgas.html', {
        'profissionais': profissionais,
        'folgas': folgas
    })

# --- APIS DE PROFISSIONAIS ---

@login_required
def api_get_profissional(request, prof_id):
    prof = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    return JsonResponse({
        'id': prof.id,
        'nome': prof.nome,
        'especialidade': prof.especialidade,
        'foto_url': prof.foto.url if prof.foto else None,
        'jornada': prof.jornada_config or {},
        # Retorna lista de IDs dos serviços vinculados
        'servicos_ids': list(prof.servicos_realizados.values_list('id', flat=True))
    })

@login_required
@require_POST
def api_add_profissional(request):
    try:
        # Pega dados via POST (FormData)
        nome = request.POST.get('nome')
        especialidade = request.POST.get('especialidade', '')
        foto = request.FILES.get('foto') # Foto vem em FILES
        
        jornada_str = request.POST.get('jornada_config', '{}')
        jornada_config = json.loads(jornada_str)
        
        servicos_str = request.POST.get('servicos', '[]')
        servicos_ids = json.loads(servicos_str)

        prof = Profissional.objects.create(
            empresa=request.user.empresa,
            nome=nome,
            especialidade=especialidade,
            foto=foto,
            jornada_config=jornada_config
        )
        
        # Salva os serviços ManyToMany
        if servicos_ids:
            prof.servicos_realizados.set(servicos_ids)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_edit_profissional(request, prof_id):
    prof = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    try:
        prof.nome = request.POST.get('nome')
        prof.especialidade = request.POST.get('especialidade', '')
        
        if 'foto' in request.FILES:
            prof.foto = request.FILES['foto']
            
        jornada_str = request.POST.get('jornada_config', '{}')
        prof.jornada_config = json.loads(jornada_str)
        
        servicos_str = request.POST.get('servicos', '[]')
        servicos_ids = json.loads(servicos_str)
        prof.servicos_realizados.set(servicos_ids)
        
        prof.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_delete_profissional(request, prof_id):
    prof = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    prof.delete()
    return JsonResponse({'status': 'success'})

# --- APIS DE FOLGAS ---

@login_required
def api_get_folga(request, folga_id):
    folga = get_object_or_404(BloqueioAgenda, id=folga_id, empresa=request.user.empresa)
    return JsonResponse({
        'id': folga.id,
        'tipo': 'individual' if folga.profissional else 'coletiva',
        'profissional_id': folga.profissional.id if folga.profissional else '',
        'inicio': folga.data_inicio.strftime('%Y-%m-%dT%H:%M'),
        'fim': folga.data_fim.strftime('%Y-%m-%dT%H:%M'),
        'motivo': folga.motivo
    })

@login_required
@require_POST
def api_add_folga(request):
    try:
        data = json.loads(request.body)
        prof_id = data.get('profissional_id') 
        
        inicio_naive = datetime.fromisoformat(data['inicio'])
        fim_naive = datetime.fromisoformat(data['fim'])
        dt_inicio = make_aware(inicio_naive)
        dt_fim = make_aware(fim_naive)
        
        profissional = None
        if prof_id and prof_id != 'coletiva':
            profissional = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
            
        BloqueioAgenda.objects.create(
            empresa=request.user.empresa,
            profissional=profissional,
            data_inicio=dt_inicio,
            data_fim=dt_fim,
            motivo=data.get('motivo', '')
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_edit_folga(request, folga_id):
    folga = get_object_or_404(BloqueioAgenda, id=folga_id, empresa=request.user.empresa)
    try:
        data = json.loads(request.body)
        
        inicio_naive = datetime.fromisoformat(data['inicio'])
        fim_naive = datetime.fromisoformat(data['fim'])
        folga.data_inicio = make_aware(inicio_naive)
        folga.data_fim = make_aware(fim_naive)
        
        folga.motivo = data.get('motivo', '')
        
        prof_id = data.get('profissional_id')
        if prof_id and prof_id != 'coletiva':
            profissional = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
            folga.profissional = profissional
        else:
            folga.profissional = None
            
        folga.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def api_delete_folga(request, folga_id):
    folga = get_object_or_404(BloqueioAgenda, id=folga_id, empresa=request.user.empresa)
    folga.delete()
    return JsonResponse({'status': 'success'})