"""
Accounts views — registration, auth, user management, team invitations.
"""
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Invitation
from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    InviteMemberSerializer,
    AcceptInvitationSerializer,
)
from .permissions import IsAdminOrAbove


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Issue tokens immediately after registration
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data["success"] = True
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        self.request.user.last_seen_at = timezone.now()
        self.request.user.save(update_fields=["last_seen_at"])
        return self.request.user


class TeamView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.company.members.filter(is_active=True)


class InviteMemberView(APIView):
    permission_classes = [IsAdminOrAbove]

    def post(self, request):
        serializer = InviteMemberSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        return Response(
            {"success": True, "message": f"Invitation sent to {invitation.email}"},
            status=status.HTTP_201_CREATED,
        )


class AcceptInvitationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invitation = Invitation.objects.select_related("company").get(
                token=serializer.validated_data["token"],
                is_accepted=False,
            )
        except Invitation.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "Invalid or expired invitation token."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invitation.expires_at < timezone.now():
            return Response(
                {"success": False, "error": {"message": "This invitation has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email=invitation.email,
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            company=invitation.company,
            role=invitation.role,
        )
        invitation.is_accepted = True
        invitation.save(update_fields=["is_accepted"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )
