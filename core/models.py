from django.db import models


class SiteVisit(models.Model):
    id = models.BigAutoField(primary_key=True)
    path = models.CharField(max_length=255)
    session_key = models.CharField(max_length=64, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visited_at']

    def __str__(self):
        return f"{self.path} @ {self.visited_at:%Y-%m-%d %H:%M:%S}"


class HelpContact(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    contact_type = models.CharField(
        max_length=20,
        choices=(
            ('whatsapp', 'WhatsApp'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('other', 'Other'),
        ),
        default='whatsapp',
    )
    contact_value = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.contact_type})"


class HelpOption(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=120)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class ChatbotSetting(models.Model):
    id = models.BigAutoField(primary_key=True)
    greeting = models.CharField(max_length=255, default='Halo! Ada yang bisa kami bantu?')
    bubble_label = models.CharField(max_length=60, default='Butuh bantuan?')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Chatbot Setting'
        verbose_name_plural = 'Chatbot Settings'

    def __str__(self):
        return self.bubble_label
