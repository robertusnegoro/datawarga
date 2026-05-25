from django.db.models import QuerySet, Q
from kependudukan.models import Kompleks


def search_kompleks_queryset(
    queryset: QuerySet[Kompleks], search_keyword: str
) -> QuerySet[Kompleks]:
    """
    Applies search filters to a Kompleks queryset.
    If search_keyword contains "/", it filters by exact "blok/nomor".
    Otherwise, it searches cluster or blok.
    """
    if not search_keyword:
        return queryset

    search_keyword = str(search_keyword)

    if "/" in search_keyword:
        split_keyword = search_keyword.split("/")
        return queryset.filter(
            blok__icontains=split_keyword[0].strip(),
            nomor=split_keyword[1].strip(),
        )
    else:
        return queryset.filter(
            Q(cluster__icontains=search_keyword) | Q(blok__icontains=search_keyword)
        )
