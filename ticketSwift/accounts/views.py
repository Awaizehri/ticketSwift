from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from bookings.models import Order


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('shows:show_list')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('shows:show_list')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def order_history_view(request):
    orders = (
        Order.objects.filter(customer=request.user)
        .select_related('showtime__show')
        .prefetch_related('ticket_set__seat')
        .order_by('-created_at')
    )
    return render(request, 'accounts/order_history.html', {'orders': orders})
