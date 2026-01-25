import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Categoria, Servico

@login_required
def config_servicos(request):
    # Carrega categorias e serviços da empresa do usuário logado
    categorias = Categoria.objects.filter(empresa=request.user.empresa).prefetch_related('servicos')
    return render(request, 'services/config_servicos.html', {'categorias': categorias})

# --- API PARA CATEGORIAS ---

@login_required
@require_POST
def add_categoria(request):
    data = json.loads(request.body)
    nome = data.get('nome')
    
    if nome:
        categoria = Categoria.objects.create(empresa=request.user.empresa, nome=nome)
        return JsonResponse({'status': 'success', 'id': categoria.id, 'nome': categoria.nome})
    return JsonResponse({'status': 'error', 'message': 'Nome inválido'})

@login_required
@require_POST
def delete_categoria(request, cat_id):
    categoria = get_object_or_404(Categoria, id=cat_id, empresa=request.user.empresa)
    categoria.delete()
    return JsonResponse({'status': 'success'})

# --- API PARA SERVIÇOS ---

@login_required
@require_POST
def add_service(request):
    data = json.loads(request.body)
    try:
        categoria = get_object_or_404(Categoria, id=data['categoria_id'], empresa=request.user.empresa)
        servico = Servico.objects.create(
            categoria=categoria,
            nome=data['nome'],
            preco=data['preco'],
            tempo_execucao=data['tempo']
        )
        return JsonResponse({
            'status': 'success', 
            'id': servico.id,
            'nome': servico.nome,
            'preco': str(servico.preco),
            'tempo': servico.tempo_execucao
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def edit_service(request, service_id):
    servico = get_object_or_404(Servico, id=service_id, categoria__empresa=request.user.empresa)
    data = json.loads(request.body)
    
    servico.nome = data['nome']
    servico.preco = data['preco']
    servico.tempo_execucao = data['tempo']
    servico.save()
    
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def delete_service(request, service_id):
    servico = get_object_or_404(Servico, id=service_id, categoria__empresa=request.user.empresa)
    servico.delete()
    return JsonResponse({'status': 'success'})