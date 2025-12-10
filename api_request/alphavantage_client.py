import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import time
from config.settings import ALPHA_VANTAGE_API_KEY

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """
    주식정보제공 서비스인 alphavantage의 API에서 주식정보를 받는 client
    """
    BASE_URL="https://www.alphavantage.co/query"

    def __init__(self, api_key: str = ALPHA_VANTAGE_API_KEY, request_delay: float = 12.0):
        self.api_key = api_key
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            raise ValueError("Alpha Vantage API Key not found")
        
    def _make_request(self, params: Dict[str, str])-> Dict[str, Any]:
        """
        Alpha vantage에 대한 request를 만드는 함수. with rating limit

        Args:
            params (Dict[str, str]): Request parameters
            
        Returns:
            Dict[str, Any]: API response
        """

        #API key
        params["apikey"]=self.api_key

        #rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        #make request
        logger.info(f"Making request to alpha vantage: {params}")
        response = requests.get(self.BASE_URL, params=params)
        self.last_request_time = time.time()

        #Check for errors
        if response.status_code !=200:
            logger.error(f"Error {response.status_code} from Alpha Vantage: {response.text}")
            response.raise_for_status()

        #API data
        data = response.json()

        #Check for API error message
        if "Error Message" in data:
            error_message = data["Error Message"]
            logger.error(f"Alpha vantage error: {error_message}")
            raise ValueError(f"Alpha vantage error: {error_message}")
        
        if "Note" in data and "API call frequency" in data["Note"]:
            logger.warning(f"Alpha vantage rate limit warning: {data['Note']}")
        
        return data
    
    def get_stock_quote(self, symbol:str) -> Dict[str, Any]:
        """
        symbol별 실시간 주식 시세 
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Stock quote data
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }

        return self._make_request(params)

    def get_daily_stock_data(self, symbol: str, outputsize: str="compact") -> Dict[str, Any]:
        """
        주식 정보를 받는 함수
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            outputsize (str): "compact" for latest 100 datapoints, "full" for 20+ years of data
            
        Returns:
            Dict[str, Any]: Historical daily stock data
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        }
        return self._make_request(params)
    
    def get_weekly_stock_data(self, symbol:str) -> Dict[str, Any]:
        """
        Get Weekly stock price data for a specific symbol.
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            outputsize (str): "compact" for latest 100 datapoints, "full" for 20+ years of data
            
        Returns:
            Dict[str, Any]: Historical Weekly stock data
        """
        params = {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
        }
        return self._make_request(params)
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        회사 정보 및 재정적 정보
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Company overview data
        """
        params = {
            "function": "OVERVIEW",
            "symbol":symbol,
        }
        return self._make_request(params)
    
    def search_stocks(self, keywords:str) -> List[Dict[str, Any]]:
        """
        키워드에 대한 주식 검색
        Args:
            keywords (str): Search keywords
            
        Returns:
            List[Dict[str, str]]: List of matching stocks
        """
        params= {
            "function": "SYMBOL_SEARCH",
            "keywords":keywords,
        }
        response = self._make_request(params)
        return response.get("bestMatches", [])
    
    def get_sector_performance(self) -> Dict[str, Any]:
        """
        섹터 퍼포먼스
        
        Returns:
            Dict[str, Any]: Sector performance data
        """
        params = {
            "function": "SECTOR"
        }
        
        return self._make_request(params)
    
    def get_income_statement(self, symbol: str) -> Dict[str, Any]:
        """
        회사 손익계산서
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Income statement data
        """
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol
        }
        
        return self._make_request(params)
    
    def get_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """
        회사 대차대조표
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Balance sheet data
        """
        params = {
            "function": "BALANCE_SHEET",
            "symbol": symbol
        }
        
        return self._make_request(params)
    
    def get_cash_flow(self, symbol: str) -> Dict[str, Any]:
        """
        회사 현금흐름표
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Cash flow data
        """
        params = {
            "function": "CASH_FLOW",
            "symbol": symbol
        }
        
        return self._make_request(params)
    


        
