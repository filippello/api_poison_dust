from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .solana_analyzer import SolanaAnalyzer
from typing import Optional

app = FastAPI()

class AddressCheck(BaseModel):
    from_address_check: str
    to_address_check: str

class RiskResponse(BaseModel):
    is_risky: bool
    risk_level: int
    message: str

@app.post("/check-addresses", response_model=RiskResponse)
async def check_addresses(addresses: AddressCheck):
    try:
        print(f"Analyzing addresses:")
        print(f"From: {addresses.from_address_check}")
        print(f"To: {addresses.to_address_check}")
        
        analyzer = SolanaAnalyzer()
        analysis_result = await analyzer.analyze_addresses(
            addresses.from_address_check,
            addresses.to_address_check
        )
        
        # Tomamos los valores del análisis detallado
        is_risky = analysis_result["risk_assessment"]["has_similar_addresses"]
        risk_level = analysis_result["risk_assessment"]["risk_level"]
        message = analysis_result["risk_assessment"]["message"]
        
        print(f"\nAnalysis result:")
        print(f"Is risky: {is_risky}")
        print(f"Risk level: {risk_level}")
        
        return RiskResponse(
            is_risky=is_risky,
            risk_level=risk_level,
            message=message
        )

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 