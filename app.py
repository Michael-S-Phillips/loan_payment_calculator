"""
FastAPI backend for the Loan Payment Calculator web application.

Provides REST API endpoints for loan calculations and strategy comparison.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
import io
import logging
from loan_calculator import LoanCalculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Loan Payment Calculator API",
    description="REST API for comparing loan repayment strategies",
    version="1.0.0"
)

# Add CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class LoanData(BaseModel):
    """Represents a single loan."""
    loan_number: int
    lender_description: str
    loan_type: str
    term_months: int
    principal_balance: float
    min_monthly_payment: float
    annual_interest_rate: float


class CalculationRequest(BaseModel):
    """Request body for calculation endpoint."""
    loans: List[LoanData]
    max_monthly_payment: float = Field(..., gt=0, description="Maximum monthly payment budget")
    payment_case: int = Field(default=0, ge=0, le=1, description="0=fixed total, 1=fixed after interest")
    strategies: Optional[List[str]] = Field(
        default=None,
        description="List of strategy keys. None = all strategies"
    )


class StrategyResult(BaseModel):
    """Result for a single strategy."""
    strategy_name: str
    months_to_payoff: int
    total_cost: float
    total_interest: float


class CalculationResponse(BaseModel):
    """Response from calculation endpoint."""
    success: bool
    summary: List[StrategyResult]
    details: Optional[Dict] = None
    error: Optional[str] = None


class StrategyInfo(BaseModel):
    """Information about available strategies."""
    key: str
    name: str
    description: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Loan Payment Calculator API"
    }


@app.get("/api/strategies")
async def get_strategies():
    """Get list of available strategies."""
    calc = LoanCalculator()
    strategies = []

    for key, info in calc.STRATEGIES.items():
        strategies.append(StrategyInfo(
            key=key,
            name=info['name'],
            description=info['description']
        ))

    return strategies


@app.post("/api/calculate", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate loan payment strategies.

    Args:
        request: CalculationRequest with loans and settings

    Returns:
        CalculationResponse with results for all requested strategies
    """
    try:
        # Create calculator instance
        calc = LoanCalculator()

        # Convert loan data to DataFrame
        loan_dicts = [loan.model_dump() for loan in request.loans]
        df = pd.DataFrame(loan_dicts)

        # Rename columns to match expected format
        df = df.rename(columns={
            'loan_number': 'Loan Number',
            'lender_description': 'Lender/Description',
            'loan_type': 'Loan Type',
            'term_months': 'Term (months)',
            'principal_balance': 'Principal Balance',
            'min_monthly_payment': 'Minimum Monthly Payment',
            'annual_interest_rate': 'Annual Interest Rate (%)'
        })

        # Load data into calculator
        calc.loan_data = df

        # Validate data
        is_valid, error_msg = calc.validate_data()
        if not is_valid:
            raise ValueError(error_msg)

        # Run calculations
        logger.info(f"Running calculation with strategies: {request.strategies}")
        results = calc.calculate(
            max_monthly_payment=request.max_monthly_payment,
            payment_case=request.payment_case,
            strategies=request.strategies
        )

        # Build summary response
        summary = []
        for strategy_key, result in results.items():
            summary.append(StrategyResult(
                strategy_name=result['name'],
                months_to_payoff=result['months'],
                total_cost=result['total_cost'],
                total_interest=result['total_interest']
            ))

        # Build detailed results (payment tables converted to JSON-serializable format)
        details = {}
        for strategy_key, result in results.items():
            details[strategy_key] = {
                'name': result['name'],
                'months': result['months'],
                'monthly_payments': [float(x) for x in result['monthly_payments']],
                'interest_tally': [float(x) for x in result['interest_tally']],
                'total_cost': float(result['total_cost']),
                'total_interest': float(result['total_interest']),
                'payment_table': result['payment_table'].to_dict(orient='records')
            }

        logger.info("Calculation completed successfully")
        return CalculationResponse(
            success=True,
            summary=summary,
            details=details
        )

    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        return CalculationResponse(
            success=False,
            summary=[],
            error=str(e)
        )


@app.post("/api/calculate/from-file")
async def calculate_from_file(
    file: UploadFile = File(...),
    max_monthly_payment: float = None,
    payment_case: int = 0,
    strategies: Optional[str] = None  # JSON string of strategy list
):
    """
    Calculate from uploaded Excel/CSV file.

    Args:
        file: Excel or CSV file with loan data
        max_monthly_payment: Maximum monthly payment budget
        payment_case: Payment calculation mode
        strategies: JSON string of strategy list

    Returns:
        CalculationResponse with results
    """
    try:
        if max_monthly_payment is None or max_monthly_payment <= 0:
            raise ValueError("max_monthly_payment must be positive")

        # Read file
        content = await file.read()

        if file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
        elif file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise ValueError("File must be Excel or CSV format")

        # Create calculator and load data
        calc = LoanCalculator()
        calc.loan_data = df

        # Validate data
        is_valid, error_msg = calc.validate_data()
        if not is_valid:
            raise ValueError(error_msg)

        # Parse strategies if provided
        strategy_list = None
        if strategies:
            import json
            strategy_list = json.loads(strategies)

        # Run calculations
        logger.info(f"File upload calculation with {len(df)} loans")
        results = calc.calculate(
            max_monthly_payment=max_monthly_payment,
            payment_case=payment_case,
            strategies=strategy_list
        )

        # Build response
        summary = []
        for strategy_key, result in results.items():
            summary.append({
                'strategy_name': result['name'],
                'months_to_payoff': result['months'],
                'total_cost': float(result['total_cost']),
                'total_interest': float(result['total_interest'])
            })

        return {
            'success': True,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/template-columns")
async def get_template_columns():
    """Get expected column names for upload file."""
    return {
        'columns': [
            'Loan Number',
            'Lender/Description',
            'Loan Type',
            'Term (months)',
            'Principal Balance',
            'Minimum Monthly Payment',
            'Annual Interest Rate (%)'
        ],
        'example': {
            'Loan Number': 1,
            'Lender/Description': 'Student Loan A',
            'Loan Type': 'Federal',
            'Term (months)': 120,
            'Principal Balance': 25000,
            'Minimum Monthly Payment': 250,
            'Annual Interest Rate (%)': 4.5
        }
    }


# ============================================================================
# Application startup/shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Loan Payment Calculator API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Loan Payment Calculator API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
