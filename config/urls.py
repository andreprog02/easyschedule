from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. Rota Principal (Agendamento para o Cliente)
    path('', include('scheduling.urls')), 
    
    # 2. Rotas do Sistema (Dashboard e Login)
    path('conta/', include('core.urls')),
    
    # 3. NOVAS ROTAS (Conectando os módulos que faltavam)
    path('servicos/', include('services.urls')),
    path('equipe/', include('professionals.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)