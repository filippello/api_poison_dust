from typing import List, Dict, Set
import httpx
import asyncio
from dotenv import load_dotenv
import os
import traceback
from fastapi import FastAPI
from pydantic import BaseModel
import json

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
        
        # Process all addresses and their first blocks
        address_first_blocks = {}
        print("\nProcessing initial blocks for all addresses:")
        
        # Procesar transferencias de from_address
        for transfer in from_transfers:
            for addr in [transfer.get('from_address'), transfer.get('to_address')]:
                if addr:
                    block_info = {
                        'block_id': transfer.get('block_id', float('inf')),
                        'block_time': transfer.get('block_time', float('inf')),
                        'transfer': transfer
                    }
                    if addr not in address_first_blocks or block_info['block_id'] < address_first_blocks[addr]['block_id']:
                        address_first_blocks[addr] = block_info
        
        # Procesar transferencias de to_address
        """ for transfer in to_transfers:
            for addr in [transfer.get('from_address'), transfer.get('to_address')]:
                if addr:
                    block_info = {
                        'block_id': transfer.get('block_id', float('inf')),
                        'block_time': transfer.get('block_time', float('inf')),
                        'transfer': transfer
                    }
                    if addr not in address_first_blocks or block_info['block_id'] < address_first_blocks[addr]['block_id']:
                        address_first_blocks[addr] = block_info """
        
        # Mostrar información de debug
        for addr, info in address_first_blocks.items():
            print(f"\nDirección: {addr}")
            print(f"Número de bloque: {info['block_id']}")
            print(f"Tiempo de bloque: {info['block_time']}")
            print(f"Detalles de la transferencia:")
            print(json.dumps(info['transfer'], indent=2))
        
        # Extraer todas las direcciones relacionadas
        from_addresses = self.extract_addresses(from_transfers, from_txs)
        to_addresses = self.extract_addresses(to_transfers, to_txs)
        
        # Analizar similitudes usando los bloques ya procesados
        similarity_analysis = await self.check_address_similarity(
            target_address=to_address,
            addresses=from_addresses,
            address_first_blocks=address_first_blocks
        )
        
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

    async def check_address_similarity(self, target_address: str, addresses: Set[str], address_first_blocks: Dict[str, Dict], prefix_length: int = 4) -> Dict:
        similar_addresses = []
        target_prefix = target_address[:prefix_length]
        
        print(f"\nLooking for matches for address {target_address} with prefix {target_prefix}")
        
        # Primero encontramos todas las direcciones con el mismo prefijo
        for address in addresses:
            if address and address[:prefix_length] == target_prefix:
                similar_addresses.append(address)
            
        is_risky = len(similar_addresses) > 1
        risk_level = 0
        message = "No risks detected"
        original_address = None
        
        if is_risky:
            print("\nAnalyzing blocks for similar addresses:")
            for addr in similar_addresses:
                if addr in address_first_blocks:
                    info = address_first_blocks[addr]
                    print(f"\nAddress: {addr}")
                    print(f"Block number: {info['block_id']}")
                    print(f"Block time: {info['block_time']}")
                    print(f"Transfer details:")
                    print(json.dumps(info['transfer'], indent=2))
            
            block_times = {addr: address_first_blocks[addr]['block_id'] 
                          for addr in similar_addresses 
                          if addr in address_first_blocks}
            
            if block_times:
                original_address = min(block_times.items(), key=lambda x: x[1])[0]
                print(f"\nOriginal address identified: {original_address}")
                print(f"Oldest block number: {block_times[original_address]}")
                
                if target_address != original_address:
                    risk_level = min(len(similar_addresses) * 20, 100)
                    message = f"Suspicious address: similar to {original_address} (original address)"
                    print(f"Alert! Target address is newer than the original")
                    
                    # Chequeo adicional de valor de transacción
                    original_info = address_first_blocks[original_address]
                    target_info = address_first_blocks[target_address]
                    
                    print("\nAnalyzing transaction values:")
                    print(f"Original transfer: {json.dumps(original_info['transfer'], indent=2)}")
                    print(f"Target transfer: {json.dumps(target_info['transfer'], indent=2)}")
                    
                    # SOL token check
                    if target_info['transfer']['token_address'] == "So11111111111111111111111111111111111111111":
                        target_value = float(target_info['transfer'].get('value', 0))
                        print(f"SOL transaction value: {target_value}")
                        if target_value < 0.001:
                            risk_level = 90
                            message += " - Low value SOL transaction"
                            print("Alert! Low value SOL transaction detected")
                    # Other tokens check
                    elif original_info['transfer']['token_address'] == target_info['transfer']['token_address']:
                        original_value = float(original_info['transfer'].get('value', 0))
                        target_value = float(target_info['transfer'].get('value', 0))
                        print(f"Comparing values - Original: {original_value}, Target: {target_value}")
                        if target_value * 5 < original_value:
                            risk_level = 90
                            message += f" - Significantly lower transaction value (Original: {original_value}, Current: {target_value})"
                            print(f"Alert! Significantly lower transaction value detected")
                else:
                    is_risky = False
                    message = "Original address detected"
                    print("Target address is the original one")
        
        return {
            "has_similar_addresses": is_risky,
            "similar_addresses": similar_addresses,
            "is_risky": is_risky,
            "risk_level": risk_level,
            "message": message,
            "original_address": original_address,
            "block_times": block_times if is_risky else {}
        }

    async def get_first_block(self, address: str) -> int:
        transfers = await self.get_account_transfers(address)
        print(f"\nAnalizing first transfers for {address}:")
        print(f"Total of transfers found: {len(transfers)}")
        
        if not transfers:
            print("No transfers found")
            return float('inf')
        
        # Ordenamos por block_time ascendente y tomamos el primero
        sorted_transfers = sorted(transfers, key=lambda x: x.get('block_time', float('inf')))
        first_block = sorted_transfers[0].get('block_time', float('inf'))
        
        print(f"First transfer found in block: {first_block}")
        print(f"Details of the first transfer: {sorted_transfers[0]}")
        
        return first_block

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
            "risk_level": analysis_result["risk_assessment"]["risk_level"],
            "details": analysis_result["details"],
            "similar_addresses": analysis_result["risk_assessment"]["similar_addresses"]
        }
    except Exception as e:
        return {
            "error": f"Error during analysis: {str(e)}",
            "traceback": traceback.format_exc()
        } 