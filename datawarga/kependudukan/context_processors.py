from .version import VERSION


def app_version(request):
    return {"app_version": VERSION}
