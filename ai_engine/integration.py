
import json
from datetime import datetime
from typing import Dict, List, Any
from fraudguard_agent import FraudGuardAgent
from cashflow_oracle import CashflowOracle
from smartpayment_agent import SmartPaymentAgent


class MoneyFyiAI:
   
    
    def __init__(self):
        self.fraudguard = FraudGuardAgent()
        self.cashflow_oracle = CashflowOracle()
        self.smartpayment = SmartPaymentAgent()
    
    def analyze_full(
        self,
        transaction: Dict[str, Any],
        transaction_history: List[Dict[str, Any]],
        vendor_history: Dict[str, Any],
        current_balance: float
    ) -> Dict[str, Any]:
       
        print(" Starting MoneyFyi AI Analysis...")
        
        print("    Running fraud detection...")
        fraud_analysis = self.fraudguard.analyze_transaction(
            transaction,
            vendor_history,
            transaction_history
        )
        
        print("   Predicting cashflow...")
        cashflow_analysis = self.cashflow_oracle.predict(
            transaction_history,
            current_balance
        )
        
        print("   Generating payment recommendation...")
        payment_recommendation = self.smartpayment.recommend(
            transaction,
            fraud_analysis,
            cashflow_analysis,
            vendor_history
        )
        
        
        print("   Generating insights...")
        actionable_insights = self._generate_actionable_insights(
            fraud_analysis,
            cashflow_analysis,
            payment_recommendation
        )
        
        
        result = {
            "analysis_timestamp": datetime.now().isoformat(),
            "transaction_id": transaction.get('id', 'unknown'),
            "transaction_details": {
                "vendor": transaction.get('vendor'),
                "amount": transaction.get('amount'),
                "date": transaction.get('date'),
                "mode": transaction.get('mode', 'unknown')
            },
            "fraud_analysis": fraud_analysis,
            "cashflow_analysis": {
                "current_balance": cashflow_analysis['current_balance'],
                "cashflow_stress": cashflow_analysis['cashflow_stress'],
                "7_day_forecast": cashflow_analysis['7_day_forecast'][:7],  # Limit data
                "30_day_outlook": {
                    "trend": "positive" if cashflow_analysis['net_weekly_change'] > 0 else "negative",
                    "net_weekly_change": cashflow_analysis['net_weekly_change']
                },
                "risks": cashflow_analysis.get('risks', [])
            },
            "payment_recommendation": payment_recommendation,
            "actionable_insights": actionable_insights,
            "overall_risk_score": self._calculate_overall_risk(
                fraud_analysis,
                cashflow_analysis,
                payment_recommendation
            )
        }
        
        print("Analysis completed successfully")
        
        return result
    
    def analyze_batch(
        self,
        transactions: List[Dict[str, Any]],
        transaction_history: List[Dict[str, Any]],
        vendor_history: Dict[str, Any],
        current_balance: float
    ) -> Dict[str, Any]:
        
        print(f"Starting batch analysis of {len(transactions)} transactions...")
        
        results = []
        high_risk_count = 0
        total_flagged_amount = 0
        
        for i, txn in enumerate(transactions):
            print(f"  Analyzing transaction {i+1}/{len(transactions)}...")
            
            analysis = self.analyze_full(
                txn,
                transaction_history,
                vendor_history,
                current_balance
            )
            
            results.append(analysis)
            
            
            if analysis['overall_risk_score'] >= 70:
                high_risk_count += 1
                total_flagged_amount += txn.get('amount', 0)
        
        
        summary = {
            "total_analyzed": len(transactions),
            "high_risk_count": high_risk_count,
            "total_flagged_amount": total_flagged_amount,
            "recommendations": {
                "pay_full": sum(1 for r in results if r['payment_recommendation']['recommendation'] == 'PAY_FULL'),
                "pay_partially": sum(1 for r in results if r['payment_recommendation']['recommendation'] == 'PAY_PARTIALLY'),
                "avoid": sum(1 for r in results if r['payment_recommendation']['recommendation'] == 'AVOID')
            },
            "average_fraud_score": sum(r['fraud_analysis']['fraud_score'] for r in results) / len(results),
            "cashflow_status": results[0]['cashflow_analysis']['cashflow_stress'] if results else 'unknown'
        }
        
        return {
            "batch_summary": summary,
            "individual_analyses": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_actionable_insights(
        self,
        fraud: Dict,
        cashflow: Dict,
        payment: Dict
    ) -> List[str]:
        """Generate top-level actionable insights"""
        insights = []
        
        
        if fraud['risk_level'] == 'high':
            insights.append(" CRITICAL: High fraud risk detected - verify before any payment")
        
        if cashflow['cashflow_stress'] == 'high':
            insights.append(" URGENT: Cashflow critically low - prioritize only essential payments")
        
        
        recommendation = payment['recommendation']
        if recommendation == 'AVOID':
            insights.append(f"DO NOT PAY: Safety score {payment['payment_safety_score']}/100")
        elif recommendation == 'PAY_PARTIALLY':
            insights.append(f"PARTIAL PAYMENT ADVISED: Pay {payment['suggested_pct']}% (₹{payment['suggested_amount']:,.0f})")
        else:
            insights.append(f" SAFE TO PAY: All checks passed (score {payment['payment_safety_score']}/100)")
        
        # Fraud-specific insights
        if 'DUPLICATE_UTR' in fraud.get('flags', []):
            insights.append("DUPLICATE PAYMENT: This UTR has been used before")
        
        if 'NEW_VENDOR' in fraud.get('flags', []):
            insights.append(" NEW VENDOR: First transaction - verify vendor credentials")
        
        # Cashflow insights
        risks = cashflow.get('risks', [])
        if any(r['risk_type'] == 'NEGATIVE_BALANCE' for r in risks):
            insights.append(" WARNING: Predicted negative balance within 30 days")
        
        # General advice
        if cashflow['net_weekly_change'] < 0:
            insights.append(f"Negative cashflow: Review expenses to avoid shortfall")
        
        return insights
    
    def _calculate_overall_risk(
        self,
        fraud: Dict,
        cashflow: Dict,
        payment: Dict
    ) -> int:
        """Calculate overall risk score (0-100)"""
        # Weighted combination
        fraud_weight = 0.4
        cashflow_weight = 0.3
        payment_weight = 0.3
        
        fraud_score = fraud['fraud_score']
        
        # Convert cashflow stress to score
        cashflow_stress_map = {'low': 20, 'medium': 50, 'high': 80}
        cashflow_score = cashflow_stress_map.get(cashflow['cashflow_stress'], 50)
        
        # Invert payment safety score (higher safety = lower risk)
        payment_score = 100 - payment['payment_safety_score']
        
        overall = (
            fraud_score * fraud_weight +
            cashflow_score * cashflow_weight +
            payment_score * payment_weight
        )
        
        return int(overall)
    
    def export_for_backend(self, analysis: Dict) -> str:
        """Export analysis in JSON format for backend consumption"""
        return json.dumps(analysis, indent=2)
    
    def save_to_file(self, analysis: Dict, filename: str):
        """Save analysis to JSON file"""
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f" Analysis saved to {filename}")


