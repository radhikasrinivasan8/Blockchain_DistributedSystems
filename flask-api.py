from flask import Flask, jsonify, request,render_template
from datetime import datetime
from blockchain import Blockchain
import sys 
import zmq
from threading import Thread
from uuid import uuid4
import json
from config import tran_alert_tcp_conn,flask_run, node_id,client_map

app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()
call_concensus = False
last_concensus_block_id = 0
last_concensus_block_mined_by = 'None'

# invoked through threads, sends the messages to all pears with transaction details
def send_new_transaction_alert(values):
    context = zmq.Context()
    sock = context.socket(zmq.REQ)
    # imported from config
    sock.connect(tran_alert_tcp_conn[node_id])   
    sock.send_string(json.dumps(values))
    mess= (sock.recv().decode())
    print(mess)

# invoked through threads, sends the messages to all pears with block details
def send_new_block_alert(values):
    print("in send block concensus block")
    print(values)
    context = zmq.Context()
    sock = context.socket(zmq.REQ)
    # imported from config
    sock.connect(tran_alert_tcp_conn[node_id])   
    sock.send_string(json.dumps(values))
    mess= (sock.recv().decode())
    print(mess)

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json(force=True)
    print(values)
    nodes = values.get('nodes')
    print(nodes)
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        print(node)
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/concensus_info', methods=['GET'])
def check_for_concensus():
    global call_concensus
    global last_concensus_block_id
    global last_concensus_block_mined_by
    print(call_concensus)
    if not call_concensus:
        ret = "No new Transactions mined by other nodes. Data is up to date"
    else:
        ret = "New Transactions mined by other nodes. Call for Consensus"
    response = {
        'value':ret,
        'last_concensus_block_id': last_concensus_block_id,
        'last_concensus_block_mined_by': last_concensus_block_mined_by
    }
    return jsonify(response)

@app.route('/update_concensus_info', methods=['POST'])
def update_concensus_flag():
    global call_concensus
    global last_concensus_block_id
    global last_concensus_block_mined_by
    value = request.get_json(force=True)
    value = json.loads(value)
    print("in update concensus block")
    print(value)
    valid_proof = blockchain.valid_chain(value['previous_hash'],value['proof'])
    print("before valid proof")
    print(valid_proof)
    call_concensus = True
    tran_details = value['tran_details']
    if valid_proof:
        for transaction_details in tran_details:
            block_result = blockchain.new_block(datetime.utcnow(),
                                            value['block_id'],
                                            transaction_details['transaction_id'],
                                            value['previous_hash'],
                                            value['proof_provided_by'],
                                            value['current_hash'],
                                            value['merkle_root'],
                                            value['proof'])
            update_tran = blockchain.update_transaction_status(transaction_details['transaction_id'])
            last_concensus_block_id = value['block_id']
            last_concensus_block_mined_by = value['proof_provided_by']
    return "success"

@app.route('/getnodes', methods=['GET'])
def get_nodes():
    nodes = blockchain.nodes
    print(len(nodes))
    if nodes is None:
        return "No miners active right now", 200

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(nodes),
    }
    print(response)
    return jsonify(response), 201

@app.route('/get_pending_transactions', methods=['GET'])
def get_pending_transaction():
    result = blockchain.get_pending_transaction()
    ret = list()
    for i in range(0, len(result)):
        transaction_details = {'transaction_id' : result[i].transaction_id,
                            'product_serial_number' : result[i].product_serial_number,
                            'product_name' :result[i].product_name,
                            'product_price':result[i].product_price,
                            'tran_type': result[i].type,
                            'manufacturer_seller_id':result[i].manufacturer_seller_id,
                            'manufacturer_seller_name':result[i].manufacturer_seller_name,
                            'manufacturer_seller_address':result[i].manufacturer_seller_address,
                            'manufacturer_seller_licence_number':result[i].manufacturer_seller_licence_number
                        }
        ret.append(transaction_details)
    return jsonify(ret)


@app.route('/transactions/new_seller',endpoint='seller', methods=['POST'])
@app.route('/transactions/new_manufacturer',endpoint = 'manufacturer', methods=['POST'])
def collect_data_from_SellerManufacturer_Form():
   
    if request.endpoint == 'seller':
        tran_type = "Seller"
    elif request.endpoint == 'manufacturer':
        tran_type = "Manufacturer"

    data = {'product_serial_number':request.form['product_serial_number'],
            'product_name': request.form['product_name'],
            'product_price':request.form['Product_Price'],
            'manufacturer_seller_id': request.form['manufacturer_seller_id'],
            'manufacturer_seller_name': request.form['manufacturer_seller_name'],
            'manufacturer_seller_address': request.form['manufacturer_seller_address'],
            'manufacturer_seller_licence_number': request.form['manufacturer_seller_licence_number'],
            'tran_type' : tran_type
    }
    result = new_transaction(data)
    return result

