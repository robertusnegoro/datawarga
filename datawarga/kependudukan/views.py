from django.shortcuts import render
from .forms import WargaForm
import logging

logger = logging.getLogger(__name__)

# Create your views here.


def index(request):
    return render(request=request, template_name="index.html")


def formWarga(request):
    form = WargaForm()
    logger.info("Form warga empty loaded")
    return render(
        request=request,
        template_name="form.html",
        context={"form": form},
    )
