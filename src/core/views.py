from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render

from .models import Dataset
from .services import load_dataset_preview, fetch_and_store_characters


def download_dataset(request):
    if request.method == "POST":
        try:
            fname = fetch_and_store_characters()
            return JsonResponse({"status": "ok", "file": fname})
        except Exception as e:
            return JsonResponse({"status": "error", "msg": str(e)}, status=500)
    return JsonResponse({"detail": "Method not allowed"}, status=405)


def view_dataset(request, pk):
    ds = get_object_or_404(Dataset, pk=pk)
    data = load_dataset_preview(ds.filename, offset=0, limit=10)

    if data:
        num_cols = len(data[0].keys())
        col_width = 100 / num_cols
    else:
        col_width = 0

    return render(
        request,
        "detail.html",
        {
            "dataset": ds,
            "data": data,
            "col_width": col_width,
        },
    )


def load_more_rows(request, pk):
    ds = get_object_or_404(Dataset, pk=pk)
    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0
    rows = load_dataset_preview(ds.filename, offset=offset, limit=10)
    return JsonResponse({"rows": rows})


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        datasets = Dataset.objects.order_by("-download_date")
        ctx["datasets"] = [
            {
                "pk": ds.pk,
                "formatted_date": timezone.localtime(ds.download_date)
                .strftime("%b. %-d, %Y, %-I:%M %p")
                .lower(),
            }
            for ds in datasets
        ]
        return ctx
