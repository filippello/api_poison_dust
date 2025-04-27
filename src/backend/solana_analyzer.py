from typing import List, Dict, Set
import httpx
import asyncio
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

class SolanaAnalyzer:
    def __init__(self):
        self.api_token = os.getenv('SOLSCAN_API_TOKEN')
        if not self.api_token:
            raise ValueError("SOLSCAN_API_TOKEN no encontrado en variables de entorno")
        self.headers = {"token": self.api_token}
        self.base_url = "https://pro-api.solscan.io/v2.0"

    async def get_account_transfers(self, address: str) -> List[Dict]:
        url = f"{self.base_url}/account/transfer"
        params = {
            "page": 1,
            "page_size": 100,
            "sort_by": "block_time",
            "sort_order": "desc",
            "address": address
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            data = response.json()
            return data.get("data", [])

    async def get_account_transactions(self, address: str) -> List[Dict]:
        url = f"{self.base_url}/account/transactions"
        params = {
            "limit": 40,
            "address": address
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            data = response.json()
            return data.get("data", [])

    def extract_addresses(self, transfers: List[Dict], transactions: List[Dict]) -> Set[str]:
        addresses = set()
        
        # Log para transfers
        print("Transfers recibidos:", len(transfers))
        
        for transfer in transfers:
            from_addr = transfer.get("from_address")
            to_addr = transfer.get("to_address")
            print(f"Transfer encontrado - From: {from_addr}, To: {to_addr}")
            addresses.add(from_addr)
            addresses.add(to_addr)
        
        # Log para transactions
        print("Transactions recibidas:", len(transactions))
        
        for tx in transactions:
            signers = tx.get("signer", [])
            print(f"Signers encontrados en tx: {signers}")
            addresses.update(signers)
        
        # Log final de direcciones
        print("Total direcciones únicas encontradas:", len(addresses))
        addresses.discard(None)
        print("Contenido completo de addresses:", sorted(list(addresses)))
        return addresses

    def check_address_similarity(self, target_address: str, addresses: Set[str], prefix_length: int = 4) -> List[str]:
        similar_addresses = []
        target_prefix = target_address[:prefix_length]
        
        print(f"Buscando coincidencias para dirección {target_address} con prefijo {target_prefix}")
        
        for address in addresses:
            if address:  # Solo verificar que la dirección no sea None
                current_prefix = address[:prefix_length]
                if current_prefix == target_prefix or address == target_address:  # Incluir coincidencias exactas
                    print(f"Coincidencia encontrada: {address}")
                    similar_addresses.append(address)
        
        return similar_addresses

    async def analyze_addresses(self, from_address: str, to_address: str) -> Dict:
        # Obtener datos para from_address
        from_transfers, from_txs = await asyncio.gather(
            self.get_account_transfers(from_address),
            self.get_account_transactions(from_address)
        )
        
        # Obtener datos para to_address
        to_transfers, to_txs = await asyncio.gather(
            self.get_account_transfers(to_address),
            self.get_account_transactions(to_address)
        )

        # Extraer todas las direcciones relacionadas
        from_addresses = self.extract_addresses(from_transfers, from_txs)
        to_addresses = self.extract_addresses(to_transfers, to_txs)

        # Buscar direcciones similares
        similar_addresses = self.check_address_similarity(to_address, from_addresses)

        return {
            "from_address_data": {
                "transfers": from_transfers,
                "transactions": from_txs,
                "related_addresses": list(from_addresses)
            },
            "to_address_data": {
                "transfers": to_transfers,
                "transactions": to_txs,
                "related_addresses": list(to_addresses)
            },
            "similar_addresses_found": similar_addresses,
            "risk_assessment": {
                "has_similar_addresses": len(similar_addresses) > 0,
                "similar_addresses_count": len(similar_addresses)
            }
        } 