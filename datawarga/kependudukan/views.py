from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from django.urls import reverse
from django.db.models import Q
from .forms import WargaForm
from .models import Warga
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    return render(request=request, template_name="index.html")


def formWarga(request, idwarga=0):
    if idwarga == 0:
        form = WargaForm()
    else:
        warga_record = get_object_or_404(Warga, pk=idwarga)
        form = WargaForm(instance=warga_record)
    logger.info("Form warga empty loaded")
    return render(
        request=request,
        template_name="form_warga.html",
        context={"form": form, "idwarga": int(idwarga)},
    )


def formWargaSimpan(request):
    if request.POST:
        if 'idwarga' in request.POST:
            idwarga = int(request.POST['idwarga'])
            warga_record = get_object_or_404(Warga, pk=idwarga)
            logger.info("update mode")
            form = WargaForm(request.POST, request.FILES, instance=warga_record)
        else:
            logger.info("insert mode")
            form = WargaForm(request.POST, request.FILES)
        if form.is_valid():
            logger.info("Form warga is valid")
            warga = form.save()
            base_url = reverse("kependudukan:listWarga")
            payload = urlencode({"message": "data saved!"})
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


def WargaList(request):
    message = ""
    search_keyword = ""
    if request.GET:
        message = request.GET["message"]
    if request.POST:
        search_keyword = request.POST["search"]

    if search_keyword == "":
        list_warga = Warga.objects.all()
    else:
        list_warga = Warga.objects.filter(
            Q(nama_lengkap__contains=search_keyword) | Q(nik__contains=search_keyword)
        )

    context = {"list_warga": list_warga, "message": message}

    return render(request=request, template_name="list_warga.html", context=context)

def deleteFormWarga(request, idwarga=0):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    if request.POST:
        warga_record.delete()
        logger.info("Deleting data warga with id : %s , name : %s" % (idwarga, warga_record.nama_lengkap))
        base_url = reverse("kependudukan:listWarga")
        payload = urlencode({"message": "data %s was deleted!" % (warga_record.nama_lengkap)})
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)
    else:
        return render(request=request, template_name="delete_form_warga.html", context={'idwarga': idwarga, 'warga': warga_record})
