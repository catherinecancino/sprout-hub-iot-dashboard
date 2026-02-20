# api/urls.py

from django.urls import path
from .views import (
    SensorDataReceiver,
    ChatbotView,
    UploadDocumentView,
    ListDocumentsView,
    DeleteDocumentView,
    SearchKnowledgeView,
    KnowledgeLibraryListView,
    CropProfileDetailView,
    AssignCropToNodeView,
    AIStatusView,
    NodeConnectivityCheckView,
    NodeComparisonView,
)

urlpatterns = [
    # ── IoT Data ──
    path('ingest/', SensorDataReceiver.as_view(), name='ingest'),

    # ── AI Chatbot ──
    path('chat/', ChatbotView.as_view(), name='chat'),

    # ── RAG Documents ──
    path('upload-document/', UploadDocumentView.as_view(), name='upload-document'),
    path('list-documents/', ListDocumentsView.as_view(), name='list-documents'),
    path('delete-document/<str:document_name>/', DeleteDocumentView.as_view(), name='delete-document'),
    path('search-knowledge/', SearchKnowledgeView.as_view(), name='search-knowledge'),

    # ── Knowledge Library (Crop Profiles) ──
    path('knowledge-library/', KnowledgeLibraryListView.as_view(), name='knowledge-library'),
    path('knowledge-library/<str:crop_type>/', CropProfileDetailView.as_view(), name='crop-profile-detail'),

    # ── Node Crop Assignment ──
    path('assign-crop/', AssignCropToNodeView.as_view(), name='assign-crop'),

    # ── Utilities ──
    path('ai-status/', AIStatusView.as_view(), name='ai-status'),
    path('check-connectivity/', NodeConnectivityCheckView.as_view(), name='check-connectivity'),
    path('compare-nodes/', NodeComparisonView.as_view(), name='compare-nodes'),
]