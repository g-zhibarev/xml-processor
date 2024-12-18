from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Numeric, Integer, Date, Text, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)


class Phone(BaseModel):
    __tablename__ = 'phone'
    phone = Column(Text, nullable=False)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    company = relationship("Company", back_populates="phone")


class Company(BaseModel):
    __tablename__ = 'company'
    ogrn = Column(Numeric(13, 0), unique=True, nullable=False)
    inn = Column(Numeric(10, 0), nullable=False)
    name = Column(Text, nullable=True)
    phone = relationship("Phone", back_populates="company")
    update = Column(Date, nullable=False)
