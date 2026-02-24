from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import CompanyUser

# Filtro personalizado para empresas
class CompanyFilter(admin.SimpleListFilter):
    title = 'Empresa'
    parameter_name = 'company'
    
    def lookups(self, request, model_admin):
        companies = CompanyUser.objects.values_list(
            'company__id', 'company__name'
        ).distinct().order_by('company__name')
        return companies
    
    def queryset(self, request, queryset):
        if self.value():
            user_ids = CompanyUser.objects.filter(
                company_id=self.value()
            ).values_list('user_id', flat=True)
            return queryset.filter(id__in=user_ids)
        return queryset

# Inline para mostrar empresas en User admin
class CompanyUserInline(admin.TabularInline):
    model = CompanyUser
    fk_name = 'user'  # Especificar ForeignKey
    extra = 0
    fields = ['company', 'role', 'department']

# Custom UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = [CompanyUserInline]
    list_filter = ['is_staff', 'is_superuser', 'is_active', CompanyFilter]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin para CompanyUser
@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role']
    list_filter = ['company', 'role']