import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Profissional, BloqueioAgenda
from services.models import Servico

@login_required
def gestao_equipe(request):
    # Carrega profissionais e serviços para o formulário
    profissionais = Profissional.objects.filter(empresa=request.user.empresa)
    todos_servicos = Servico.objects.filter(categoria__empresa=request.user.empresa)
    return render(request, 'professionals/gestao_equipe.html', {
        'profissionais': profissionais,
        'todos_servicos': todos_servicos
    })

@login_required
@require_POST
def api_add_profissional(request):
    # Usando request.POST pois teremos upload de arquivo (foto)
    nome = request.POST.get('nome')
    especialidade = request.POST.get('especialidade')
    servicos_ids = request.POST.getlist('servicos[]')
    foto = request.FILES.get('foto')
    
    # Jornada (JSON enviado como string pelo JS)
    jornada_json = request.POST.get('jornada')
    
    try:
        profissional = Profissional.objects.create(
            empresa=request.user.empresa,
            nome=nome,
            especialidade=especialidade,
            foto=foto,
            jornada_config=json.loads(jornada_json) if jornada_json else {}
        )
        if servicos_ids:
            profissional.servicos_realizados.set(servicos_ids)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def api_delete_profissional(request, prof_id):
    profissional = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    profissional.delete()
    return JsonResponse({'status': 'success'})


@login_required
def gestao_folgas(request):
    folgas = BloqueioAgenda.objects.filter(empresa=request.user.empresa).order_by('-data_inicio')
    profissionais = Profissional.objects.filter(empresa=request.user.empresa)
    return render(request, 'professionals/gestao_folgas.html', {
        'folgas': folgas,
        'profissionais': profissionais
    })

@login_required
@require_POST
def api_add_folga(request):
    data = json.loads(request.body)
    prof_id = data.get('profissional_id') # Se for null, é coletiva
    
    # Converte strings para datetime
    # Formato esperado: "2026-01-25T08:00"
    dt_inicio = datetime.fromisoformat(data['inicio'])
    dt_fim = datetime.fromisoformat(data['fim'])
    
    profissional = None
    if prof_id:
        profissional = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
        
    BloqueioAgenda.objects.create(
        empresa=request.user.empresa,
        profissional=profissional,
        data_inicio=dt_inicio,
        data_fim=dt_fim,
        motivo=data.get('motivo', '')
    )
    return JsonResponse({'status': 'success'})

@login_required
def api_get_profissional(request, prof_id):
    """Retorna os dados do profissional para preencher o modal de edição"""
    prof = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    
    # Prepara a lista de IDs de serviços que ele já faz
    servicos_ids = list(prof.servicos_realizados.values_list('id', flat=True))
    
    data = {
        'id': prof.id,
        'nome': prof.nome,
        'especialidade': prof.especialidade,
        'jornada': prof.jornada_config,
        'servicos': servicos_ids,
        'foto_url': prof.foto.url if prof.foto else None
    }
    return JsonResponse(data)

@login_required
@require_POST
def api_edit_profissional(request, prof_id):
    """Salva as alterações do profissional"""
    prof = get_object_or_404(Profissional, id=prof_id, empresa=request.user.empresa)
    
    prof.nome = request.POST.get('nome')
    prof.especialidade = request.POST.get('especialidade')
    
    jornada_json = request.POST.get('jornada')
    if jornada_json:
        prof.jornada_config = json.loads(jornada_json)
    
    if request.FILES.get('foto'):
        prof.foto = request.FILES.get('foto')
    
    prof.save()
    
    # Atualiza os serviços (relação ManyToMany)
    servicos_ids = request.POST.getlist('servicos[]')
    prof.servicos_realizados.set(servicos_ids)
    
    return JsonResponse({'status': 'success'})