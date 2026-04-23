from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum
from django.utils.timezone import now
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from django.db.models.functions import TruncDate, TruncMonth
from django.views.decorators.http import require_http_methods
from datetime import datetime
import json
import urllib.error
import urllib.request

from requests import request
from .models import Farmer, MilkEntry, FeedDeduction
from .assistant_fallback import generic_assistant_reply, local_farmer_reply
from django.shortcuts import redirect
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
import openpyxl
import random
from django.utils.timezone import now
from datetime import timedelta
from django.db.models.functions import TruncDate

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(date_str, "%B %d, %Y").date()
        except:
            return None

def dashboard(request):
    if not request.session.get('admin_logged_in'):
        return redirect('index')
    
    selected_date = request.GET.get('date')
    parsed_date = parse_date(selected_date) if selected_date else None

    if parsed_date:
        entries = MilkEntry.objects.filter(date__date=parsed_date)
    else:
        today = now().date()
        entries = MilkEntry.objects.filter(date__date=today)
        parsed_date = today

    total_milk = entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_earnings = entries.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_entries = entries.count()

    farmer_summary = entries.values('farmer__name').annotate(
        total_qty=Sum('quantity'),
        total_amt=Sum('total_amount')
    )

    # 📊 Graph Data (Daily & Monthly Earnings)
    thirty_days_ago = now().date() - timedelta(days=30)
    recent_entries = MilkEntry.objects.filter(date__date__gte=thirty_days_ago)
    
    daily_graph = recent_entries.annotate(day=TruncDate('date')).values('day').annotate(
        total_earning=Sum('total_amount')
    ).order_by('day')

    daily_labels = [item['day'].strftime('%d %b') for item in daily_graph if item['day']]
    daily_data = [float(item['total_earning'] or 0) for item in daily_graph]

    current_year = now().year
    year_entries = MilkEntry.objects.filter(date__year=current_year)
    monthly_graph = year_entries.annotate(month=TruncMonth('date')).values('month').annotate(
        total_earning=Sum('total_amount')
    ).order_by('month')

    monthly_labels = [item['month'].strftime('%b %Y') for item in monthly_graph if item['month']]
    monthly_data = [float(item['total_earning'] or 0) for item in monthly_graph]

    return render(request, 'dashboard.html', {
        'total_milk': total_milk,
        'total_earnings': total_earnings,
        'total_entries': total_entries,
        'farmer_summary': farmer_summary,
        'selected_date': parsed_date,
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
    })


