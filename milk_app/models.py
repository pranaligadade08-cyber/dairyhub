from django.db import models
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
from django.utils.timezone import now
from django.contrib.auth.hashers import make_password


class Farmer(models.Model):
    farmer_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    village = models.CharField(max_length=100)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    # OTP fields
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    # Login fields
    username = models.CharField(max_length=50, unique=True, blank=True)
    password = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # Step 1: Save first (to get ID)
        super().save(*args, **kwargs)

        # Step 2: Generate farmer_id
        if not self.farmer_id:
            self.farmer_id = f"FARMER_{self.id}"

        # Step 3: Generate login
        if not self.username:
            self.username = self.farmer_id
            self.password = make_password(self.mobile)

        # Step 4: Generate QR code
        if not self.qr_code:
            base = getattr(settings, "PUBLIC_SITE_URL", "http://127.0.0.1:8000").rstrip("/")
            qr_data = f"{base}/get-farmer/?farmer_id={self.farmer_id}"
            qr = qrcode.make(qr_data)

            buffer = BytesIO()
            qr.save(buffer, format='PNG')

            file_name = f"{self.farmer_id}.png"
            self.qr_code.save(file_name, File(buffer), save=False)

        # Step 5: Save again with updated fields
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


MILK_TYPE_CHOICES = [
    ('cow', 'Cow'),
    ('buffalo', 'Buffalo'),
]

class MilkEntry(models.Model):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE)
    
    milk_type = models.CharField(max_length=10, choices=MILK_TYPE_CHOICES, default='cow')  # ✅ NEW
    
    quantity = models.FloatField()
    fat = models.FloatField()
    snf = models.FloatField(default=8.5)
    price_per_liter = models.FloatField(default=30)
    total_amount = models.FloatField(blank=True, null=True)
    date = models.DateTimeField(default=now) 
    
    def save(self, *args, **kwargs):
        if not self.date:
            self.date = now()

        self.total_amount = round(self.quantity * self.price_per_liter, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.farmer.name} - {self.date}"

class FeedDeduction(models.Model):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE)
    amount = models.FloatField()
    description = models.CharField(max_length=255, default='Cattle Feed')
    date = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.farmer.name} - {self.amount} - {self.date}"