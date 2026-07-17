"""Slice 20b — 지갑(보유·현금) CRUD REST 표면 (admin 입력 지름길 대체).

모델 무변경 — 기존 WalletHolding(portfolio.models) + CashBalance(models_my) 위에
얇은 CRUD를 가산한다. cash upsert/delete는 서비스 헬퍼(my_container) 재사용,
Wallet 컨테이너 get-or-create만 신규(MVP: 사용자당 1개).

엔드포인트(전부 user 스코프 `wallet__user`, IsAuthenticated):
  GET/POST         wallet/holdings/          보유 목록 / 추가
  PATCH/DELETE     wallet/holdings/<uuid>/   보유 수정 / 삭제
  GET/PUT/DELETE   wallet/cash/              현금 목록 / 통화별 upsert / 통화별 삭제

Stock은 기존 등록 종목만 허용(보유 = 이미 아는 심볼) — AV 자동 생성 없음(hermetic).
통화는 WalletHolding에 필드 없음 → stock.currency 파생(모델 무변경).
"""

from __future__ import annotations

from decimal import Decimal

from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.portfolio.models import Wallet, WalletHolding
from apps.portfolio.models_my import CashBalance
from apps.portfolio.services import my_container as mc
from packages.shared.stocks.models import Stock


# ── 헬퍼 ──


def _get_or_create_wallet(user) -> Wallet:
    """사용자 기본 지갑(MVP: 1개). 없으면 생성."""
    wallet = Wallet.objects.filter(user=user).order_by("created_at").first()
    if wallet is None:
        wallet = Wallet.objects.create(user=user)
    return wallet


def _holding_payload(h: WalletHolding) -> dict:
    """보유 1행 봉투(통화는 stock.currency 파생)."""
    return {
        "id": str(h.id),
        "symbol": h.stock_id,
        "name": getattr(h.stock, "company_name", "") or getattr(h.stock, "name", "") or "",
        "currency": h.stock.currency,
        "shares": str(h.shares),
        "avg_cost": str(h.avg_cost),
        "first_bought_at": h.first_bought_at.isoformat() if h.first_bought_at else None,
        "acquisition_fx_rate": (
            str(h.acquisition_fx_rate) if h.acquisition_fx_rate is not None else None
        ),
        "investment_thesis": h.investment_thesis or "",
        "current_price": str(h.stock.real_time_price),
    }


def _cash_payload(c: CashBalance) -> dict:
    return {"currency": c.currency, "amount": str(c.amount)}


# ── 스키마 앵커 serializer ──


class HoldingCreateSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=20)
    shares = serializers.DecimalField(max_digits=14, decimal_places=4)
    avg_cost = serializers.DecimalField(max_digits=12, decimal_places=4)
    first_bought_at = serializers.DateField()
    investment_thesis = serializers.CharField(required=False, allow_blank=True)
    acquisition_fx_rate = serializers.DecimalField(
        max_digits=12, decimal_places=4, required=False, allow_null=True
    )


class HoldingUpdateSerializer(serializers.Serializer):
    shares = serializers.DecimalField(max_digits=14, decimal_places=4, required=False)
    avg_cost = serializers.DecimalField(max_digits=12, decimal_places=4, required=False)
    first_bought_at = serializers.DateField(required=False)
    investment_thesis = serializers.CharField(required=False, allow_blank=True)
    acquisition_fx_rate = serializers.DecimalField(
        max_digits=12, decimal_places=4, required=False, allow_null=True
    )


class CashUpsertSerializer(serializers.Serializer):
    currency = serializers.ChoiceField(choices=["USD", "KRW"])
    amount = serializers.DecimalField(max_digits=16, decimal_places=2)


# ── 보유(WalletHolding) ──


