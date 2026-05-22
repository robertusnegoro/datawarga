import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .forms import KendaraanForm
from .models import Warga, Kendaraan

logger = logging.getLogger(__name__)


@login_required
def form_kendaraan(request, idwarga, idkendaraan=0):
    warga_record = get_object_or_404(Warga, pk=idwarga)
    context = {"warga": warga_record, "idwarga": idwarga, "idkendaraan": idkendaraan}

    if idkendaraan == 0:
        form = KendaraanForm(initial={"pemilik": warga_record})
    else:
        kendaraan_record = get_object_or_404(Kendaraan, pk=idkendaraan)
        context["kendaraan"] = kendaraan_record
        form = KendaraanForm(instance=kendaraan_record)

    context["form"] = form

    return render(
        request=request,
        template_name="form_kendaraan.html",
        context=context,
    )


@login_required
def form_kendaraan_save(request):
    if request.POST:
        idwarga = int(request.POST.get("idwarga", 0))
        idkendaraan = int(request.POST.get("idkendaraan", 0))

        warga_record = get_object_or_404(Warga, pk=idwarga)

        if idkendaraan > 0:
            kendaraan_record = get_object_or_404(Kendaraan, pk=idkendaraan)
            logger.info("update mode kendaraan")
            form = KendaraanForm(request.POST, request.FILES, instance=kendaraan_record)
        else:
            logger.info("insert mode kendaraan")
            form = KendaraanForm(request.POST, request.FILES)

        if form.is_valid():
            logger.info("Form kendaraan is valid")
            kendaraan = form.save(commit=False)
            kendaraan.pemilik = warga_record
            kendaraan.save()

            base_url = reverse(
                "kependudukan:detailWarga",
                kwargs={"idwarga": idwarga},
            )
            messages.success(
                request,
                f"Data kendaraan dengan plat nomor <strong>{kendaraan.plat_nomor}</strong> berhasil disimpan.",
            )
            return redirect(base_url)
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@login_required
def delete_kendaraan(request, idkendaraan=0):
    kendaraan_record = get_object_or_404(Kendaraan, pk=idkendaraan)
    warga_id = kendaraan_record.pemilik.id

    if request.method == "POST":
        plat_nomor = kendaraan_record.plat_nomor
        kendaraan_record.delete()
        logger.info(
            "Deleting data kendaraan with id : %s , plat_nomor : %s"
            % (idkendaraan, plat_nomor)
        )
        base_url = reverse("kependudukan:detailWarga", kwargs={"idwarga": warga_id})
        messages.success(
            request,
            f"Data kendaraan dengan plat nomor <strong>{plat_nomor}</strong> berhasil dihapus.",
        )
        return redirect(base_url)
    else:
        return render(
            request=request,
            template_name="delete_kendaraan.html",
            context={
                "idkendaraan": idkendaraan,
                "kendaraan": kendaraan_record,
                "warga_id": warga_id,
            },
        )
