# Block-Chain-Implementation

# This is implementation of blockchain concepts in python. Using this one can register baby products on blockchain platform.
# Features covered in this code 
    1) Each Transaction when mined gets the unique hash, which is immutable
    2) Mining.
    3) Proof of Work.
    4) Merkle Root for the block.
    5) Multiple transactions which are mined together form a single block.
    6) Network can have n number of miners and they are able to discover each other using gossip protocol. Gossip protocol is implemented using zeromq and udp protocol.
    7) Whenever a transaction is created on any node,it is replicated on each node(miner) so that they know that there is a new transaction to be mined.
    8) Once a transaction is mined by any block, it sends the message to other nodes to call for concensus.
    9) Other miners verify the proof of work and validates the chain and then adds to the chain.

# Steps to Run
Simulating multiple nodes on single machine
1)  In config.py put the node_id as 1 and start flask server and zeromq server as
  python flask-api.py
  python zero-mq-server.py
  Then change the node_id = 2 and follow the same process.
  
2) Deploy the html pages on apache server and run the register_product.html 
