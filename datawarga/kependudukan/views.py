from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse, Http404, JsonResponse
from django.views.generic import ListView
from django.urls import reverse
from django.db.models import Q
from .forms import WargaForm
from .models import Warga
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
def index(request):
    return render(request=request, template_name="index.html")

@login_required
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

@login_required
def formWargaSimpan(request):
    if request.POST:
        if "idwarga" in request.POST:
            idwarga = int(request.POST["idwarga"])
            warga_record = get_object_or_404(Warga, pk=idwarga)
            logger.info("update mode")
            form = WargaForm(request.POST, request.FILES, instance=warga_record)
        else:
            logger.info("insert mode")
            form = WargaForm(request.POST, request.FILES)
        if form.is_valid():
            logger.info("Form warga is valid")
            warga = form.save()
            base_url = reverse("kependudukan:listWargaView")
            payload = urlencode({"message": "data saved!"})
            url_redir = "{}?{}".format(base_url, payload)
            return redirect(url_redir)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()

@method_decorator(login_required, name='dispatch')
class WargaListView(ListView):
    paginate_by = 50
    template_name = "list_warga_view.html"
    queryset = Warga.objects.order_by("-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "message" in self.request.GET:
            context["message"] = self.request.GET["message"]
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.GET:
            search_keyword = str(self.request.GET["search"])

            queryset = queryset.filter(
                Q(nama_lengkap__icontains=search_keyword)
                | Q(nik__icontains=search_keyword)
            )
        return queryset

@login_required
def deleteFormWarga(request, idwarga=0):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    if request.POST:
        warga_record.delete()
        logger.info(
            "Deleting data warga with id : %s , name : %s"
            % (idwarga, warga_record.nama_lengkap)
        )
        base_url = reverse("kependudukan:listWarga")
        payload = urlencode(
            {"message": "data %s was deleted!" % (warga_record.nama_lengkap)}
        )
        url_redir = "{}?{}".format(base_url, payload)
        return redirect(url_redir)
    else:
        return render(
            request=request,
            template_name="delete_form_warga.html",
            context={"idwarga": idwarga, "warga": warga_record},
        )


def testView(request):
    return render(request=request, template_name="registration/login.html")
