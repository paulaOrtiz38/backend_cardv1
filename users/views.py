from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny , IsAdminUser
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from .models import CompanyUser
from .serializers import UserSerializer, CompanyUserSerializer
from companies.models import Company

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios del sistema.
    Solo accesible para superusuarios.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]  # Solo superusuarios

class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios por empresa.
    """
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filtrar usuarios según la empresa y permisos del usuario actual.
        """
        user = self.request.user
        company_id = self.request.query_params.get('company_id')
        
        if not company_id:
            return CompanyUser.objects.none()
        
        # Verificar que el usuario tenga permiso para gestionar usuarios en esta empresa
        user_permission = CompanyUser.objects.filter(
            user=user,
            company_id=company_id,
            can_manage_users=True
        ).exists()
        
        if not user_permission and not user.is_superuser:
            return CompanyUser.objects.none()
        
        return CompanyUser.objects.filter(company_id=company_id)
    
    def perform_create(self, serializer):
        """
        Al crear un usuario de empresa, verificar permisos.
        """
        company_id = self.request.data.get('company')
        if company_id:
            # Verificar permisos
            if not self.request.user.is_superuser:
                user_permission = CompanyUser.objects.filter(
                    user=self.request.user,
                    company_id=company_id,
                    can_manage_users=True
                ).exists()
                
                if not user_permission:
                    raise PermissionError("No tienes permiso para agregar usuarios a esta empresa")
        
        serializer.save(invited_by=self.request.user)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Registro de nuevo usuario usando API Key de empresa.
    """
    from companies.models import Company
    
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    company_api_key = request.data.get('company_api_key')
    
    # Validaciones básicas
    if not all([username, email, password, company_api_key]):
        return Response(
            {'error': 'Faltan campos requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el usuario ya existe
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'El nombre de usuario ya existe'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'El email ya está registrado'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar empresa por API Key
    try:
        company = Company.objects.get(api_key=company_api_key, is_active=True)
    except Company.DoesNotExist:
        return Response(
            {'error': 'API Key inválida o empresa inactiva'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Crear usuario
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Crear relación con empresa (rol por defecto: editor)
        CompanyUser.objects.create(
            user=user,
            company=company,
            role='editor',
            invited_by=None  # Registro automático
        )
        
        # Crear token de autenticación
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'Usuario registrado exitosamente',
            'user_id': user.id,
            'username': user.username,
            'token': token.key,
            'company': company.name
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Error al crear usuario: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Autenticación de usuario.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Se requieren nombre de usuario y contraseña'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Autenticar usuario
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Credenciales inválidas'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'Usuario inactivo'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Obtener o crear token
    token, created = Token.objects.get_or_create(user=user)
    
    # Obtener empresas del usuario
    companies = CompanyUser.objects.filter(user=user).select_related('company')
    companies_data = []
    
    for company_user in companies:
        companies_data.append({
            'company_id': str(company_user.company.id),
            'company_name': company_user.company.name,
            'role': company_user.role,
            'permissions': {
                'can_create_templates': company_user.can_create_templates,
                'can_manage_users': company_user.can_manage_users,
                'can_export_data': company_user.can_export_data,
            }
        })
    
    return Response({
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_superuser': user.is_superuser,
        'companies': companies_data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Cerrar sesión (eliminar token).
    """
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Sesión cerrada exitosamente'})
    except Exception as e:
        return Response(
            {'error': 'Error al cerrar sesión'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Obtener y actualizar perfil del usuario actual.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user