from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render

from .models import Dataset
from .services import fetch_and_store_characters

def download_dataset(request):
    if request.method == 'POST':
        try:
            fname = fetch_and_store_characters()
            return JsonResponse({'status': 'ok', 'file': fname})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)
    return JsonResponse({'detail': 'Method not allowed'}, status=405)

def view_dataset(request, pk):
    ds = get_object_or_404(Dataset, pk=pk)
    return render(request, 'dataset_detail.html', {'dataset': ds})

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        datasets = Dataset.objects.order_by('-download_date')
        ctx['datasets'] = [
            {
                'pk': ds.pk,
                'formatted_date': timezone.localtime(ds.download_date)
                    .strftime('%b. %-d, %Y, %-I:%M %p').lower()
            }
            for ds in datasets
        ]
        return ctx
