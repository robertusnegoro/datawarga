from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
import logging

from kependudukan.models import Warga, Surat, Penandatangan
from django import forms

logger = logging.getLogger(__name__)


class SuratForm(forms.ModelForm):
    class Meta:
        model = Surat
        fields = ["jenis_surat", "keperluan", "penandatangan"]
        widgets = {
            "jenis_surat": forms.Select(attrs={"class": "form-control"}),
            "keperluan": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "penandatangan": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super(SuratForm, self).__init__(*args, **kwargs)
        self.fields["penandatangan"].queryset = Penandatangan.objects.filter(aktif=True)
        self.fields["penandatangan"].required = True


@login_required
def form_surat(request, idwarga):
    warga = get_object_or_404(Warga, pk=idwarga)
    if request.method == "POST":
        form = SuratForm(request.POST)
        if form.is_valid():
            surat = form.save(commit=False)
            surat.warga = warga
            surat.save()
            messages.success(
                request,
                f"Surat <strong>{surat.get_jenis_surat_display()}</strong> untuk <strong>{warga.nama_lengkap}</strong> berhasil dibuat.",
            )
            return redirect(
                reverse("kependudukan:cetak_surat", kwargs={"idsurat": surat.id})
            )
    else:
        form = SuratForm()

    context = {
        "warga": warga,
        "form": form,
    }
    return render(request, "surat/form_surat.html", context)


@login_required
def cetak_surat(request, idsurat):
    surat = get_object_or_404(Surat, pk=idsurat)
    context = _prepare_surat_context(surat)
    return render(request, "surat/cetak_surat.html", context)


@login_required
def cetak_surat_pdf(request, idsurat):
    surat = get_object_or_404(Surat, pk=idsurat)
    context = _prepare_surat_context(surat)

    response = HttpResponse(content_type="application/pdf")
    safe_name = f"surat_{surat.jenis_surat.lower()}_{surat.warga.nama_lengkap.replace(' ', '_').lower()}.pdf"
    response["Content-Disposition"] = f"inline; filename={safe_name}"

    html = render_to_string("surat/cetak_surat.html", context, request=request)
    font_config = FontConfiguration()
    HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf(
        response, font_config=font_config
    )
    return response


@login_required
def list_surat(request):
    surat_list = Surat.objects.all().order_by("-tanggal_surat")
    context = {"surat_list": surat_list}
    return render(request, "surat/list_surat.html", context)


def format_tanggal_indo(date_obj):
    if not date_obj:
        return "-"
    indonesian_months = (
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember",
    )
    return f"{date_obj.day} {indonesian_months[date_obj.month - 1]} {date_obj.year}"


def _prepare_surat_context(surat):
    warga = surat.warga
    return {
        "surat": surat,
        "warga": warga,
        "kompleks": warga.kompleks,
        "penandatangan": surat.penandatangan,
        "warga_tanggal_lahir_indo": format_tanggal_indo(warga.tanggal_lahir),
        "surat_tanggal_surat_indo": format_tanggal_indo(surat.tanggal_surat),
        "rt": warga.kompleks.rt if warga.kompleks else settings.RUKUNTANGGA,
        "rw": warga.kompleks.rw if warga.kompleks else settings.RUKUNWARGA,
        "kelurahan": settings.KELURAHAN,
        "kecamatan": settings.KECAMATAN,
        "kota": settings.KOTA,
        "provinsi": settings.PROVINSI,
    }


@login_required
def delete_surat(request, idsurat):
    surat = get_object_or_404(Surat, pk=idsurat)
    warga_id = surat.warga.id
    jenis_display = surat.get_jenis_surat_display()
    warga_nama = surat.warga.nama_lengkap
    next_url = request.GET.get("next")

    if request.method == "POST":
        surat.delete()
        logger.info(
            "Deleting data surat with id : %s , jenis : %s , warga : %s"
            % (idsurat, jenis_display, warga_nama)
        )
        messages.success(
            request,
            f"Surat <strong>{jenis_display}</strong> untuk <strong>{warga_nama}</strong> berhasil dihapus.",
        )
        if next_url == "list_surat":
            return redirect(reverse("kependudukan:list_surat"))
        return redirect(
            reverse("kependudukan:detailWarga", kwargs={"idwarga": warga_id})
        )

    context = {
        "surat": surat,
        "warga_id": warga_id,
        "next": next_url,
    }
    return render(request, "surat/delete_surat.html", context)
