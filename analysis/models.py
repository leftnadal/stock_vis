from django.db import models

# Create your models here.

class EconomicIndicator(models.Model):
    # 경제지표 이름
    indicator_name = models.CharField(max_length=100)  # 예: "미국 기준금리", "GDP Growth"
    # 해당 지표 날짜
    date = models.DateField()
    # 해당 지표 값
    value = models.DecimalField(max_digits=10, decimal_places=4)
    # 지표 단위
    unit = models.CharField(max_length=50, blank=True, null=True)  # 예: %, USD, 등

    def __str__(self):
        return f"{self.indicator_name} - {self.date} = {self.value} {self.unit}"
   