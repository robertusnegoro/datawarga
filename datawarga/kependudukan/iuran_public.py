from .forms import IuranBulananForm
from .models import Warga, Kompleks, TransaksiIuranBulanan
from .utility import helper_finance_year_list
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core import serializers
from urllib.parse import urlencode
import logging
import json

logger = logging.getLogger(__name__)


def form_iuran_bulanan_display(request):
    list_kompleks = Kompleks.objects.order_by('id')
    context = {'list_kompleks': list_kompleks}
    context["iuran_year_period"] = helper_finance_year_list()

    if request.POST:
        id_komplek = int(request.POST['kompleks'])
        periode_tahun = str(request.POST['periode_tahun'])
        list_trx = TransaksiIuranBulanan.objects.order_by("periode_bulan").filter(
            periode_tahun=periode_tahun, kompleks__id=id_komplek
        )
        context['data_pembayaran'] = list_trx
        context['periode_tahun'] = periode_tahun

    return render(
        request=request, template_name="public/iuran.html", context=context
    )
