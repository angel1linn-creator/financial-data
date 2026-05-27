from models import get_db_session, Project, FinancialData, Company

with get_db_session() as session:
    projects = session.query(Project).all()
    print(f"Total Projects: {len(projects)}")
    for p in projects:
        count = session.query(FinancialData).filter(FinancialData.project_id == p.id).count()
        print(f" - Project: {p.name} (ID: {p.id}), Records: {count}")
    
    companies = session.query(Company).all()
    print(f"Total Companies: {len(companies)}")
    for c in companies:
        print(f" - {c.ticker}: {c.name} ({c.industry_tag})")
