import re
import hashlib
import logging
from django.core.cache import cache
from django.conf import settings
from django.core.cache.utils import make_key
from rest_framework.response import Response
from rest_framework import status

# 캐시 보안 로거 설정
cache_security_logger = logging.getLogger('stocks.cache.security')
cache_performance_logger = logging.getLogger('stocks.cache.performance')

class SecureStockCache:
    """
    ## 보안이 강화된 주식 데이터 캐싱 클래스
    # - 입력값 검증 및 sanitization
    # - 접근 로깅 및 모니터링
    # - 캐시 키 해싱으로 예측 불가능하게 만듦
    """
    
    # 허용되는 캐시 타입들 (화이트리스트)
    ALLOWED_CACHE_TYPES = {
        'overview', 'balance_sheet', 'income_statement', 
        'cash_flow', 'chart', 'daily_price', 'weekly_price'
    }
    
    # 캐시 타입별 최대 만료 시간 (보안상 제한)
    MAX_CACHE_TIMEOUTS = {
        'overview': 1800,        # 30분 최대
        'balance_sheet': 7200,   # 2시간 최대
        'income_statement': 7200,
        'cash_flow': 7200,
        'chart': 300,            # 5분 최대
        'daily_price': 300,
        'weekly_price': 600,
    }

    @staticmethod
    def validate_symbol(symbol):
        """
        ## 주식 심볼 검증 및 sanitization
        # - SQL Injection 방지
        # - XSS 방지  
        # - 형식 검증
        """
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        
        # 1. 길이 제한 (DoS 방지)
        if len(symbol) > 10:
            raise ValueError("Symbol too long")
        
        # 2. 허용된 문자만 (알파벳, 숫자, 하이픈, 점)
        if not re.match(r'^[A-Za-z0-9.-]+$', symbol):
            raise ValueError("Symbol contains invalid characters")
        
        # 3. 대문자로 통일
        clean_symbol = symbol.upper().strip()
        
        # 4. 추가 보안 검증 (일반적인 주식 심볼 패턴)
        if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', clean_symbol):
            cache_security_logger.warning(f"Unusual symbol pattern: {symbol}")
        
        return clean_symbol

    @staticmethod
    def validate_cache_type(cache_type):
        """
        ## 캐시 타입 검증
        # - 허용된 캐시 타입만 사용 가능
        """
        if cache_type not in SecureStockCache.ALLOWED_CACHE_TYPES:
            raise ValueError(f"Invalid cache type: {cache_type}")
        return cache_type

    @staticmethod
    def generate_secure_cache_key(cache_type, symbol, **params):
        """
        ## 보안 강화된 캐시 키 생성
        # - 해시를 사용하여 예측 불가능하게 만듦
        # - 파라미터들을 안전하게 포함
        """
        # 1. 입력값 검증
        clean_symbol = SecureStockCache.validate_symbol(symbol)
        clean_cache_type = SecureStockCache.validate_cache_type(cache_type)
        
        # 2. 파라미터 정리 (정렬하여 일관성 보장)
        param_str = ''.join(f"{k}:{v}" for k, v in sorted(params.items()))
        
        # 3. 해시 생성 (예측 불가능하게)
        base_string = f"{clean_cache_type}:{clean_symbol}:{param_str}"
        
        # 4. HMAC을 사용한 보안 해시 (있다면)
        if hasattr(settings, 'CACHE_SECRET_KEY'):
            import hmac
            hash_obj = hmac.new(
                settings.CACHE_SECRET_KEY.encode(),
                base_string.encode(),
                hashlib.sha256
            )
            secure_hash = hash_obj.hexdigest()[:16]  # 16자리로 축약
        else:
            # 기본 해시 (개발환경용)
            secure_hash = hashlib.md5(base_string.encode()).hexdigest()[:16]
        
        # 5. 최종 캐시 키 생성
        cache_key = f"stocks:{clean_cache_type}:{clean_symbol}:{secure_hash}"
        
        # 6. 접근 로그 기록
        cache_security_logger.info(f"Cache key generated: {cache_type} for {clean_symbol}")
        
        return cache_key

    @staticmethod
    def secure_cache_get(cache_type, symbol, **params):
        """
        ## 보안 강화된 캐시 조회
        # - 접근 로깅
        # - 에러 처리
        # - 성능 모니터링
        """
        try:
            # 1. 보안 캐시 키 생성
            cache_key = SecureStockCache.generate_secure_cache_key(
                cache_type, symbol, **params
            )
            
            # 2. 캐시에서 조회
            cached_data = cache.get(cache_key)
            
            # 3. 결과 로깅
            if cached_data:
                cache_performance_logger.info(f"Cache HIT: {cache_type} for {symbol}")
                return cached_data
            else:
                cache_performance_logger.info(f"Cache MISS: {cache_type} for {symbol}")
                return None
        
        except Exception as e:
            # 4. 에러 로깅 및 안전한 fallback
            cache_security_logger.error(f"Cache get error: {cache_type}, {symbol}, Error: {e}")
            return None

    @staticmethod
    def secure_cache_set(cache_type, symbol, data, timeout=None, **params):
        """
        ## 보안 강화된 캐시 저장
        # - 타임아웃 제한
        # - 데이터 검증
        # - 접근 로깅
        """
        try:
            # 1. 타임아웃 검증 및 제한
            max_timeout = SecureStockCache.MAX_CACHE_TIMEOUTS.get(cache_type, 300)
            if timeout is None or timeout > max_timeout:
                timeout = max_timeout
                cache_security_logger.warning(
                    f"Cache timeout limited to {max_timeout}s for {cache_type}"
                )
            
            # 2. 데이터 크기 제한 (DoS 방지)
            if len(str(data)) > 1024 * 1024:  # 1MB 제한
                cache_security_logger.error(f"Cache data too large for {cache_type}")
                return False
            
            # 3. 보안 캐시 키 생성
            cache_key = SecureStockCache.generate_secure_cache_key(
                cache_type, symbol, **params
            )
            
            # 4. 캐시에 저장
            success = cache.set(cache_key, data, timeout)
            
            # 5. 결과 로깅
            if success:
                cache_performance_logger.info(
                    f"Cache SET: {cache_type} for {symbol}, timeout: {timeout}s"
                )
            else:
                cache_security_logger.error(f"Cache set failed: {cache_type} for {symbol}")
            
            return success
        
        except Exception as e:
            # 6. 에러 로깅
            cache_security_logger.error(f"Cache set error: {cache_type}, {symbol}, Error: {e}")
            return False


