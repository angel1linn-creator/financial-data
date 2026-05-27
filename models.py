import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from contextlib import contextmanager

# 資料庫檔案路徑，預設儲存在專案目錄下
DATABASE_URL = "sqlite:///tp_analysis.db"

# 建立 SQLAlchemy 引擎
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # 允許 Streamlit 的多執行緒安全存取 SQLite
)

# 建立 Session 類別
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立宣告式基底類別
Base = declarative_base()


class Project(Base):
    """
    專案基本資訊表
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    # 建立與財務數據的一對多關聯
    financial_records = relationship("FinancialData", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class Company(Base):
    """
    公司基本資訊與產業分類表
    """
    __tablename__ = "companies"

    ticker = Column(String, primary_key=True, index=True)  # 股票代號，例如 "2330"、"2382"
    name = Column(String, nullable=False)                 # 公司簡稱，例如 "台積電"
    industry_tag = Column(String, nullable=False)          # 產業標籤，例如 "AI通路" 或 "系統整合"

    # 建立與財務數據的一對多關聯
    financial_records = relationship("FinancialData", back_populates="company")

    def __repr__(self):
        return f"<Company(ticker='{self.ticker}', name='{self.name}', tag='{self.industry_tag}')>"


class FinancialData(Base):
    """
    財報指標明細表（記錄五年歷史財務數據）
    """
    __tablename__ = "financial_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, ForeignKey("companies.ticker"), nullable=False)
    year = Column(Integer, nullable=False)                 # 會計年度，例如 2024
    revenue = Column(Float, nullable=False)               # 營業收入 (單位：新台幣千元)
    gross_profit = Column(Float, nullable=False)          # 營業毛利 (單位：新台幣千元)
    operating_income = Column(Float, nullable=False)      # 營業利益 (單位：新台幣千元)
    net_income = Column(Float, nullable=False)            # 稅後純益 (單位：新台幣千元)
    eps = Column(Float, nullable=True)                    # 每股盈餘 (EPS)
    is_tested_party = Column(Boolean, default=False)      # 是否為受測企業 (Tested Party)

    # 建立關聯對應
    project = relationship("Project", back_populates="financial_records")
    company = relationship("Company", back_populates="financial_records")

    def __repr__(self):
        return f"<FinancialData(project_id={self.project_id}, ticker='{self.ticker}', year={self.year})>"


def init_db():
    """
    初始化資料庫，如果資料表不存在則自動建立。
    """
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """
    提供 Context Manager 來安全地管理資料庫 Session 生命週期，避免資料庫被鎖定 (Database Locked)。
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
