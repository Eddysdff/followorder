from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import asyncio
import json
import logging
from datetime import datetime
import aiohttp
from typing import List, Dict


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='smart_wallet_tracker.log'
)

class SmartWalletTracker:
    def __init__(self):
        self.RPC_URL = "https://g.w.lavanet.xyz:443/gateway/solana/"
        self.client = AsyncClient(self.RPC_URL)
        
        self.SMART_WALLETS = [
            "99999"
        ]
        
        self.JUPITER_API = "https://price.jup.ag/v4"
        
        self.processed_signatures = set()

    async def get_token_info(self, token_address: str) -> Dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.JUPITER_API}/token/{token_address}") as response:
                    if response.status == 200:
                        return await response.json()
            return None
        except Exception as e:
            logging.error(f"获取代币信息失败: {str(e)}")
            return None

    async def analyze_transaction(self, tx_sig: str) -> Dict:
        try:
            tx = await self.client.get_transaction(tx_sig)
            if not tx.value:
                return None

            transaction_data = {
                "timestamp": datetime.fromtimestamp(tx.value.block_time).strftime('%Y-%m-%d %H:%M:%S'),
                "signature": tx_sig,
                "token_transfers": [],
                "sol_transfer": 0
            }

            for log in tx.value.transaction.meta.log_messages:
                if "Transfer" in log:
                    await self.parse_transfer_log(log, transaction_data)

            return transaction_data

        except Exception as e:
            logging.error(f"分析交易失败: {str(e)}")
            return None

    async def parse_transfer_log(self, log: str, transaction_data: Dict):
        try:
            if "Transfer" in log:
                token_info = {
                    "token_address": "从日志中解析",
                    "amount": "从日志中解析",
                    "direction": "in/out"
                }
                
                token_details = await self.get_token_info(token_info["token_address"])
                if token_details:
                    token_info.update(token_details)
                
                transaction_data["token_transfers"].append(token_info)

        except Exception as e:
            logging.error(f"解析转账日志失败: {str(e)}")

    async def monitor_wallet(self, wallet_address: str):
        try:
            while True:
                signatures = await self.client.get_signatures_for_address(
                    Pubkey.from_string(wallet_address),
                    limit=10
                )

                for sig in signatures.value:
                    if sig.signature not in self.processed_signatures:
                        tx_data = await self.analyze_transaction(sig.signature)
                        if tx_data and tx_data["token_transfers"]:
                            self.process_transaction(wallet_address, tx_data)
                        self.processed_signatures.add(sig.signature)

                await asyncio.sleep(1) 

        except Exception as e:
            logging.error(f"监控钱包失败 {wallet_address}: {str(e)}")

    def process_transaction(self, wallet_address: str, tx_data: Dict):
        try:
            # 打印交易信息
            print(f"\n🔍 发现新交易!")
            print(f"钱包地址: {wallet_address}")
            print(f"交易时间: {tx_data['timestamp']}")
            print(f"交易签名: {tx_data['signature']}")
            
            for transfer in tx_data["token_transfers"]:
                direction = "买入 ⬇️" if transfer["direction"] == "in" else "卖出 ⬆️"
                print(f"{direction} {transfer['amount']} {transfer.get('symbol', 'Unknown Token')}")
                if transfer.get("price"):
                    print(f"价格: ${transfer['price']}")
                    
            logging.info(f"新交易: {json.dumps(tx_data, indent=2)}")

        except Exception as e:
            logging.error(f"处理交易数据失败: {str(e)}")

    async def start_monitoring(self):
        print("开始监控智能钱包...")
        
        tasks = [self.monitor_wallet(wallet) for wallet in self.SMART_WALLETS]
        await asyncio.gather(*tasks)

async def main():
    tracker = SmartWalletTracker()
    try:
        await tracker.start_monitoring()
    except KeyboardInterrupt:
        print("监控已停止")
    except Exception as e:
        logging.error(f"主程序错误: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(main())
