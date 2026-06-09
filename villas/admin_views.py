from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import HasAdminRole
from .models import Villa
from .serializers import HostVillaSerializer
import datetime

class AdminPendingVillaListView(APIView):
    """GET /admin/villas/pending/ — list all villas waiting for review."""
    permission_classes = [HasAdminRole]

    def get(self, request):
        villas = (
            Villa.objects
            .filter(status=Villa.STATUS_PENDING_REVIEW)
            .select_related('host__user')
            .prefetch_related('photos', 'amenities')
            .order_by('created_at')
        )
        return Response({'villas': HostVillaSerializer(villas, many=True).data})

class AdminVillaActionView(APIView):
    """POST /admin/villas/{id}/approve/ or /admin/villas/{id}/reject/."""
    permission_classes = [HasAdminRole]

    def post(self, request, pk, action):
        try:
            villa = Villa.objects.get(pk=pk)
        except Villa.DoesNotExist:
            return Response({'error': 'Villa not found.'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            villa.status = Villa.STATUS_PUBLISHED
            villa.is_verified = True
            villa.verified_at = datetime.datetime.now()
            villa.verified_by = request.user
            villa.rejection_reason = ""
            villa.save()
            return Response({'detail': 'Villa approved and published.', 'status': villa.status})
        
        elif action == 'reject':
            reason = request.data.get('reason', 'Listing does not meet requirements.')
            villa.status = Villa.STATUS_DRAFT
            villa.rejection_reason = reason
            villa.save()
            return Response({'detail': 'Villa rejected and sent back to draft.', 'status': villa.status})
        
        return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)