def export_excel(request):
    selected_date = request.GET.get('date')
    parsed_date = parse_date(selected_date) if selected_date else None

    if parsed_date:
        entries = MilkEntry.objects.filter(date__date=parsed_date)
    else:
        today = now().date()
        entries = MilkEntry.objects.filter(date__date=today)

    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(["Farmer", "Quantity", "Fat", "Price/L", "Total", "Date"])

    for entry in entries:
        formatted_date = entry.date.strftime("%d-%m-%Y %H:%M") if entry.date else ""

        ws.append([
            entry.farmer.name,
            entry.quantity,
            entry.fat,
            entry.price_per_liter,
            entry.total_amount,
            formatted_date
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=milk_report.xlsx'

    wb.save(response)
    return response


def monthly_report(request):
    selected_month = request.GET.get('month')

    if selected_month:
        year, month = selected_month.split('-')
        entries = MilkEntry.objects.filter(date__year=year, date__month=month)
    else:
        today = now()
        entries = MilkEntry.objects.filter(date__year=today.year, date__month=today.month)
        selected_month = f"{today.year}-{str(today.month).zfill(2)}"

    total_milk = entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_earnings = entries.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    farmer_summary = entries.values('farmer__name').annotate(
        total_qty=Sum('quantity'),
        total_amt=Sum('total_amount')
    )

    return render(request, 'monthly_report.html', {
        'total_milk': total_milk,
        'total_earnings': total_earnings,
        'farmer_summary': farmer_summary,
        'selected_month': selected_month
    })


def scan_qr(request):
    if not request.session.get('admin_logged_in'):
        return redirect('index')
        
    return render(request, 'scan.html')

def generate_bill(request):
    if not request.session.get('admin_logged_in'):
        return redirect('index')

    farmer_id = request.GET.get('farmer_id')
    period = request.GET.get('period') # '10', '15', '30'
    
    farmer = get_object_or_404(Farmer, farmer_id=farmer_id)
    
    today = now().date()
    if period == '10':
        start_date = today - timedelta(days=10)
    elif period == '15':
        start_date = today - timedelta(days=15)
    elif period == '30':
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30) # default 1 month
        
    entries = MilkEntry.objects.filter(farmer=farmer, date__date__gte=start_date).order_by('date')
    feed_entries = FeedDeduction.objects.filter(farmer=farmer, date__date__gte=start_date).order_by('date')
    
    total_milk = entries.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_milk_amount = entries.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_feed_deduction = feed_entries.aggregate(Sum('amount'))['amount__sum'] or 0
    
    final_payable_amount = total_milk_amount - total_feed_deduction
    
    avg_fat = 0
    avg_snf = 0
    if entries.exists():
        total_fat = sum(e.fat * e.quantity for e in entries)
        total_snf = sum(e.snf * e.quantity for e in entries)
        avg_fat = round(total_fat / total_milk, 2) if total_milk > 0 else 0
        avg_snf = round(total_snf / total_milk, 2) if total_milk > 0 else 0
        
    return render(request, 'generate_bill.html', {
        'farmer': farmer,
        'entries': entries,
        'feed_entries': feed_entries,
        'period': period,
        'start_date': start_date,
        'end_date': today,
        'total_milk': total_milk,
        'total_milk_amount': total_milk_amount,
        'total_feed_deduction': total_feed_deduction,
        'final_payable_amount': final_payable_amount,
        'avg_fat': avg_fat,
        'avg_snf': avg_snf
    })


def get_farmer(request):
    farmer_id = request.GET.get('farmer_id')
    farmer = get_object_or_404(Farmer, farmer_id=farmer_id)

    last_entry = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'add_milk')
        
        if form_type == 'add_milk':
            quantity = float(request.POST.get('quantity'))
            fat = float(request.POST.get('fat'))
            snf = float(request.POST.get('snf', 8.5))
            milk_type = request.POST.get('milk_type')

            print("Milk Type:", milk_type)  # ✅ Debug

            # Price logic based on Fat & SNF chart simulation
            if milk_type == "cow":
                price_per_liter = round((fat * 5.0) + (snf * 2.5), 2)
            elif milk_type == "buffalo":
                price_per_liter = round((fat * 6.0) + (snf * 3.0), 2)
            else:
                price_per_liter = round((fat * 5.0) + (snf * 2.5), 2)

            total = round(quantity * price_per_liter, 2)

            last_entry = MilkEntry.objects.create(
                farmer=farmer,
                quantity=quantity,
                fat=fat,
                snf=snf,
                milk_type=milk_type,
                price_per_liter=price_per_liter,
                total_amount=total
            )
        elif form_type == 'add_feed':
            amount = float(request.POST.get('feed_amount'))
            description = request.POST.get('feed_description', 'Cattle Feed')
            FeedDeduction.objects.create(
                farmer=farmer,
                amount=amount,
                description=description
            )

    entries = MilkEntry.objects.filter(farmer=farmer).order_by('-date')

    return render(request, 'farmer_detail.html', {
        'farmer': farmer,
        'entries': entries,
        'last_entry': last_entry
    })

from django.contrib.auth.hashers import check_password

# ================= FARMER LOGIN =================
def farmer_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            farmer = Farmer.objects.get(username=username)

            if check_password(password, farmer.password):
                request.session['farmer_id'] = farmer.id
                return redirect('farmer_dashboard')
            else:
                return render(request, 'farmer_login.html', {'error': 'Invalid Password'})

        except Farmer.DoesNotExist:
            return render(request, 'farmer_login.html', {'error': 'User not found'})

    return render(request, 'farmer_login.html')


# ================= FARMER DASHBOARD =================
def farmer_dashboard(request):
    farmer_id = request.session.get('farmer_id')

    if not farmer_id:
        return redirect('farmer_login')

    farmer = Farmer.objects.get(id=farmer_id)

    entries = MilkEntry.objects.filter(farmer=farmer).order_by('-date')

    return render(request, 'farmer_dashboard.html', {
        'farmer': farmer,
        'entries': entries
    })


