import hashlib
import json
from time import time
from time import gmtime, strftime
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import sys
import requests
import zmq
from threading import Thread
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, load_only
from database import Block, Block_Alert
from database import Base
from database import Transaction
from datetime import datetime
from config import database_node, node_id

class Blockchain(object):
    def __init__(self):
        # database connection
        #gets database name from config
        self.engine = create_engine(str(database_node[node_id]))
        Base.metadata.create_all(self.engine)
        self.chain = []
        self.current_transaction = []
        self.nodes = set()
        # create a genesis block
        self.create_genesis_block()
    
    # creates database connection
    def session_factory(self):
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        session = Session()
        return session
    
    # creates the first block on system 
    def create_genesis_block(self):
        latest_transaction = self.get_latest_transaction()
        if latest_transaction == None:
            time_stamp = datetime.utcnow()
            result = self.new_transaction_db(time_stamp = time_stamp,
                                    product_serial_number = "",
                                    product_name = "",
                                    product_price = 0,
                                    tran_type= "genesis block",
                                    manufacturer_seller_id = 0,
                                    manufacturer_seller_name = "",
                                    manufacturer_seller_address = "",
                                    manufacturer_seller_licence_number = "",
                                    Status = "Completed")
            if result != None:
                block = {'transaction' : {'product_serial_number' : result.product_serial_number,
                                        'product_name' :result.product_name,
                                        'product_price':result.product_price,
                                        'tran_type': result.type,
                                        'manufacturer_seller_id':result.manufacturer_seller_id,
                                        'manufacturer_seller_name':result.manufacturer_seller_name,
                                        'manufacturer_seller_address':result.manufacturer_seller_address,
                                        'manufacturer_seller_licence_number':result.manufacturer_seller_licence_number
                    },
                    'previous_hash' : 1,
                    'proof_provided_by' : "system",
                    'proof' : 100
                }
                current_hash = self.hash(block)
                self.new_block(time_stamp = time_stamp,
                               block_id = 10000,
                               transaction_id = result.transaction_id,
                               previous_hash = 1,
                               proof_provided_by = "system",
                               current_hash= current_hash,
                               merkle_root_hash = current_hash,
                               proof = 100)
    
    # used in merkle tree calculation
    def dict_to_string(self, dict):
        print(''.join(''.join((k, str(v))) for k,v in dict.items()).encode('utf-8'))
        return ''.join(''.join((k, str(v))) for k,v in dict.items()).encode('utf-8')


    def compute_merkle_root(self, children):
        if len(children) == 1:
            return children[0]

        current_hash = ''
        cnt = 0
        hashlist = []
        for hashes in children:
            current_hash = current_hash + hashes
            cnt = cnt + 1
            if cnt % 2 == 0:
                hashlist.append(hashlib.sha256(current_hash.encode('utf-8')).hexdigest())
                current_hash = ''
            
        return self.compute_merkle_root(hashlist)
    # creates the new block in database
    def new_block(self,time_stamp,block_id,transaction_id,previous_hash,
                  proof_provided_by,current_hash, merkle_root_hash,
                  proof = None):
        print(previous_hash)
        session = self.session_factory()

        block = Block(time_stamp=time_stamp,block_id = block_id,transaction_id = transaction_id,proof = proof,
                            proof_provided_by = proof_provided_by, previous_hash = previous_hash,
                            hash = current_hash, merkle_root_hash = merkle_root_hash)
        session.add(block)
        session.commit()
        latest_block = session.query(Block).order_by(Block.id.desc()).first()
        session.close()
        return latest_block
    
    # gets the last transaction that was added
    def get_latest_transaction(self):
            session = self.session_factory()
            latest_tran_id = session.query(Transaction).order_by(Transaction.transaction_id.desc()).first()
            session.close()
            return latest_tran_id

    #gets transaction as per transaction id
    def get_transaction_details(self, transaction_id):
        session = self.session_factory()
        transaction_details = session.query(Transaction).filter_by(transaction_id=transaction_id).first()
        session.close()
        return transaction_details

    def get_product_serial_number(self, product_serial_number):
        session = self.session_factory()
        transaction_details = session.query(Transaction).filter_by(product_serial_number=product_serial_number).all()
        session.close()
        return transaction_details

    # gets the last block that was added on the system
    def get_latest_block(self):
            session = self.session_factory()
            latest_block = session.query(Block).order_by(Block.id.desc()).first()
            session.close()
            return latest_block
    
    def get_blocks_per_blockID(self, block_id):
        session = self.session_factory()
        block = session.query(Block).filter_by(block_id=block_id).all()
        session.close()
        return block

    def get_transactions_per_blockID(self, block_id):
        session = self.session_factory()
        block = session.query(Block).filter_by(block_id=block_id).all()
        session.close()
        return block

    def get_blocks_per_transaction_id(self, transaction_id):
        session = self.session_factory()
        block = session.query(Block).filter_by(transaction_id=transaction_id).first()
        session.close()
        return block

    def get_pending_transaction(self):
        session = self.session_factory()
        pending_tran_query = session.query(Transaction).filter_by(Status="Pending").order_by(Transaction.transaction_id.asc()).all()
        session.close()
        return pending_tran_query
    
    # creates new transaction in database
    def update_transaction_status(self, transaction_id):
        session = self.session_factory()
        print(transaction_id)
        transaction = session.query(Transaction).filter_by(transaction_id=transaction_id).first()
        #print(len(transaction))
        transaction.Status = "Completed" 
        session.commit()
        session.close()     
        return "success"

    def new_transaction_db(self,time_stamp,product_serial_number,product_name,
                           product_price,tran_type,manufacturer_seller_id,
                           manufacturer_seller_name,manufacturer_seller_address,
                           manufacturer_seller_licence_number,Status= "Pending"):      
        session = self.session_factory()
        tran = Transaction(time_stamp=time_stamp,product_serial_number=product_serial_number,product_name=product_name,
                            product_price = product_price, type = tran_type, manufacturer_seller_id = manufacturer_seller_id,
                            manufacturer_seller_name = manufacturer_seller_name, manufacturer_seller_address = manufacturer_seller_address,
                            manufacturer_seller_licence_number = manufacturer_seller_licence_number,Status = Status)
        session.add(tran)
        session.commit()
        latest_tran_id = session.query(Transaction).order_by(Transaction.transaction_id.desc()).first()
        '''
        tran_alert = Transaction_Alert(transaction_id = latest_tran_id.transaction_id, status = "Active")
        session.add(tran_alert)
        session.commit()
        '''
        session.close()
        return latest_tran_id

    #calculates hash
    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys= True).encode()
        return hashlib.sha256(block_string).hexdigest()


    @property
    def get_blockchain(self):
        session = self.session_factory()
        block_chain = session.query(Block).order_by(Block.block_id.asc(),Block.transaction_id.asc()).all()
        session.close()
        return block_chain

    #provides proof of work  
    def proof_of_work(self ,last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof = proof + 1
        return proof

    def valid_proof(self,last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        #print("i am inside valid proof")
        return guess_hash[:4] == "0000"

    #adds nodes in the system
    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
    
   
    def valid_chain(self, previous_hash,proof):
        
        last_block = self.get_latest_block()
        if str(last_block.hash) != str(previous_hash):
            print(last_block.hash)
            print(previous_hash)
            return False

            # Check that the Proof of Work is correct
            val = self.valid_proof(last_block.proof, proof)
            print(val)
            if not self.valid_proof(last_block.proof, proof):
                return False
        return True

    
