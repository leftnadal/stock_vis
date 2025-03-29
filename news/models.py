from django.db import models
from stocks.models import Stock

# Create your models here.

class NewsArticle(models.Model):

    # 주식
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='news')
    # 뉴스 제목
    title = models.CharField(max_length=200)
    # 뉴스 내용
    content = models.TextField()
    # 뉴스 출처 ( # 예: Reuters, Bloomberg, 네이버, etc.)
    source = models.CharField(max_length=50, blank=True, null=True)  
    # 뉴스 발행일
    published_at = models.DateTimeField()
    # 뉴스 url
    url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"[{self.stock.symbol}] {self.title}"