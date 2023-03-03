from django.contrib import admin
from .models import Warga, Kompleks, TransaksiIuranBulanan

# Register your models here.
admin.site.register(Warga)
admin.site.register(Kompleks)
admin.site.register(TransaksiIuranBulanan)