@extend_schema(methods=["GET"], responses={200: None}, tags=["portfolio-wallet"])
@extend_schema(methods=["POST"], request=HoldingCreateSerializer, responses={201: None}, tags=["portfolio-wallet"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def wallet_holdings(request: Request) -> Response:
    """보유 목록(GET) / 추가(POST). user 스코프 wallet__user."""
    if request.method == "GET":
        qs = (
            WalletHolding.objects.filter(wallet__user=request.user)
            .select_related("stock")
            .order_by("-created_at")
        )
        return Response({"holdings": [_holding_payload(h) for h in qs]})

    # POST
    ser = HoldingCreateSerializer(data=request.data)
    if not ser.is_valid():
        return Response({"errors": ser.errors}, status=400)
    data = ser.validated_data

    symbol = data["symbol"].upper()
    try:
        stock = Stock.objects.get(symbol=symbol)
    except Stock.DoesNotExist:
        return Response(
            {"errors": {"symbol": f"종목 '{symbol}'이 등록돼 있지 않습니다. 먼저 검색·등록하세요."}},
            status=400,
        )

    wallet = _get_or_create_wallet(request.user)
    if WalletHolding.objects.filter(wallet=wallet, stock=stock).exists():
        return Response(
            {"errors": {"symbol": f"'{symbol}'은 이미 보유 목록에 있습니다. 수정으로 변경하세요."}},
            status=400,
        )

    holding = WalletHolding.objects.create(
        wallet=wallet,
        stock=stock,
        shares=data["shares"],
        avg_cost=data["avg_cost"],
        first_bought_at=data["first_bought_at"],
        investment_thesis=data.get("investment_thesis", "") or "",
        acquisition_fx_rate=data.get("acquisition_fx_rate"),
    )
    return Response(_holding_payload(holding), status=201)


@extend_schema(methods=["PATCH"], request=HoldingUpdateSerializer, responses={200: None}, tags=["portfolio-wallet"])
@extend_schema(methods=["DELETE"], responses={204: None}, tags=["portfolio-wallet"])
@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def wallet_holding_detail(request: Request, pk) -> Response:
    """보유 수정(PATCH) / 삭제(DELETE). 타 user 미접근(wallet__user 스코프)."""
    holding = (
        WalletHolding.objects.filter(wallet__user=request.user, pk=pk)
        .select_related("stock")
        .first()
    )
    if holding is None:
        return Response({"detail": "보유 항목을 찾을 수 없습니다."}, status=404)

    if request.method == "DELETE":
        holding.delete()
        return Response(status=204)

    # PATCH
    ser = HoldingUpdateSerializer(data=request.data, partial=True)
    if not ser.is_valid():
        return Response({"errors": ser.errors}, status=400)
    data = ser.validated_data
    if not data:
        return Response({"detail": "수정할 필드가 없습니다."}, status=400)

    for field in ("shares", "avg_cost", "first_bought_at", "acquisition_fx_rate"):
        if field in data:
            setattr(holding, field, data[field])
    if "investment_thesis" in data:
        holding.investment_thesis = data["investment_thesis"] or ""
    holding.save()
    return Response(_holding_payload(holding))


# ── 현금(CashBalance) ──


@extend_schema(methods=["GET"], responses={200: None}, tags=["portfolio-wallet"])
@extend_schema(methods=["PUT"], request=CashUpsertSerializer, responses={200: None}, tags=["portfolio-wallet"])
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def wallet_cash(request: Request) -> Response:
    """현금 목록(GET) / 통화별 upsert(PUT) / 통화별 삭제(DELETE ?currency=)."""
    if request.method == "GET":
        qs = mc.get_cash_for_user(request.user).order_by("currency")
        return Response({"cash": [_cash_payload(c) for c in qs]})

    if request.method == "DELETE":
        currency = (request.query_params.get("currency") or "").upper()
        if currency not in ("USD", "KRW"):
            return Response({"detail": "currency=USD|KRW 쿼리 파라미터가 필요합니다."}, status=400)
        wallet = _get_or_create_wallet(request.user)
        mc.delete_cash_for_wallet(wallet, currency=currency)
        return Response(status=204)

    # PUT (upsert)
    ser = CashUpsertSerializer(data=request.data)
    if not ser.is_valid():
        return Response({"errors": ser.errors}, status=400)
    amount = ser.validated_data["amount"]
    if amount < Decimal("0"):
        return Response({"errors": {"amount": "현금은 0 이상이어야 합니다."}}, status=400)
    wallet = _get_or_create_wallet(request.user)
    cash = mc.upsert_cash_for_wallet(wallet, amount, currency=ser.validated_data["currency"])
    return Response(_cash_payload(cash))


urlpatterns = [
    path("wallet/holdings/", wallet_holdings, name="wallet_holdings"),
    path("wallet/holdings/<uuid:pk>/", wallet_holding_detail, name="wallet_holding_detail"),
    path("wallet/cash/", wallet_cash, name="wallet_cash"),
]