def new_transaction(values):
    time_stamp = datetime.utcnow()
    ret = validate_input(values)
    if ret == 'Missing values':
        print("in ret")
        return 'Missing values', 400

    # Create a new Transaction  
    index = blockchain.new_transaction_db(time_stamp, values['product_serial_number'],\
    values['product_name'], values['product_price'], values['tran_type'], values['manufacturer_seller_id'],\
    values['manufacturer_seller_name'],values['manufacturer_seller_address'],values['manufacturer_seller_licence_number'])
    if index != None:
        values['time_stamp'] = str(time_stamp)
        output = (Thread(target=send_new_transaction_alert, args=(values, )))
        output.start()
        response = 'Operation Successful. Transaction is in pending state right now. It will be added to Block once it is approved'
    else:
        response = 'Some error occurred. Please try again later'
    return response, 201 

def validate_input(values):
    required = ['product_serial_number', 'product_name', 'product_price','manufacturer_seller_id',\
    'manufacturer_seller_name','manufacturer_seller_address','manufacturer_seller_licence_number']
    if not all(k in values for k in required):
        return 'Missing values'

@app.route('/mine',endpoint = 'mine', methods=['POST'])
def collect_data_from_form_mine():
    data = request.form['comment']
    ls = data.splitlines()
    transaction_list = []
    tran_dict = {}
    for i in range(0, len(ls)):
        ls1 = ls[i].split(": ")
        if ls1[0] == "Transaction_id":
            tran_dict['transaction_id']= ls1[1]

        elif ls1[0] == "Product Serial Number":
            tran_dict['product_serial_number'] = ls1[1]

        elif ls1[0] == "Product Name":
            tran_dict["product_name"] = ls1[1]

        elif ls1[0] == "Product Price":
            tran_dict["product_price"] = ls1[1]

        elif ls1[0] == "Type":
            tran_dict["tran_type"] = ls1[1]
            
        elif ls1[0] == "Manufacturer ID" or ls1[0] == "Seller ID":
            tran_dict["manufacturer_seller_id"] = ls1[1]

        elif ls1[0] == "Manufacturer Name" or ls1[0] == "Manufacturer Name":
             tran_dict["manufacturer_seller_name"] = ls1[1]

        elif ls1[0] == "Address":
             tran_dict["manufacturer_seller_address"] = ls1[1]

        elif ls1[0] == "Licence Number":
            tran_dict['manufacturer_seller_licence_number'] = ls1[1]
            transaction_list.append(tran_dict)
            tran_dict = {}

    ret = mine(transaction_list)
    print(ret)
    if int(ret[0]) > 0:
        result = "Transactions Mined Successfully and added to Block. Proof of Work - " + str(ret[0]) 
    else: 
        result = "Some error occurred. Please try again later. " + str(ret) 
    return result

