from kependudukan.forms import GenerateKompleksForm
from kependudukan.models import Warga, Kompleks, WargaPermissionGroup, UserPermission
from kependudukan.views.utility import helper_finance_year_list
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core import serializers
from django.db.models import Q, Count
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from kependudukan.utils.auth_guards import admin_or_petugas_required
import logging
import json

logger = logging.getLogger(__name__)


@user_passes_test(lambda u: u.is_superuser)
def kompleks_form(request):
    permission_group_data = WargaPermissionGroup.objects.all()
    context = {
        "rt": settings.RUKUNTANGGA,
        "rw": settings.RUKUNWARGA,
        "alamat": settings.ALAMAT,
        "kecamatan": settings.KECAMATAN,
        "kelurahan": settings.KELURAHAN,
        "kota": settings.KOTA,
        "provinsi": settings.PROVINSI,
        "permission_group": permission_group_data,
    }

    return render(request=request, template_name="form_kompleks.html", context=context)


@login_required
@admin_or_petugas_required
def generate_kompleks(request):
    if request.POST:
        form = GenerateKompleksForm(request.POST)

        if form.is_valid():
            cluster = str(request.POST["cluster"])
            blok = str(request.POST["blok"])
            rt = str(request.POST["rt"])
            rw = str(request.POST["rw"])
            start_num = int(request.POST["start_num"])
            finish_num = int(request.POST["finish_num"])
            alamat = str(request.POST["alamat"])
            kecamatan = str(request.POST["kecamatan"])
            kelurahan = str(request.POST["kelurahan"])
            kota = str(request.POST["kota"])
            provinsi = str(request.POST["provinsi"])
            kode_pos = str(request.POST["kode_pos"])
            permission_group = int(request.POST["permission_group"])

            total_num = finish_num - start_num

            if total_num > settings.GENERATE_KOMPLEKS_LIMIT:
                logger.error(
                    "user is trying to generate more than %s data kompleks rumah."
                    % (settings.GENERATE_KOMPLEKS_LIMIT)
                )
                return HttpResponse(
                    "Error. User seharusnya tidak mengenerate lebih dari %s nomor rumah."
                    % (settings.GENERATE_KOMPLEKS_LIMIT)
                )

            counter = start_num
            while counter <= finish_num:
                Kompleks.objects.create(
                    cluster=cluster,
                    blok=blok,
                    rt=rt,
                    rw=rw,
                    nomor=counter,
                    alamat=alamat,
                    kecamatan=kecamatan,
                    kelurahan=kelurahan,
                    kota=kota,
                    provinsi=provinsi,
                    kode_pos=kode_pos,
                    permission_group=WargaPermissionGroup.objects.get(
                        pk=permission_group
                    ),
                )
                logger.info("%s, %s, %s is saved to db" % (cluster, blok, counter))
                counter += 1
            messages.success(
                request,
                f"Data blok <strong>{blok}</strong> sebanyak <strong>{total_num}</strong> nomor rumah telah disimpan.",
            )
            return redirect(reverse("kependudukan:listKompleksView"))
        else:
            logger.info(form.errors)
            return HttpResponse("form is not valid %s" % (form.errors))
    else:
        return Http404()


