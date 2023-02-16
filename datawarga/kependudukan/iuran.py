from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from django.http import HttpResponse, Http404, JsonResponse
from .models import Warga, Kompleks, TransaksiIuranBulanan

@login_required
def form_iuran_bulanan(request, idkompleks, year=datetime.now().strftime('%Y')):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)

    return HttpResponse("%s ; %s" % (year, data_kompleks))
