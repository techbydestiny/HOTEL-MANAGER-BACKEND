# backend/consumables/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.ExpenseCategoryViewSet)
router.register('expenses', views.ExpenseViewSet)
router.register('attachments', views.ExpenseAttachmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]