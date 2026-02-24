from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.CardTemplateViewSet, basename='template')
router.register(r'', views.IDCardViewSet, basename='card')

urlpatterns = [
    path('', include(router.urls)),
    path('export/csv/', views.IDCardViewSet.as_view({'get': 'export_csv'}), name='export-csv'),
    path('batch/create/', views.IDCardViewSet.as_view({'post': 'batch_create'}), name='batch-create'),
]