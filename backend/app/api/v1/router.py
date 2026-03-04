from fastapi import APIRouter

from app.api.v1 import ticker, market_data, analysis, wave_engine, hmm, prophet, xgboost, seasonality, news, cot

router = APIRouter()

router.include_router(ticker.router, prefix="/ticker", tags=["ticker"])
router.include_router(market_data.router, prefix="/data", tags=["market-data"])
router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
router.include_router(wave_engine.router, prefix="/wave-engine", tags=["wave-engine"])
router.include_router(hmm.router, prefix="/hmm", tags=["hmm"])
router.include_router(prophet.router, prefix="/prophet", tags=["prophet"])
router.include_router(xgboost.router, prefix="/xgboost", tags=["xgboost"])
router.include_router(seasonality.router, prefix="/seasonality", tags=["seasonality"])
router.include_router(news.router, prefix="/news", tags=["news"])
router.include_router(cot.router, prefix="/cot", tags=["cot"])
