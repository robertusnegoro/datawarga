from typing import Optional
from django.db.models import QuerySet, Q
from django.contrib.auth.models import User
from kependudukan.models import Warga, Kompleks, UserPermission


def get_warga_by_id(idwarga: int) -> Warga:
    """Retrieve Warga by ID."""
    from django.shortcuts import get_object_or_404

    return get_object_or_404(Warga, pk=idwarga)


def check_user_permission_for_kompleks(user: User, kompleks: Kompleks) -> bool:
    """
    Check if the given user is allowed to access data for the specified kompleks.
    Returns True if allowed, False otherwise.
    """
    try:
        current_permission_group = UserPermission.objects.get(user=user)
        if str(current_permission_group.permission_group).lower() != "all":
            if kompleks.permission_group != current_permission_group.permission_group:
                return False
    except UserPermission.DoesNotExist:
        pass
    return True


def check_user_permission_for_warga(user: User, warga: Warga) -> bool:
    """
    Check if the given user is allowed to access data for the specified warga.
    """
    if warga.kompleks:
        return check_user_permission_for_kompleks(user, warga.kompleks)
    return True


def search_warga_queryset(
    queryset: QuerySet[Warga],
    search_keyword: str,
    include_kompleks_fields_in_general_search: bool = False,
) -> QuerySet[Warga]:
    """
    Applies search filters to a Warga queryset.
    If search_keyword contains "/", it filters by "blok/nomor".
    Otherwise, it searches nama_lengkap, nik, no_kk, and optionally blok and nomor.
    """
    if not search_keyword:
        return queryset

    search_keyword = str(search_keyword)

    if "/" in search_keyword:
        split_keyword = search_keyword.split("/")
        return queryset.filter(
            kompleks__blok__icontains=split_keyword[0].strip(),
            kompleks__nomor=split_keyword[1].strip(),
        )
    else:
        q_filter = (
            Q(nama_lengkap__icontains=search_keyword)
            | Q(nik__icontains=search_keyword)
            | Q(no_kk__icontains=search_keyword)
        )
        if include_kompleks_fields_in_general_search:
            q_filter |= Q(kompleks__blok__icontains=search_keyword)
            q_filter |= Q(kompleks__nomor__icontains=search_keyword)

        return queryset.filter(q_filter)


def get_anggota_keluarga(
    warga_or_kompleks_id, exclude_warga_id: Optional[int] = None
) -> list[Warga]:
    """
    Get all active members of a household (kompleks), excluding 'PINDAH' and 'MENINGGAL'.
    Optionally exclude a specific warga ID (e.g. to exclude the main person being viewed).
    Returns a sorted list of Warga based on family role.
    """
    queryset = Warga.objects.filter(kompleks_id=warga_or_kompleks_id).exclude(
        status_tinggal__in=["PINDAH", "MENINGGAL"]
    )

    if exclude_warga_id is not None:
        queryset = queryset.exclude(pk=exclude_warga_id)

    data_warga = list(queryset)
    role_order = {
        "SUAMI": 1,
        "ISTRI": 2,
        "ANAK": 3,
        "ORANG TUA": 4,
        "SAUDARA": 5,
        "LAINNYA": 6,
        "N/A": 7,
    }
    data_warga.sort(
        key=lambda w: (role_order.get(w.status_keluarga, 8), w.nama_lengkap)
    )
    return data_warga


def get_no_kk_for_kompleks(kompleks_id: int) -> str:
    """
    Finds the active No KK for a given kompleks by checking the kepala_keluarga
    or falling back to the first available No KK.
    """
    data_warga = get_anggota_keluarga(kompleks_id)
    no_kk = "-"

    for w in data_warga:
        if w.kepala_keluarga and w.no_kk:
            return w.no_kk

    if no_kk == "-" and data_warga:
        for w in data_warga:
            if w.no_kk:
                return w.no_kk

    return no_kk
