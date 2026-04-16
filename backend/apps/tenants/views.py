from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Owners/Admins can only see their own company
        return Company.objects.filter(id=self.request.company.id)

    def get_object(self):
        return self.request.company

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.company)
        return Response(serializer.data)
