from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import math

app = FastAPI(
    title="Risk → Goal API",
    description="Calculates SIP/lumpsum required for a target using risk-based return assumptions and 7% inflation.",
    version="1.0.0",
)

# Allow frontend (Netlify) to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to your Netlify domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Assumptions ---
INFLATION = 0.07  # 7% p.a.
RISK_RETURN = {
    "low": 0.105,       # 10.5%
    "moderate": 0.13,   # 13%
    "high": 0.155,      # 15.5%
}

# --- Helper functions ---
def inflate_goal(pv: float, years: int, inflation: float = INFLATION) -> float:
    return pv * ((1 + inflation) ** years)

def sip_required(goal_fv: float, annual_return: float, years: int) -> float:
    months = years * 12
    r = annual_return / 12.0
    if months <= 0 or r <= 0:
        return 0.0
    return goal_fv * r / (((1 + r) ** months) - 1)

def fv_of_sip(pmt: float, annual_return: float, years: int) -> float:
    months = years * 12
    r = annual_return / 12.0
    if months <= 0 or r <= 0:
        return 0.0
    return pmt * (((1 + r) ** months - 1) / r)

def lumpsum_required(goal_fv: float, annual_return: float, years: int) -> float:
    return goal_fv / ((1 + annual_return) ** years)

def fv_of_lumpsum(pv: float, annual_return: float, years: int) -> float:
    return pv * ((1 + annual_return) ** years)

# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/risk-to-goal")
def risk_to_goal(
    target_corpus: float = Query(..., gt=0),
    risk_level: Literal["low","moderate","high"] = Query(...),
    years: int = Query(..., gt=0),
    inflation: float = INFLATION
):
    annual_return = RISK_RETURN[risk_level]
    inflated_goal = inflate_goal(target_corpus, years, inflation)
    sip = sip_required(inflated_goal, annual_return, years)
    lump = lumpsum_required(inflated_goal, annual_return, years)

    return {
        "inputs": {
            "target_today": target_corpus,
            "risk_level": risk_level,
            "years": years,
            "assumed_inflation": inflation,
            "assumed_return": annual_return,
        },
        "outputs": {
            "inflated_goal_fv": round(inflated_goal, 0),
            "required_sip": round(sip, 0),
            "required_lumpsum": round(lump, 0)
        }
    }

@app.get("/projected-sip")
def projected_sip(
    monthly_sip: float = Query(..., gt=0),
    risk_level: Literal["low","moderate","high"] = Query(...),
    years: int = Query(..., gt=0)
):
    annual_return = RISK_RETURN[risk_level]
    fv = fv_of_sip(monthly_sip, annual_return, years)
    return {"inputs": {"sip": monthly_sip,"risk": risk_level,"years": years},
            "outputs": {"projected_corpus": round(fv, 0)}}

@app.get("/projected-lumpsum")
def projected_lumpsum(
    lumpsum: float = Query(..., gt=0),
    risk_level: Literal["low","moderate","high"] = Query(...),
    years: int = Query(..., gt=0)
):
    annual_return = RISK_RETURN[risk_level]
    fv = fv_of_lumpsum(lumpsum, annual_return, years)
    return {"inputs": {"lumpsum": lumpsum,"risk": risk_level,"years": years},
            "outputs": {"projected_corpus": round(fv, 0)}}
