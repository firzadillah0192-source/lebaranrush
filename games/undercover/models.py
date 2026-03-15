from django.db import models

class UndercoverWord(models.Model):
    word_common = models.CharField(max_length=100)
    word_undercover = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.word_common} vs {self.word_undercover}"
