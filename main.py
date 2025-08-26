from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import math

app = FastAPI(
    title="Risk → Goal API",
    description="Calculates SIP required for a target using risk-based return assumptions and 7% inflation.",
    version="1.0.0",
)

# CORS (open for demo; you can restrict to your domain later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with ["https://yourdomain.com"] when live
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Core assumptions ---
INFLATION = 0.07  # 7% p.a.
RISK_RETURN = {
    "low": 0.105,       # 10.5%
    "moderate": 0.13,   # 13%
    "high": 0.155,      # 15.5%
}

def inflate_goal(present_value: float, years: int, inflation: float = INFLATION) -> float:
    """Future value of a goal after inflation."""
    return present_value * ((1 + inflation) ** years)

def sip_required(goal_fv: float, annual_return: float, years: int) -> float:
    """
    SIP PMT for target FV:
      PMT = FV * r / ((1+r)^n - 1)
    where r = monthly return, n = months
    """
    months = years * 12
    r = annual_return / 12.0
    if months <= 0 or r <= 0:
        return 0.0
    denom = (1 + r) ** months - 1
    return (goal_fv * r) / denom if denom != 0 else 0.0

def future_value_of_sip(pmt: float, annual_return: float, years: int) -> float:
    """FV of a monthly SIP: FV = PMT * [((1+r)^n - 1)/r]"""
    months = years * 12
    r = annual_return / 12.0
    if months <= 0 or r <= 0:
        return 0.0
    return pmt * (((1 + r) ** months - 1) / r)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/risk-to-goal")
def risk_to_goal(
    target_corpus: float = Query(..., gt=0, description="Goal in today's rupees, e.g. 1000000"),
    risk_level: Literal["low", "moderate", "high"] = Query(...),
    years: int = Query(..., gt=0, description="Time horizon in years"),
    inflation: float = Query(INFLATION, ge=0.0, le=0.2, description="Override if needed, default 7%"),
):
    """
    Returns inflation-adjusted target (FV) and required SIP using risk-based expected return.
    """
    annual_return = RISK_RETURN[risk_level]
    inflated_goal = inflate_goal(target_corpus, years, inflation)
    sip = sip_required(inflated_goal, annual_return, years)

    return {
        "inputs": {
            "target_corpus_today": round(target_corpus, 2),
            "risk_level": risk_level,
            "years": years,
            "assumed_inflation": inflation,
            "assumed_return": annual_return,
        },
        "outputs": {
            "inflation_adjusted_target_fv": round(inflated_goal, 0),
            "estimated_monthly_sip": round(sip, 0),
        }
    }

@app.get("/projected-corpus")
def projected_corpus(
    monthly_sip: float = Query(..., gt=0, description="Monthly SIP amount"),
    risk_level: Literal["low", "moderate", "high"] = Query(...),
    years: int = Query(..., gt=0),
):
    """
    Reverse calc: given SIP + years + risk level, what corpus could you reach (FV)?
    """
    annual_return = RISK_RETURN[risk_level]
    fv = future_value_of_sip(monthly_sip, annual_return, years)
    return {
        "inputs": {
            "monthly_sip": round(monthly_sip, 2),
            "risk_level": risk_level,
            "years": years,
            "assumed_return": annual_return,
        },
        "outputs": {
            "projected_corpus_fv": round(fv, 0)
        }
    }