# 데코레이터를 사용한 간편한 캐싱 적용
def secure_cached_api(cache_type, timeout=None):
    """
    ## API 메서드에 보안 캐싱을 적용하는 데코레이터
    # - 자동으로 보안 캐싱 적용
    # - 에러 처리 내장
    # - 성능 모니터링 자동화
    """
    def decorator(func):
        def wrapper(self, request, symbol):
            try:
                # 1. 파라미터 추출
                params = dict(request.GET.items())
                
                # 2. 캐시 조회 시도
                cached_data = SecureStockCache.secure_cache_get(
                    cache_type, symbol, **params
                )
                
                # 3. 캐시가 있으면 반환
                if cached_data:
                    return Response(cached_data, status=status.HTTP_200_OK)
                
                # 4. 캐시가 없으면 원본 함수 실행
                response = func(self, request, symbol)
                
                # 5. 성공적인 응답이면 캐시에 저장
                if response.status_code == status.HTTP_200_OK:
                    SecureStockCache.secure_cache_set(
                        cache_type, symbol, response.data, timeout, **params
                    )
                
                return response
                
            except ValueError as e:
                # 입력값 오류
                cache_security_logger.warning(f"Invalid input for {cache_type}: {e}")
                return Response({
                    'error': f'잘못된 요청입니다: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            except Exception as e:
                # 기타 오류 - 원본 함수로 fallback
                cache_security_logger.error(f"Caching error for {cache_type}: {e}")
                return func(self, request, symbol)
        
        return wrapper
    return decorator


# 사용 예시: 보안 강화된 API 뷰
class SecureStockBalanceSheetAPIView(APIView):
    """
    ## 보안 강화된 Balance Sheet API
    # - 데코레이터를 사용한 자동 보안 캐싱
    """
    
    @secure_cached_api(cache_type='balance_sheet', timeout=3600)
    def get(self, request, symbol):
        """
        ## 대차대조표 데이터 조회 (보안 캐싱 자동 적용)
        """
        # 기존 로직과 동일하지만 보안 캐싱이 자동으로 적용됨
        stock = get_object_or_404(Stock, symbol=symbol.upper())
        
        period = request.GET.get('period', 'annual').lower()
        limit = int(request.GET.get('limit', 5))
        
        balance_sheets = BalanceSheet.objects.filter(
            stock=stock,
            period_type=period
        ).order_by('-fiscal_year', '-fiscal_quarter')[:limit]
        
        serializer = BalanceSheetTabSerializer(balance_sheets, many=True)
        
        return Response({
            'symbol': symbol.upper(),
            'tab': 'balance_sheet',
            'period': period,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
