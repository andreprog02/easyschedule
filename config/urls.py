from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView # <--- Importante para o redirecionamento

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. ROTA DA RAIZ (Homepage Vazia)
    # Se o usuário acessar apenas o domínio, redireciona para o Login
    path('', RedirectView.as_view(url='/conta/login/'), name='home_redirect'),

    # 2. Rotas do Sistema (Dashboard, Login, Configurações)
    path('conta/', include('core.urls')),
    path('servicos/', include('services.urls')),
    path('equipe/', include('professionals.urls')),
    
    # 3. Rota de Agendamento (Multi-Tenant / Slug)
    # IMPORTANTE: Mantive por último para evitar conflitos de URL
    # Aqui o Django vai procurar por "slugs" como /barbearia-top/
    path('', include('scheduling.urls')), 
]

# Configuração de Arquivos de Mídia (Imagens) - Apenas uma vez
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)