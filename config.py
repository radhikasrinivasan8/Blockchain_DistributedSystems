client_map = {1:["255.255.255.255",1100],
              2:["255.255.255.255",1101],
              3:["255.255.255.255",1103],
              4:["255.255.255.255",1104]}

flask_api_url = {1:"http://0.0.0.0:5000",
                2:"http://0.0.0.0:5001",
                3:"http://0.0.0.0:5002",
                4:"http://0.0.0.0:5003"}

flask_run =     {1:["0.0.0.0",5000],
                2:["0.0.0.0",5001],
                3:["0.0.0.0",5002],
                4:["0.0.0.0",5003]}
# define your node from here


# trusted network port range
port_start_range = 1100

port_end_range = 1110

# new transaction alert port number-- will be same for all the systems

tran_alert_port_number = {1:1127,
                         2:1128,
                         3:1129,
                         4:1130}

# transaction alert tcp connection -- change if running on same system
tran_alert_tcp_conn = {1:"tcp://127.0.0.1:5678",
                       2:"tcp://127.0.0.1:5679",
                       3:"tcp://127.0.0.1:5680",
                       4:"tcp://127.0.0.1:5681"
                    }
database_node = {1:'sqlite:///sqlalchemy_blockchain1.db',
                 2:'sqlite:///sqlalchemy_blockchain2.db',
                 3:'sqlite:///sqlalchemy_blockchain3.db',
                 4:'sqlite:///sqlalchemy_blockchain4.db'
                }
node_id = 1
