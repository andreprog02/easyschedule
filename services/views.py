import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Categoria, Servico

@login_required
def config_servicos(request):
    categorias = Categoria.objects.filter(empresa=request.user.empresa).prefetch_related('servicos')
    return render(request, 'services/config_servicos.html', {'categorias': categorias})

# --- API PARA CATEGORIAS ---

@login_required
@require_POST
def add_categoria(request):
    # Suporte a FormData (com arquivo) e JSON
    nome = request.POST.get('nome')
    icone = request.FILES.get('icone')
    
    # Fallback para JSON se não vier via POST form
    if not nome and request.body:
        try:
            data = json.loads(request.body)
            nome = data.get('nome')
        except:
            pass

    if nome:
        categoria = Categoria.objects.create(
            empresa=request.user.empresa, 
            nome=nome,
            icone=icone
        )
        return JsonResponse({
            'status': 'success', 
            'id': categoria.id, 
            'nome': categoria.nome,
            'icone_url': categoria.icone.url if categoria.icone else None
        })
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
    try:
        # Pega dados via POST (FormData)
        cat_id = request.POST.get('categoria_id')
        nome = request.POST.get('nome')
        preco = request.POST.get('preco')
        tempo = request.POST.get('tempo')
        icone = request.FILES.get('icone')
        
        # Fallback para JSON (caso antigo)
        if not cat_id and request.body:
            data = json.loads(request.body)
            cat_id = data.get('categoria_id')
            nome = data.get('nome')
            preco = data.get('preco')
            tempo = data.get('tempo')

        categoria = get_object_or_404(Categoria, id=cat_id, empresa=request.user.empresa)
        
        # Tratamento do Preço (troca vírgula por ponto e evita vazio)
        if preco:
            preco = str(preco).replace(',', '.')
            if preco.strip() == '': preco = '0.00'
        
        servico = Servico.objects.create(
            categoria=categoria,
            nome=nome,
            preco=preco,
            tempo_execucao=tempo,
            icone=icone
        )
        return JsonResponse({
            'status': 'success', 
            'id': servico.id,
            'nome': servico.nome,
            'preco': str(servico.preco),
            'tempo': servico.tempo_execucao,
            'icone_url': servico.icone.url if servico.icone else None
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@require_POST
def edit_service(request, service_id):
    servico = get_object_or_404(Servico, id=service_id, categoria__empresa=request.user.empresa)
    
    # 1. Tenta pegar via FormData (Novo Padrão com Imagem)
    nome = request.POST.get('nome')
    preco = request.POST.get('preco')
    tempo = request.POST.get('tempo')
    icone = request.FILES.get('icone')

    # 2. Se não veio nada no POST, tenta JSON (fallback)
    if not nome and request.body:
        try:
            data = json.loads(request.body)
            nome = data.get('nome')
            preco = data.get('preco')
            tempo = data.get('tempo')
        except:
            pass

    # Atualização dos Campos
    if nome: servico.nome = nome
    if tempo: servico.tempo_execucao = tempo
    
    if preco is not None:
        # Limpeza para evitar erro de Decimal (ex: converter "" para None ou 0)
        preco_str = str(preco).replace(',', '.')
        if preco_str.strip() == '':
            pass # Não atualiza se estiver vazio
        else:
            servico.preco = preco_str

    if icone:
        servico.icone = icone
        
    servico.save()
    
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def delete_service(request, service_id):
    servico = get_object_or_404(Servico, id=service_id, categoria__empresa=request.user.empresa)
    servico.delete()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def edit_categoria(request, cat_id):
    categoria = get_object_or_404(Categoria, id=cat_id, empresa=request.user.empresa)
    
    nome = request.POST.get('nome')
    icone = request.FILES.get('icone')

    if nome:
        categoria.nome = nome
    if icone:
        categoria.icone = icone
        
    categoria.save()
    
    return JsonResponse({
        'status': 'success',
        'nome': categoria.nome,
        'icone_url': categoria.icone.url if categoria.icone else None
    })