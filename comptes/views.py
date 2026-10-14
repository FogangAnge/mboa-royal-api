from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions

from .serializers import InscriptionSerializer, UtilisateurSerializer


class InscriptionView(generics.CreateAPIView):
    """POST /api/auth/inscription/ : crée un compte client."""

    serializer_class = InscriptionSerializer
    permission_classes = [permissions.AllowAny]


class MoiView(generics.RetrieveAPIView):
    """GET /api/auth/moi/ : renvoie le compte de la personne connectée."""

    serializer_class = UtilisateurSerializer

    def get_object(self):
        return self.request.user