def _openai_chat_reply(message: str, lang: str) -> tuple[str | None, str | None]:
    """
    Call OpenAI-compatible chat API. Returns (reply, error_code) where error_code is set on failure.
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        return None, "not_configured"

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    base = getattr(settings, "OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"

    lang_note = (
        "The farmer may write in Marathi or English. Reply in the same language they used when possible."
        if lang == "mr"
        else "The farmer may write in English or Marathi. Reply in the same language they used when possible."
    )

    system = (
        "You are a helpful assistant for smallholder dairy farmers in India. "
        "Give practical, concise advice about milk collection, fat percentage, animal care, "
        "hygiene, cooperative payments, and common dairy questions. "
        "Do not give medical prescriptions for animals; suggest consulting a veterinarian when needed. "
        "Do not invent personal data about the user. "
        + lang_note
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": 1024,
        "temperature": 0.6,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None, "upstream_error"
    except urllib.error.URLError:
        return None, "network_error"

    try:
        reply = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return None, "bad_response"

    return reply, None


@require_http_methods(["POST"])
def farmer_assistant_chat(request):
    """JSON API: OpenAI when configured; otherwise built-in dairy Q&A (no API key required)."""
    if not request.session.get("farmer_id"):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "empty_message"}, status=400)
    if len(message) > 4000:
        return JsonResponse({"error": "message_too_long"}, status=400)

    lang = request.session.get("lang", "en")

    reply, err = _openai_chat_reply(message, lang)
    if reply:
        return JsonResponse({"reply": reply})

    local = local_farmer_reply(message, lang)
    if local:
        return JsonResponse({"reply": local})

    return JsonResponse({"reply": generic_assistant_reply(lang)})


# ================= LOGOUT =================
def farmer_logout(request):
    request.session.flush()
    return redirect('index')

#================== LANGUAGE SWITCHER =================

def change_language(request):
    current_lang = request.session.get('lang', 'en')

    if current_lang == 'en':
        request.session['lang'] = 'mr'
    else:
        request.session['lang'] = 'en'

    return redirect(request.META.get('HTTP_REFERER', '/'))





#================= MAIN LOGIN (ADMIN + FARMER) =================
def index(request):
    if request.method == "POST":
        role = request.POST.get("role")
        username = request.POST.get("username")
        password = request.POST.get("password")

        # ================= ADMIN LOGIN =================
        if role == "admin":
            user = authenticate(request, username=username, password=password)

            if user is not None:
                request.session['admin_logged_in'] = True
                return redirect('dashboard')
            else:
                return render(request, 'index.html', {'error': 'Invalid Admin Credentials'})

        # ================= FARMER LOGIN =================
        elif role == "farmer":
            try:
                farmer = Farmer.objects.get(username=username)

                from django.contrib.auth.hashers import check_password
                if check_password(password, farmer.password):
                    request.session['farmer_id'] = farmer.id
                    return redirect('farmer_dashboard')
                else:
                    return render(request, 'index.html', {'error': 'Invalid Farmer Password'})

            except Farmer.DoesNotExist:
                return render(request, 'index.html', {'error': 'Farmer not found'})

    return render(request, 'index.html')



# ================= FORGOT PASSWORD =================
def forgot_password(request):
    if request.method == "POST":
        username = request.POST.get("username")

        try:
            farmer = Farmer.objects.get(username=username)

            # Generate OTP
            otp = str(random.randint(100000, 999999))

            # ✅ STORE IN SESSION (IMPORTANT)
            request.session['reset_username'] = username
            request.session['reset_otp'] = otp

            print("Your OTP is:", otp)

            return redirect('verify_otp')

        except Farmer.DoesNotExist:
            return render(request, 'forgot_password.html', {'error': 'User not found'})

    return render(request, 'forgot_password.html')


# ================= VERIFY OTP =================
def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        # ✅ GET FROM SESSION
        saved_otp = request.session.get('reset_otp')

        if entered_otp == saved_otp:
            return redirect('reset_password')
        else:
            return render(request, 'verify_otp.html', {'error': 'Invalid OTP'})

    return render(request, 'verify_otp.html')

# ================= RESET PASSWORD =================
from django.contrib.auth.hashers import make_password

from django.contrib.auth.hashers import make_password

def reset_password(request):
    username = request.session.get('reset_username')

    if not username:
        return redirect('forgot_password')

    if request.method == "POST":
        new_password = request.POST.get("password")

        farmer = Farmer.objects.get(username=username)
        farmer.password = make_password(new_password)
        farmer.save()

        # Clear session
        request.session.pop('reset_otp', None)
        request.session.pop('reset_username', None)

        return redirect('index')

    return render(request, 'reset_password.html')