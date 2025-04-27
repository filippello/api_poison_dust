from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .solana_analyzer import SolanaAnalyzer

app = FastAPI()

class AddressCheck(BaseModel):
    from_address_check: str
    to_address_check: str

class RiskResponse(BaseModel):
    is_risky: bool
    risk_level: int
    message: str
    analysis_data: dict

@app.post("/check-addresses", response_model=RiskResponse)
async def check_addresses(addresses: AddressCheck):
    try:
        print(f"Analizando direcciones:")
        print(f"From: {addresses.from_address_check}")
        print(f"To: {addresses.to_address_check}")
        
        analyzer = SolanaAnalyzer()
        analysis_result = await analyzer.analyze_addresses(
            addresses.from_address_check,
            addresses.to_address_check
        )
        
        is_risky = analysis_result["risk_assessment"]["has_similar_addresses"]
        risk_level = len(analysis_result["similar_addresses_found"]) * 20 if is_risky else 0
        
        print(f"Resultado del análisis:")
        print(f"Es riesgoso: {is_risky}")
        print(f"Nivel de riesgo: {risk_level}")
        print(f"Direcciones similares: {analysis_result['similar_addresses_found']}")
        
        return RiskResponse(
            is_risky=is_risky,
            risk_level=min(risk_level, 100),
            message="Se encontraron direcciones similares" if is_risky else "No se encontraron riesgos",
            analysis_data=analysis_result
        )

    except Exception as e:
        print(f"Error durante el análisis: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 