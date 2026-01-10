"""Price history service for collecting and storing historical stock prices."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import StockPrice
from app.services.kis_api import KISApiClient


class PriceHistoryError(Exception):
    pass


class PriceHistoryService:
    def __init__(self, db: AsyncSession, kis_client: KISApiClient | None = None) -> None:
        self.db = db
        self.kis_client = kis_client

    async def get_prices(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> list[StockPrice]:
        query = (
            select(StockPrice)
            .where(StockPrice.stock_code == stock_code)
            .where(StockPrice.trade_date >= start_date)
            .where(StockPrice.trade_date <= end_date)
            .order_by(StockPrice.trade_date)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_date(self, stock_code: str) -> date | None:
        query = (
            select(StockPrice.trade_date)
            .where(StockPrice.stock_code == stock_code)
            .order_by(StockPrice.trade_date.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        row = result.scalar_one_or_none()
        return row

    async def store_prices(self, prices: list[dict]) -> int:
        if not prices:
            return 0

        stored_count = 0
        for price_data in prices:
            stmt = (
                insert(StockPrice)
                .values(
                    stock_code=price_data["stock_code"],
                    trade_date=price_data["trade_date"],
                    open_price=price_data["open_price"],
                    high_price=price_data["high_price"],
                    low_price=price_data["low_price"],
                    close_price=price_data["close_price"],
                    volume=price_data["volume"],
                )
                .on_conflict_do_nothing(
                    index_elements=["stock_code", "trade_date"],
                )
            )
            result = await self.db.execute(stmt)
            if result.rowcount > 0:
                stored_count += 1

        await self.db.commit()
        return stored_count

    async def fetch_and_store(
        self,
        stock_code: str,
        days: int = 100,
    ) -> int:
        if self.kis_client is None:
            raise PriceHistoryError("KIS client not configured")

        daily_prices = await self.kis_client.get_daily_prices(stock_code, count=days)

        prices_to_store = []
        for item in daily_prices:
            date_str = str(item.get("date", ""))
            if len(date_str) == 8:
                trade_date = date(
                    int(date_str[:4]),
                    int(date_str[4:6]),
                    int(date_str[6:8]),
                )
            else:
                continue

            prices_to_store.append({
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": float(item.get("open", 0)),
                "high_price": float(item.get("high", 0)),
                "low_price": float(item.get("low", 0)),
                "close_price": float(item.get("close", 0)),
                "volume": int(item.get("volume", 0)),
            })

        return await self.store_prices(prices_to_store)

    async def sync_latest(self, stock_code: str) -> int:
        latest_date = await self.get_latest_date(stock_code)
        today = date.today()

        if latest_date is None:
            return await self.fetch_and_store(stock_code, days=365)

        days_since = (today - latest_date).days
        if days_since <= 1:
            return 0

        return await self.fetch_and_store(stock_code, days=min(days_since + 10, 365))

    async def get_price_dataframe(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        prices = await self.get_prices(stock_code, start_date, end_date)
        return [
            {
                "date": p.trade_date,
                "open": p.open_price,
                "high": p.high_price,
                "low": p.low_price,
                "close": p.close_price,
                "volume": p.volume,
            }
            for p in prices
        ]

    async def has_sufficient_data(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
        min_data_points: int = 20,
    ) -> bool:
        prices = await self.get_prices(stock_code, start_date, end_date)
        return len(prices) >= min_data_points

    async def fill_missing_dates(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> int:
        existing = await self.get_prices(stock_code, start_date, end_date)
        existing_dates = {p.trade_date for p in existing}

        if len(existing_dates) == 0:
            return await self.fetch_and_store(
                stock_code,
                days=(end_date - start_date).days + 10,
            )

        return 0
