from models import get_db_session, FinancialData

with get_db_session() as session:
    tp_count = session.query(FinancialData).filter(
        FinancialData.project_id == 1, 
        FinancialData.is_tested_party == True
    ).count()
    print(f"Project 1 Tested Party Records: {tp_count}")
