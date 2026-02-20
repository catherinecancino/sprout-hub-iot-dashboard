# api/views.py — Complete file with Knowledge Library endpoints

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from config.firebase import db
from .services import IoTService
from .ai_service import AIChatService
from .rag_service import RAGService
from .knowledge_library_service import KnowledgeLibraryService


# ─────────────────────── EXISTING VIEWS ───────────────────────

class SensorDataReceiver(APIView):
    def post(self, request):
        try:
            data = request.data
            if 'node_id' not in data:
                return Response({"error": "node_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            saved_data = IoTService.process_reading(data)
            return Response({
                "message": "Data received successfully",
                "node_id": data['node_id'],
                "data": saved_data
            }, status=status.HTTP_201_CREATED)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatbotView(APIView):
    def post(self, request):
        question = request.data.get('question')
        if not question:
            return Response({"error": "No question provided"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            answer = AIChatService.ask_agronomist(question)
            return Response({"question": question, "answer": answer, "model": "gpt-4o-mini (OpenAI)"})
        except Exception as e:
            return Response({"error": f"AI service error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploadDocumentView(APIView):
    """Upload document → extracts thresholds → saves to crop profile library"""

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        document_name = request.POST.get('document_name', file.name)
        crop_type = request.POST.get('crop_type', '').strip()
        description = request.POST.get('description', '')

        if not crop_type:
            return Response({"error": "crop_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        file_path = default_storage.save(f'temp/{file.name}', ContentFile(file.read()))
        full_path = default_storage.path(file_path)

        try:
            metadata = {'crop_type': crop_type.lower(), 'description': description}
            result = RAGService.process_document(full_path, document_name, metadata)

            # Save to Knowledge Library (permanent crop profile)
            KnowledgeLibraryService.save_crop_profile(
                crop_type=crop_type,
                thresholds=result.get('thresholds'),
                document_name=document_name,
                description=description
            )

            default_storage.delete(file_path)

            return Response({
                "message": f"Document uploaded and saved to '{crop_type.title()}' crop profile",
                **result
            })

        except Exception as e:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListDocumentsView(APIView):
    def get(self, request):
        try:
            documents = RAGService.list_documents()
            return Response({"documents": documents})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteDocumentView(APIView):
    def delete(self, request, document_name):
        try:
            result = RAGService.delete_document(document_name)
            return Response({"message": f"Document '{document_name}' deleted", **result})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchKnowledgeView(APIView):
    def post(self, request):
        query = request.data.get('query')
        crop_type = request.data.get('crop_type')
        n_results = request.data.get('n_results', 3)
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            filter_metadata = {"crop_type": crop_type.lower()} if crop_type else None
            results = RAGService.search_knowledge(query, n_results, filter_metadata)
            return Response({"query": query, "results": results})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────── KNOWLEDGE LIBRARY VIEWS ───────────────────────

class KnowledgeLibraryListView(APIView):
    """GET all crop profiles for dropdown"""

    def get(self, request):
        try:
            profiles = KnowledgeLibraryService.get_all_crop_profiles()
            return Response({"crops": profiles, "total": len(profiles)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CropProfileDetailView(APIView):
    """GET or DELETE a single crop profile"""

    def get(self, request, crop_type):
        try:
            profile = KnowledgeLibraryService.get_crop_profile(crop_type)
            if profile:
                return Response({"crop": profile})
            return Response({"error": f"Crop '{crop_type}' not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, crop_type):
        try:
            KnowledgeLibraryService.delete_crop_profile(crop_type)
            return Response({"message": f"Crop profile '{crop_type}' deleted from library"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignCropToNodeView(APIView):
    """
    POST: Assign active crop to a node (what the dropdown triggers)
    GET:  Get current active crop for a node
    """

    def post(self, request):
        node_id = request.data.get('node_id')
        crop_type = request.data.get('crop_type')

        if not node_id or not crop_type:
            return Response(
                {"error": "node_id and crop_type are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            result = KnowledgeLibraryService.set_active_crop_for_node(node_id, crop_type)
            return Response({
                "message": f"Node '{node_id}' switched to '{crop_type}' profile",
                **result
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        node_id = request.query_params.get('node_id')
        if not node_id:
            return Response({"error": "node_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            active_crop = KnowledgeLibraryService.get_active_crop_for_node(node_id)
            thresholds, _ = KnowledgeLibraryService.get_active_thresholds_for_node(node_id)
            return Response({"node_id": node_id, "active_crop": active_crop, "thresholds": thresholds})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────── UTILITY VIEWS ───────────────────────

class AIStatusView(APIView):
    def get(self, request):
        try:
            return Response(AIChatService.check_openai_status())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NodeConnectivityCheckView(APIView):
    def post(self, request):
        try:
            IoTService.check_node_connectivity()
            return Response({"message": "Connectivity check completed"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NodeComparisonView(APIView):
    def get(self, request):
        try:
            comparison = AIChatService.get_node_comparison()
            return Response({"comparison": comparison})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)