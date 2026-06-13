"""加密货币品种导入脚本"""

import asyncio

from sqlalchemy import select

from app.core.database import async_session
from app.models.orm.asset_variety_orm import AssetVarietyRecord

# name -> ticker
CRYPTOS: list[tuple[str, str]] = [
    ("Bitcoin", "BTC"),
    ("Ethereum", "ETH"),
    ("Dogecoin", "DOGE"),
    ("Litecoin", "LTC"),
    ("Shiba Inu", "SHIB"),
    ("0x Protocol", "ZRX"),
    ("Aave", "AAVE"),
    ("Aerodrome Finance", "AERO"),
    ("Algorand", "ALGO"),
    ("Arbitrum", "ARB"),
    ("Avalanche", "AVAX"),
    ("Axie Infinity", "AXS"),
    ("Basic Attention Token", "BAT"),
    ("Bio Protocol", "BIO"),
    ("Bitcoin Cash", "BCH"),
    ("BNB", "BNB"),
    ("BONK", "BONK"),
    ("Cardano", "ADA"),
    ("cat in a dogs world", "MEW"),
    ("Chainlink", "LINK"),
    ("Compound", "COMP"),
    ("Cosmos", "ATOM"),
    ("Curve DAO", "CRV"),
    ("Dogwifhat", "WIF"),
    ("Ethena", "ENA"),
    ("Ethereum Classic", "ETC"),
    ("Flare", "FLR"),
    ("Floki", "FLOKI"),
    ("Hedera", "HBAR"),
    ("Hyperliquid", "HYPE"),
    ("Immutable", "IMX"),
    ("Jito", "JTO"),
    ("LayerZero", "ZRO"),
    ("Lido DAO", "LDO"),
    ("Mantle", "MNT"),
    ("NEAR Protocol", "NEAR"),
    ("OFFICIAL TRUMP", "TRUMP"),
    ("Ondo", "ONDO"),
    ("Onyxcoin", "XCN"),
    ("Optimism", "OP"),
    ("Orca", "ORCA"),
    ("Pepecoin", "PEPE"),
    ("Polkadot", "DOT"),
    ("Popcat", "POPCAT"),
    ("Pudgy Penguins", "PENGU"),
    ("Pyth Network", "PYTH"),
    ("Quant", "QNT"),
    ("Raydium", "RAY"),
    ("Render", "RENDER"),
    ("SEI", "SEI"),
    ("Solana", "SOL"),
    ("Starknet", "STRK"),
    ("SUI", "SUI"),
    ("Stellar Lumens", "XLM"),
    ("Synthetix", "SNX"),
    ("Tezos", "XTZ"),
    ("The Graph", "GRT"),
    ("Toncoin", "TON"),
    ("Uniswap", "UNI"),
    ("USD Coin", "USDC"),
    ("Venice Token", "VVV"),
    ("Virtuals Protocol", "VIRTUAL"),
    ("Wormhole", "W"),
    ("XRP", "XRP"),
    ("Zcash", "ZEC"),
]


async def main():
    inserted = 0
    skipped = 0
    async with async_session() as session:
        for name, ticker in CRYPTOS:
            # 检查是否已存在
            existing = (await session.execute(
                select(AssetVarietyRecord).where(
                    AssetVarietyRecord.ticker == ticker,
                    AssetVarietyRecord.asset_class == "CRYPTO",
                    AssetVarietyRecord.market == "CRYPTO",
                )
            )).scalar_one_or_none()
            if existing:
                print(f"  [跳过] {ticker} ({name}) — 已存在")
                skipped += 1
                continue

            record = AssetVarietyRecord(
                ticker=ticker,
                name=name,
                market="CRYPTO",
                asset_class="CRYPTO",
                currency="USD",
            )
            session.add(record)
            inserted += 1
            print(f"  [新增] {ticker} ({name})")

        await session.commit()

    print(f"\n完成：新增 {inserted}，跳过 {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
