from django.contrib import admin
from django.utils.html import format_html

from .models import Farmer, MilkEntry


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    """Admins add farmers here; Farmer ID, login, and QR are created on first save."""

    list_display = ("farmer_id", "name", "mobile", "village", "qr_list_thumb")
    list_filter = ("village",)
    search_fields = ("name", "mobile", "farmer_id", "username")
    ordering = ("-id",)
    exclude = ("qr_code", "password", "otp", "otp_created_at")

    def get_fieldsets(self, request, obj=None):
        add_help = (
            "Save to generate Farmer ID, QR code, and login. "
            "Username will match the Farmer ID; the password is derived from the mobile number."
        )
        if obj is None:
            return (
                (
                    "Add farmer",
                    {
                        "fields": ("name", "mobile", "village"),
                        "description": add_help,
                    },
                ),
            )
        return (
            ("Farmer", {"fields": ("name", "mobile", "village")}),
            (
                "Farmer ID, login & QR",
                {
                    "fields": ("farmer_id", "username", "qr_panel"),
                    "description": "Give the farmer their ID and QR for scanning at milk collection.",
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("farmer_id", "username", "qr_panel")
        return ()

    @admin.display(description="QR")
    def qr_list_thumb(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="44" height="44" alt="" style="object-fit:contain" />',
                obj.qr_code.url,
            )
        return "—"

    @admin.display(description="QR code & Farmer ID")
    def qr_panel(self, obj):
        if not obj.pk:
            return "—"
        fid = obj.farmer_id or "(save to assign)"
        if obj.qr_code:
            return format_html(
                '<div style="max-width:320px">'
                "<p><strong>Farmer ID:</strong> "
                '<code style="font-size:1.15em;padding:2px 6px;background:#f0f0f0">{}</code></p>'
                '<p><img src="{}" alt="Farmer QR" style="max-width:280px;height:auto;'
                'border:1px solid #ccc;padding:10px;background:#fff" /></p>'
                '<p><a href="{}" download="farmer_{}.png">Download QR image</a></p>'
                "</div>",
                fid,
                obj.qr_code.url,
                obj.qr_code.url,
                fid,
            )
        return format_html(
            '<p><strong>Farmer ID:</strong> <code>{}</code></p>'
            "<p>QR not generated yet — click <strong>Save</strong> again.</p>",
            fid,
        )


@admin.register(MilkEntry)
class MilkEntryAdmin(admin.ModelAdmin):
    list_display = ("farmer", "milk_type", "quantity", "fat", "price_per_liter", "total_amount", "date")
    list_filter = ("date", "milk_type")
    search_fields = ("farmer__name", "farmer__farmer_id")
    autocomplete_fields = ("farmer",)


admin.site.site_header = "Dairy administration"
admin.site.site_title = "Dairy admin"
admin.site.index_title = "Manage farmers and milk entries"
