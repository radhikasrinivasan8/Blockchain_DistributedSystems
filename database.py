import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Table,TIMESTAMP,Float, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Transaction(Base):
    __table__ = Table('transaction', Base.metadata,
    Column('transaction_id',Integer, Sequence('seq', start=10000, increment=1), primary_key=True),
    Column('time_stamp',TIMESTAMP, nullable= False),
    Column('product_serial_number',String(250), nullable= False),
    Column('product_name',String(250), nullable = False),
    Column('product_price',Float,nullable=False),
    Column('type',String(250),nullable=False),
    Column('manufacturer_seller_id',String(250),nullable=False),
    Column('manufacturer_seller_name',String(250),nullable=False),
    Column('manufacturer_seller_address',String(250),nullable=False),
    Column('manufacturer_seller_licence_number',String(250),nullable=False),
    Column('Status',String(250),nullable=False)
    #wallet = relationship(Wallet)
    ) 
class Block(Base):
     __table__ = Table('block', Base.metadata,
    Column('id',Integer, Sequence('seq', start=10000, increment=1),primary_key=True),
    Column('block_id',Integer, nullable = False),
    Column('time_stamp',TIMESTAMP, nullable= False),
    Column('transaction_id',Integer),
    Column('proof',String(250), nullable = False),
    Column('proof_provided_by',String(250), nullable = False),
    Column('previous_hash',String(250),nullable=False),
    Column('hash',String(250),nullable=False), 
    Column('merkle_root_hash',String(250),nullable=False) 
    )
class Block_Alert(Base):
    __table__ = Table('transaction_alert', Base.metadata,
    Column('id',Integer, Sequence('seq', start=10000, increment=1), primary_key=True),
    Column('block_id',Integer, nullable = False),
    Column('Status',String(250),nullable=False)
    ) 
# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
from sqlalchemy import create_engine
engine = create_engine('sqlite:///sqlalchemy_blockchain.db')
 
# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

from sqlalchemy.orm import sessionmaker
DBSession = sessionmaker(bind=engine)

session = DBSession()