@method_decorator(login_required, name="dispatch")
@method_decorator(admin_or_petugas_required, name="dispatch")
class KompleksListView(ListView):
    paginate_by = 50
    template_name = "list_kompleks_view.html"
    queryset = Kompleks.objects.order_by("-id").annotate(num_warga=Count("warga"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "search" in self.request.GET:
            context["search"] = str(self.request.GET["search"])
        return context

    def get_queryset(self):
        queryset = super().get_queryset()

        current_permission_group = UserPermission.objects.get(user=self.request.user)
        logger.info(current_permission_group.permission_group)

        if str(current_permission_group.permission_group).lower() != "all":
            queryset = queryset.filter(
                permission_group=current_permission_group.permission_group.id
            )

        if "search" in self.request.GET:
            search_keyword = str(self.request.GET["search"])

            if "/" in search_keyword:
                split_keyword = search_keyword.split("/")
                queryset = queryset.filter(
                    blok__icontains=split_keyword[0].strip(),
                    nomor=split_keyword[1].strip(),
                )
            else:
                queryset = queryset.filter(
                    Q(cluster__icontains=search_keyword)
                    | Q(blok__icontains=search_keyword)
                )
        return queryset


@login_required
@admin_or_petugas_required
def delete_blok_form(request):
    if request.POST:
        blok = str(request.POST["blok"])
        data_blok = Kompleks.objects.filter(blok=blok)
        jumlah_data = len(data_blok)
        if jumlah_data == 0:
            return HttpResponse("Tidak ada yang dihapus, klik back")
        data_blok.delete()
        messages.success(
            request,
            f"Data blok <strong>{blok}</strong> sebanyak <strong>{jumlah_data}</strong> nomor rumah telah dihapus.",
        )
        return redirect(reverse("kependudukan:listKompleksView"))
    else:
        return render(request=request, template_name="delete_blok_form.html")


@login_required
@admin_or_petugas_required
def detail_kompleks(request, idkompleks):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
    context = {}
    if request.POST:
        cluster = str(request.POST["cluster"])
        blok = str(request.POST["blok"])
        rt = str(request.POST["rt"])
        rw = str(request.POST["rw"])
        nomor = str(request.POST["nomor"])
        description = str(request.POST["description"])
        alamat = str(request.POST["alamat"])
        kecamatan = str(request.POST["kecamatan"])
        kelurahan = str(request.POST["kelurahan"])
        kota = str(request.POST["kota"])
        provinsi = str(request.POST["provinsi"])
        kode_pos = str(request.POST["kode_pos"])

        data_kompleks.cluster = cluster
        data_kompleks.blok = blok
        data_kompleks.rt = rt
        data_kompleks.rw = rw
        data_kompleks.nomor = nomor
        data_kompleks.description = description
        data_kompleks.alamat = alamat
        data_kompleks.kecamatan = kecamatan
        data_kompleks.kelurahan = kelurahan
        data_kompleks.kota = kota
        data_kompleks.provinsi = provinsi
        data_kompleks.kode_pos = kode_pos
        data_kompleks.save()

        messages.success(
            request,
            f"Data <strong>{blok}/{nomor}</strong> berhasil disimpan.",
        )

    context["data"] = data_kompleks
    context["load_url"] = reverse(
        "kependudukan:wargaRumah", kwargs={"idkompleks": idkompleks}
    )
    context["iuran_bulanan_url"] = reverse(
        "kependudukan:listIuranBulananJson", kwargs={"idkompleks": idkompleks}
    )

    context["iuran_year_period"] = helper_finance_year_list()
    return render(
        request=request, template_name="form_kompleks_detail.html", context=context
    )


@login_required
@admin_or_petugas_required
def warga_rumah(request, idkompleks):
    data_warga = Warga.objects.filter(kompleks=idkompleks).exclude(
        status_tinggal__in=["PINDAH", "MENINGGAL"]
    )
    total_warga = len(data_warga)
    data = serializers.serialize("json", data_warga)
    response = {"data": json.loads(data), "total": total_warga}
    return JsonResponse(response)


@login_required
@admin_or_petugas_required
def delete_rumah_form(request, idkompleks):
    data_kompleks = get_object_or_404(Kompleks, pk=idkompleks)
    context = {"data_kompleks": data_kompleks}
    if request.POST:
        logger.info(
            "Deleting data rumah with id : %s , data : %s" % (idkompleks, data_kompleks)
        )
        data_kompleks_str = str(data_kompleks)
        data_kompleks.delete()
        messages.success(
            request,
            f"Data rumah <strong>{data_kompleks_str}</strong> berhasil dihapus.",
        )
        return redirect(reverse("kependudukan:listKompleksView"))
    return render(
        request=request, template_name="delete_form_rumah.html", context=context
    )


@login_required
@admin_or_petugas_required
def list_kompleks_json(request):
    from django.db.models import Prefetch
    from kependudukan.selectors.kompleks_selector import search_kompleks_queryset

    # Active residents query
    active_warga = Warga.objects.exclude(
        status_tinggal__in=["PINDAH", "MENINGGAL"]
    ).only("id", "nama_lengkap", "status_keluarga", "kepala_keluarga")

    # Prefetch active residents and order complexes
    data_kompleks = Kompleks.objects.prefetch_related(
        Prefetch("warga_set", queryset=active_warga, to_attr="active_residents")
    ).order_by("blok", "nomor")

    # Filter complexes by user permission group
    try:
        current_permission_group = UserPermission.objects.get(user=request.user)
        if str(current_permission_group.permission_group).lower() != "all":
            data_kompleks = data_kompleks.filter(
                permission_group=current_permission_group.permission_group.id
            )
    except UserPermission.DoesNotExist:
        pass

    # Handle keyword search from POST or GET
    search_keyword = None
    if request.method == "POST":
        search_keyword = request.POST.get("kompleks_search_keyword")
    else:
        search_keyword = request.GET.get("kompleks_search_keyword")

    if search_keyword:
        data_kompleks = search_kompleks_queryset(data_kompleks, search_keyword)

    # Format output (maintaining backward compatibility)
    results = []
    for k in data_kompleks:
        residents = []
        for r in k.active_residents:
            residents.append(
                {
                    "id": r.id,
                    "nama_lengkap": r.nama_lengkap,
                    "status_keluarga": r.status_keluarga,
                    "kepala_keluarga": r.kepala_keluarga,
                }
            )
        results.append(
            {
                "pk": k.pk,
                "fields": {
                    "cluster": k.cluster or "",
                    "blok": k.blok or "",
                    "nomor": k.nomor or "",
                    "rt": k.rt or "",
                    "rw": k.rw or "",
                    "alamat": k.alamat or "",
                    "description": k.description or "",
                    "kecamatan": k.kecamatan or "",
                    "kelurahan": k.kelurahan or "",
                    "kode_pos": k.kode_pos or "",
                    "kota": k.kota or "",
                    "provinsi": k.provinsi or "",
                    "residents": residents,
                },
            }
        )

    return JsonResponse({"data": results})