def mine(transaction_data):
    #tran_time_stamp = datetime.strptime(values['time_stamp'],"%Y-%m-%d %H:%M:%S.%f")
    current_time_stamp = datetime.utcnow()
    #print(transaction_data)
    proof = 0
    if transaction_data != None:
        # transaction added, now starting mining and add the block
        lastest_block = blockchain.get_latest_block()
        last_proof = lastest_block.proof
        proof = blockchain.proof_of_work(last_proof)
        block_id = lastest_block.block_id + 1
        
        # gets the node id
        proof_provided_by = str(client_map[node_id][0]) + ":" + str(client_map[node_id][1])
        
        for i in range(0, len(transaction_data)):
            tran_id = transaction_data[i]['transaction_id']
            block = {'time_stamp' : str(current_time_stamp),
                 'transactions' : transaction_data[i],
                 'previous_hash' : lastest_block.hash,
                 'proof_provided_by' : proof_provided_by,
                 'proof' : proof
                }
            current_hash = blockchain.hash(block)
            
            #logic to calculate merkle root
            children_hash_list = []
            get_all_hashes_per_block = blockchain.get_blocks_per_blockID(block_id)
            children_hash_list.append(current_hash)

            if len(children_hash_list) % 2 != 0:
                children_hash_list.append(current_hash)
            
            if get_all_hashes_per_block != None:
                for i in range(0, len(get_all_hashes_per_block)):
                    hash_val = get_all_hashes_per_block[i].hash
                    children_hash_list.append(hash_val)
            
            merkle_root = blockchain.compute_merkle_root(children_hash_list)
            # create block opject to send for concensus
            block_to_send_concensus = {'time_stamp' : str(current_time_stamp),
                                       'block_id': int(block_id),
                                       'tran_details': transaction_data,
                                       'previous_hash':lastest_block.hash,
                                       'proof_provided_by': proof_provided_by,
                                       'current_hash': current_hash,
                                       'merkle_root':merkle_root,
                                       'proof':proof
                                       }

            block_result = blockchain.new_block(current_time_stamp,
                                        int(block_id),
                                        tran_id,
                                        lastest_block.hash,
                                        proof_provided_by,
                                        current_hash,
                                        merkle_root,
                                        proof)
            update_tran = blockchain.update_transaction_status(tran_id)
            print(update_tran)

    if block_result != None:
        send_block_for_consensus = {'data':'Call Concensus'}
        block_alert = (Thread(target=send_new_block_alert, args=(block_to_send_concensus, )))
        block_alert.start()
    
    return proof, 200

@app.route('/replicate_transaction',endpoint = 'replicate_transaction', methods=['POST'])
def replicate_transaction():
    values = request.get_json(force=True)
    #print(values)
    time_stamp = datetime.utcnow()
    ret = validate_input(values)
    if ret == 'Missing values':
        print("in ret")
        return 'Missing values', 400
    
    # find type required to record in transaction
    values = json.loads(values)
    print(values)
    print( values['product_serial_number'])
    # Create a new Transaction  
    index = blockchain.new_transaction_db(time_stamp, values['product_serial_number'],\
    values['product_name'], values['product_price'], values['tran_type'], values['manufacturer_seller_id'],\
    values['manufacturer_seller_name'],values['manufacturer_seller_address'],values['manufacturer_seller_licence_number'])
    print(index)
    return "success"


def get_list_of_transactions(block_id):
    ls = blockchain.get_transactions_per_blockID(block_id)
    tran_list = []
    for i in range(0,len(ls)):
        transaction_details = blockchain.get_transaction_details(ls[i].transaction_id)
        tran_list.append(ls[i].transaction_id)
    return tran_list

@app.route('/chain', methods=['GET'])
def full_chain():
    ls = blockchain.get_blockchain
    chain = list()
    
    list_of_tran = []
    for i in range(0, len(ls)):

        # get transaction details
        transaction_details = blockchain.get_transaction_details(ls[i].transaction_id)

        tran_details =  {'Transaction ID' : transaction_details.transaction_id,
                         'Product Serial Number' : transaction_details.product_serial_number,
                         'Product Name' :transaction_details.product_name,
                         'Product Price':transaction_details.product_price,
                         'Type': transaction_details.type,
                         'Hash' : ls[i].hash,
                         'Merkle Root Hash' : ls[i].merkle_root_hash
                        }
        if transaction_details.type == "Manufacturer":
            tran_details['Manufacturer ID'] = transaction_details.manufacturer_seller_id
            tran_details['Manufacturer Name'] = transaction_details.manufacturer_seller_name
            tran_details['Manufacturer Address'] = transaction_details.manufacturer_seller_address
            tran_details['Manufacturer Licence Number'] = transaction_details.manufacturer_seller_licence_number
        else:
            tran_details['Seller ID'] = transaction_details.manufacturer_seller_id
            tran_details['Seller Name'] = transaction_details.manufacturer_seller_name
            tran_details['Seller Address'] = transaction_details.manufacturer_seller_address
            tran_details['Seller Licence Number'] = transaction_details.manufacturer_seller_licence_number

        list_of_tran.append(tran_details)

        if i < len(ls)-1 and ls[i].block_id != ls[i+1].block_id:
        
            resp = {"TimeStamp" : str(ls[i].time_stamp),
            "Block ID": ls[i].block_id,
            "Block Merkle Root Hash": ls[i].merkle_root_hash,
            "Transaction Details" : list_of_tran,
            "Previous Hash" : ls[i].previous_hash,
            "Proof Provided By" : ls[i].proof_provided_by,
            "Proof" : ls[i].proof,
            }
            list_of_tran = []
            chain.append(resp)
        
         
    last_record_idx = len(ls)-1
    # process last record
    resp = {"TimeStamp" : str(ls[last_record_idx].time_stamp),
            "Block ID": ls[last_record_idx].block_id,
            "Block Merkle Root Hash": ls[last_record_idx].merkle_root_hash,
            "Transaction Details" : list_of_tran,
            "Previous Hash" : ls[last_record_idx].previous_hash,
            "Proof Provided By" : ls[last_record_idx].proof_provided_by,
            "Proof" : ls[last_record_idx].proof,
            }
    chain.append(resp)

    response = {
        'chain':chain
    }
    return jsonify(response), 200

