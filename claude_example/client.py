"""
Alpha Vantage API client for fetching stock data.
"""
import requests
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """
    Client for interacting with Alpha Vantage API to fetch various stock data.
    """
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str, request_delay: float = 12.0):
        """
        Initialize Alpha Vantage client.
        
        Args:
            api_key (str): Alpha Vantage API key
            request_delay (float): Delay between API requests in seconds to respect rate limits
                                  (Alpha Vantage free tier allows 5 requests per minute)
        """
        self.api_key = api_key
        self.request_delay = request_delay
        self.last_request_time = 0
        
    def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Make a request to Alpha Vantage API with rate limiting.
        
        Args:
            params (Dict[str, str]): Request parameters
            
        Returns:
            Dict[str, Any]: API response
        """
        # Add API key to parameters
        params["apikey"] = self.api_key
        
        # Respect rate limits
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Make the request
        logger.info(f"Making request to Alpha Vantage: {params}")
        response = requests.get(self.BASE_URL, params=params)
        self.last_request_time = time.time()
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"Error {response.status_code} from Alpha Vantage: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        
        # Check for API error messages
        if "Error Message" in data:
            error_message = data["Error Message"]
            logger.error(f"Alpha Vantage API error: {error_message}")
            raise ValueError(f"Alpha Vantage API error: {error_message}")
            
        if "Note" in data and "API call frequency" in data["Note"]:
            logger.warning(f"Alpha Vantage rate limit warning: {data['Note']}")
            
        return data
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time stock quote for a specific symbol.
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Stock quote data
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        return self._make_request(params)
        
    def get_daily_stock_data(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        """
        Get daily stock price data for a specific symbol.
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            outputsize (str): "compact" for latest 100 datapoints, "full" for 20+ years of data
            
        Returns:
            Dict[str, Any]: Historical daily stock data
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize
        }
        
        return self._make_request(params)
    
    def get_weekly_stock_data(self, symbol:str, outputsize: str = "compact") -> Dict[str, Any]:
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
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive company information and financial metrics.
        
        Args:
            symbol (str): Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict[str, Any]: Company overview data
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol
        }
        
        return self._make_request(params)
    
    def search_stocks(self, keywords: str) -> List[Dict[str, str]]:
        """
        Search for stocks by keywords.
        
        Args:
            keywords (str): Search keywords
            
        Returns:
            List[Dict[str, str]]: List of matching stocks
        """
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords
        }
        
        response = self._make_request(params)
        return response.get("bestMatches", [])

    
    def get_income_statement(self, symbol: str) -> Dict[str, Any]:
        """
        Get company's income statement data.
        
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
        Get company's balance sheet data.
        
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
        Get company's cash flow data.
        
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