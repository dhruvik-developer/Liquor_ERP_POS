from django.contrib import admin
from .models import Promotion, CardSetup

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "created_at")
    search_fields = ("title", "tagline")


@admin.register(CardSetup)
class CardSetupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "fee", "status", "created_at")
    search_fields = ("name",)