@app.route('/block/<id>', methods=['GET'])
def block(id):
    block_details = blockchain.get_blocks_per_blockID(id)
    chain = []
    if block_details != None:
        for i in range(0, len(block_details)):
            transaction_details = blockchain.get_transaction_details(block_details[i].transaction_id)
        
            resp = {"time_stamp" : str(block_details[i].time_stamp),
            "block_id": block_details[i].block_id,
            "transaction_details" : {'transaction_id' : transaction_details.transaction_id,
                                    'product_serial_number' : transaction_details.product_serial_number,
                                    'product_name' :transaction_details.product_name,
                                    'product_price':transaction_details.product_price,
                                    'tran_type': transaction_details.type,
                                    'manufacturer_seller_id':transaction_details.manufacturer_seller_id,
                                    'manufacturer_seller_name':transaction_details.manufacturer_seller_name,
                                    'manufacturer_seller_address':transaction_details.manufacturer_seller_address,
                                    'manufacturer_seller_licence_number':transaction_details.manufacturer_seller_licence_number
                                },
            "previous_hash" : block_details[i].previous_hash,
            "proof_provided_by" : block_details[i].proof_provided_by,
            "hash" : block_details[i].hash,
            "merkle_root_hash" : block_details[i].merkle_root_hash,
            "proof" : block_details[i].proof
            }
            chain.append(resp)
        response = {
        'chain':chain
        }   
    return jsonify(response), 200

@app.route('/track_product/<product_serial_number>', methods=['GET'])
def track_product(product_serial_number):
    transaction_details = blockchain.get_product_serial_number(product_serial_number)
    
    chain = []
    if transaction_details != None:
        for i in range(0, len(transaction_details)):
            print(transaction_details[i].transaction_id)
            block_details = blockchain.get_blocks_per_transaction_id(transaction_details[i].transaction_id)
            
            tran_resp = {'TRANSACTION ID' : transaction_details[i].transaction_id,
                        'PRODUCT SERIAL NUMBER' : transaction_details[i].product_serial_number,
                        'PRODUCT NAME' :transaction_details[i].product_name,
                        'PRODUCT PRICE':transaction_details[i].product_price,
                        'TYPE': transaction_details[i].type
                        }
            if transaction_details[i].type == 'Seller':
                tran_resp['SELLER ID'] = transaction_details[i].manufacturer_seller_id
                tran_resp['SELLER NAME'] = transaction_details[i].manufacturer_seller_name
                tran_resp['SELLER ADDRESS']:transaction_details[i].manufacturer_seller_address
                tran_resp['SELLER LICENCE NUMBER']:transaction_details[i].manufacturer_seller_licence_number
            else:
                tran_resp['MANUFACTURER ID'] = transaction_details[i].manufacturer_seller_id
                tran_resp['MANUFACTURER NAME'] = transaction_details[i].manufacturer_seller_name
                tran_resp['MANUFACTURER ADDRESS']:transaction_details[i].manufacturer_seller_address
                tran_resp['MANUFACTURER LICENCE NUMBER']:transaction_details[i].manufacturer_seller_licence_number

            if block_details != None:
                resp = {"TIMESTAMP" : str(block_details.time_stamp),
                "BLOCK ID": block_details.block_id,
                "TRANSACTION DETAILS" : tran_resp,
                "PREVIOUS HASH" : block_details.previous_hash,
                "PROOF PROVIDED BY" : block_details.proof_provided_by,
                "CURRENT HASH" : block_details.hash,
                "MERKLE ROOT HASH" : block_details.merkle_root_hash,
                "PROOF" : block_details.proof
                }
                
                chain.append(resp)
        response = {
            'chain':chain
            }   
    return jsonify(response), 200

if __name__ == '__main__':
    # imported from config as per node_id
    host_details = flask_run[node_id][0]
    port_number = int(flask_run[node_id][1])
    app.run(host= host_details, port=port_number)
        

   