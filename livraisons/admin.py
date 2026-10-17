from django.contrib import admin

from restaurants.models import Restaurant

from .models import VersementLivreur


@admin.register(VersementLivreur)
class VersementLivreurAdmin(admin.ModelAdmin):
    list_display = ("jour", "livreur", "montant", "recu_par", "date_creation")
    list_filter = ("livreur", "jour")
    date_hierarchy = "jour"
    exclude = ("restaurant", "recu_par")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.restaurant = Restaurant.objects.filter(est_actif=True).first()
            obj.recu_par = request.user
        super().save_model(request, obj, form, change)


from django.contrib import admin

# Register your models here.