def load_sample_data():
    """Load sample data for testing"""
    # Sample transaction to analyze
    transaction = {
        "id": "TXN_001",
        "vendor": "ABC Electronics Ltd",
        "amount": 45000,
        "date": "2025-11-15T14:30:00Z",
        "utr": "UTR987654321",
        "mode": "UPI",
        "type": "debit"
    }
    
    # Sample transaction history (last 3 months)
    transaction_history = [
        {"date": "2025-09-01", "amount": 50000, "type": "credit", "vendor": "Client A"},
        {"date": "2025-09-05", "amount": -12000, "type": "debit", "vendor": "Regular Supplier A"},
        {"date": "2025-09-10", "amount": -8000, "type": "debit", "vendor": "Regular Supplier B"},
        {"date": "2025-09-15", "amount": 60000, "type": "credit", "vendor": "Client B"},
        {"date": "2025-09-20", "amount": -15000, "type": "debit", "vendor": "Regular Supplier A"},
        {"date": "2025-10-01", "amount": 55000, "type": "credit", "vendor": "Client A"},
        {"date": "2025-10-05", "amount": -11000, "type": "debit", "vendor": "Regular Supplier A"},
        {"date": "2025-10-10", "amount": -9000, "type": "debit", "vendor": "Regular Supplier B"},
        {"date": "2025-10-15", "amount": 58000, "type": "credit", "vendor": "Client C"},
        {"date": "2025-11-01", "amount": 52000, "type": "credit", "vendor": "Client A"},
        {"date": "2025-11-05", "amount": -13000, "type": "debit", "vendor": "Regular Supplier A"},
        {"date": "2025-11-10", "amount": -11000, "type": "debit", "vendor": "Regular Supplier B"},
    ]
    
    # Sample vendor history
    vendor_history = {
        "Regular Supplier A": {
            "avg_amount": 12000,
            "frequency": 15,
            "trust_score": 90
        },
        "Regular Supplier B": {
            "avg_amount": 9000,
            "frequency": 10,
            "trust_score": 85
        },
        "ABC Electronics Ltd": {
            "avg_amount": 0,  # New vendor
            "frequency": 0,
            "trust_score": 50
        }
    }
    
    current_balance = 75000
    
    return transaction, transaction_history, vendor_history, current_balance


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("MONEYFYI AI - COMPLETE INTELLIGENCE ANALYSIS")
    print("=" * 70)
    
    # Initialize the AI system
    ai = MoneyFyiAI()
    
    # Load sample data
    transaction, history, vendors, balance = load_sample_data()
    
    # Run full analysis
    result = ai.analyze_full(
        transaction=transaction,
        transaction_history=history,
        vendor_history=vendors,
        current_balance=balance
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    
    print(f"\n Transaction: {result['transaction_details']['vendor']}")
    print(f" Amount: ₹{result['transaction_details']['amount']:,.0f}")
    print(f"\n Overall Risk Score: {result['overall_risk_score']}/100")
    print(f" Fraud Score: {result['fraud_analysis']['fraud_score']}/100 ({result['fraud_analysis']['risk_level']})")
    print(f" Cashflow Stress: {result['cashflow_analysis']['cashflow_stress'].upper()}")
    print(f" Recommendation: {result['payment_recommendation']['recommendation']}")
    
    print("\n KEY INSIGHTS:")
    for insight in result['actionable_insights']:
        print(f"  {insight}")
    
    # Save to file
    ai.save_to_file(result, "sample_analysis_output.json")
    
    print("\n" + "=" * 70)
    print(" Complete! Output saved to sample_analysis_output.json")
    print("=" * 70)