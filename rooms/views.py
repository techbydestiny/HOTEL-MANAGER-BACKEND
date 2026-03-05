# rooms/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Room
from .serializers import RoomSerializer, RoomStatusSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        room = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in dict(Room.STATUS_CHOICES):
            room.status = new_status
            room.save()
            return Response({'status': 'success', 'new_status': room.status})
        
        return Response(
            {'error': 'Invalid status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        available_rooms = Room.objects.filter(status='available')
        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)