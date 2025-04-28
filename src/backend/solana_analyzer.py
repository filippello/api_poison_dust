from typing import List, Dict, Set
import httpx
import asyncio
from dotenv import load_dotenv
import os
import traceback
from fastapi import FastAPI
from pydantic import BaseModel

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

class AddressRequest(BaseModel):
    addresses: Dict[str, str]

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

    async def check_address_similarity(self, target_address: str, addresses: Set[str], prefix_length: int = 4) -> Dict:
        similar_addresses = []
        target_prefix = target_address[:prefix_length]
        
        print(f"Buscando coincidencias para dirección {target_address} con prefijo {target_prefix}")
        
        # Primero encontramos todas las direcciones con el mismo prefijo
        for address in addresses:
            if address and address[:prefix_length] == target_prefix:
                similar_addresses.append(address)
        
        is_risky = len(similar_addresses) > 1
        risk_level = 0
        message = "No se detectaron riesgos"
        
        if is_risky:
            # Obtenemos el primer bloque para cada dirección similar
            block_times = {}
            for addr in similar_addresses:
                block_time = await self.get_first_block(addr)
                block_times[addr] = block_time
            
            # Encontramos la dirección original (la que apareció primero)
            original_address = min(block_times.items(), key=lambda x: x[1])[0]
            
            # Si la dirección objetivo no es la original, es riesgosa
            if target_address != original_address:
                risk_level = min(len(similar_addresses) * 20, 100)
                message = f"Dirección sospechosa: similar a {original_address} (dirección original)"
            else:
                is_risky = False
                message = "Dirección original detectada"
        
        return {
            "has_similar_addresses": is_risky,
            "similar_addresses": similar_addresses,
            "is_risky": is_risky,
            "risk_level": risk_level,
            "message": message,
            "original_address": original_address if is_risky else None
        }

    async def analyze_addresses(self, from_address: str, to_address: str) -> Dict:
        # Obtener datos para ambas direcciones
        from_transfers, from_txs = await asyncio.gather(
            self.get_account_transfers(from_address),
            self.get_account_transactions(from_address)
        )
        
        to_transfers, to_txs = await asyncio.gather(
            self.get_account_transfers(to_address),
            self.get_account_transactions(to_address)
        )
        
        # Extraer todas las direcciones relacionadas
        from_addresses = self.extract_addresses(from_transfers, from_txs)
        to_addresses = self.extract_addresses(to_transfers, to_txs)
        
        # Analizar similitudes y posible ataque Poisson
        similarity_analysis = await self.check_address_similarity(to_address, from_addresses)
        
        return {
            "risk_assessment": {
                "has_similar_addresses": similarity_analysis["is_risky"],
                "similar_addresses": similarity_analysis["similar_addresses"],
                "risk_level": similarity_analysis["risk_level"],
                "message": similarity_analysis["message"]
            },
            "details": {
                "from_address": {
                    "transfers": from_transfers,
                    "transactions": from_txs,
                    "related_addresses": list(from_addresses)
                },
                "to_address": {
                    "transfers": to_transfers,
                    "transactions": to_txs,
                    "related_addresses": list(to_addresses)
                }
            },
            "similar_addresses_found": similarity_analysis["similar_addresses"]
        }

    async def get_first_block(self, address: str) -> int:
        transfers = await self.get_account_transfers(address)
        if not transfers:
            return float('inf')  # Si no hay transferencias, retornamos infinito
        
        # Ordenamos por block_time ascendente y tomamos el primero
        sorted_transfers = sorted(transfers, key=lambda x: x.get('block_time', float('inf')))
        return sorted_transfers[0].get('block_time', float('inf'))

@app.post("/check-addresses")
async def check_addresses(request: AddressRequest):
    try:
        analyzer = SolanaAnalyzer()
        analysis_result = await analyzer.analyze_addresses(
            request.addresses["from_address"],
            request.addresses["to_address"]
        )
        return {
            "is_risky": analysis_result["risk_assessment"]["has_similar_addresses"],
            "details": analysis_result["details"],
            "similar_addresses": analysis_result["risk_assessment"]["similar_addresses"]
        }
    except Exception as e:
        return {
            "error": f"Error durante el análisis: {str(e)}",
            "traceback": traceback.format_exc()
        } 