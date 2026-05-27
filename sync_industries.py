from models import get_db_session, Company
from scraper import fetch_financial_data

def sync_industries():
    print("=== 開始同步資料庫中的產業類別 ===")
    with get_db_session() as session:
        companies = session.query(Company).all()
        for comp in companies:
            if comp.ticker == "TEST01": continue
            
            print(f"正在更新 {comp.ticker} ({comp.name})...")
            # 僅抓取基本資訊，不需要多年財報
            res = fetch_financial_data(comp.ticker, years=1)
            if res and "industry_tag" in res:
                old_tag = comp.industry_tag
                comp.industry_tag = res["industry_tag"]
                comp.name = res["name"] # 同步更新名稱
                print(f"  ✅ 更新成功: {old_tag} -> {comp.industry_tag}")
        session.commit()
    print("=== 同步完成 ===")

if __name__ == "__main__":
    sync_industries()
