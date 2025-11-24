import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class StockPriceConsumer(AsyncWebsocketConsumer):
    """개별 주식 실시간 가격 WebSocket Consumer"""

    async def connect(self):
        """WebSocket 연결 시 처리"""
        self.symbol = self.scope['url_route']['kwargs']['symbol'].upper()
        self.room_group_name = f'stock_{self.symbol}'

        # 채널 레이어에 그룹 추가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for stock: {self.symbol}")

        # 연결 시 현재 가격 전송
        await self.send_current_price()

    async def disconnect(self, close_code):
        """WebSocket 연결 해제 시 처리"""
        # 채널 레이어에서 그룹 제거
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected for stock: {self.symbol}")

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신 시 처리"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'subscribe':
                # 구독 처리
                await self.send_current_price()
            elif message_type == 'ping':
                # 연결 유지용 ping 응답
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def price_update(self, event):
        """그룹으로부터 가격 업데이트 수신 시 클라이언트에 전송"""
        await self.send(text_data=json.dumps({
            'type': 'price_update',
            'symbol': event['symbol'],
            'price': event['price'],
            'change': event['change'],
            'change_percent': event['change_percent'],
            'timestamp': event['timestamp'],
            'volume': event.get('volume'),
            'high': event.get('high'),
            'low': event.get('low')
        }))

    @database_sync_to_async
    def get_stock_data(self):
        """데이터베이스에서 주식 데이터 조회"""
        try:
            from .models import Stock
            stock = Stock.objects.get(symbol=self.symbol)
            return {
                'symbol': stock.symbol,
                'name': stock.name,
                'price': str(stock.real_time_price) if stock.real_time_price else None,
                'change': str(stock.change) if stock.change else None,
                'change_percent': str(stock.change_percent) if stock.change_percent else None,
                'volume': stock.volume,
                'high': str(stock.day_high) if stock.day_high else None,
                'low': str(stock.day_low) if stock.day_low else None,
            }
        except Exception as e:
            logger.error(f"Error getting stock data for {self.symbol}: {e}")
            return None

    async def send_current_price(self):
        """현재 가격 정보 전송"""
        stock_data = await self.get_stock_data()
        if stock_data:
            await self.send(text_data=json.dumps({
                'type': 'current_price',
                **stock_data
            }))


class PortfolioConsumer(AsyncWebsocketConsumer):
    """포트폴리오 실시간 업데이트 WebSocket Consumer"""

    async def connect(self):
        """WebSocket 연결 시 처리"""
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            # 인증되지 않은 사용자는 연결 거부
            await self.close()
            return

        self.room_group_name = f'portfolio_{self.user.id}'

        # 채널 레이어에 그룹 추가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for portfolio: user {self.user.username}")

        # 연결 시 현재 포트폴리오 정보 전송
        await self.send_portfolio_summary()

    async def disconnect(self, close_code):
        """WebSocket 연결 해제 시 처리"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for portfolio: user {self.user.username}")

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신 시 처리"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'refresh':
                # 포트폴리오 새로고침 요청
                await self.send_portfolio_summary()
            elif message_type == 'ping':
                # 연결 유지용 ping 응답
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def portfolio_update(self, event):
        """포트폴리오 업데이트 이벤트 처리"""
        await self.send(text_data=json.dumps({
            'type': 'portfolio_update',
            'total_value': event['total_value'],
            'total_cost': event['total_cost'],
            'profit_loss': event['profit_loss'],
            'profit_loss_percentage': event['profit_loss_percentage'],
            'timestamp': event['timestamp'],
            'portfolios': event.get('portfolios', [])
        }))

    @database_sync_to_async
    def get_portfolio_data(self):
        """사용자 포트폴리오 데이터 조회"""
        try:
            from users.models import Portfolio
            from decimal import Decimal

            portfolios = Portfolio.objects.filter(
                user=self.user
            ).select_related('stock')

            total_value = Decimal('0')
            total_cost = Decimal('0')
            portfolio_list = []

            for portfolio in portfolios:
                current_price = portfolio.stock.real_time_price or Decimal('0')
                value = current_price * portfolio.quantity
                cost = portfolio.average_price * portfolio.quantity

                total_value += value
                total_cost += cost

                portfolio_list.append({
                    'symbol': portfolio.stock.symbol,
                    'name': portfolio.stock.name,
                    'quantity': str(portfolio.quantity),
                    'average_price': str(portfolio.average_price),
                    'current_price': str(current_price),
                    'value': str(value),
                    'cost': str(cost),
                    'profit_loss': str(value - cost),
                    'profit_loss_percentage': str(
                        ((value - cost) / cost * 100) if cost > 0 else 0
                    )
                })

            return {
                'total_value': str(total_value),
                'total_cost': str(total_cost),
                'profit_loss': str(total_value - total_cost),
                'profit_loss_percentage': str(
                    ((total_value - total_cost) / total_cost * 100)
                    if total_cost > 0 else 0
                ),
                'portfolios': portfolio_list
            }

        except Exception as e:
            logger.error(f"Error getting portfolio data for user {self.user.id}: {e}")
            return None

    async def send_portfolio_summary(self):
        """포트폴리오 요약 정보 전송"""
        portfolio_data = await self.get_portfolio_data()
        if portfolio_data:
            await self.send(text_data=json.dumps({
                'type': 'portfolio_summary',
                **portfolio_data
            }))