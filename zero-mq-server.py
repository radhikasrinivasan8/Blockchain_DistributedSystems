import os
import socket
import sys
import time

import zmq
import urllib.request
import requests
from threading import Thread
from queue import Queue
import json
import ast 
import configparser
from config import client_map,flask_api_url, node_id,port_start_range, port_end_range, tran_alert_port_number,tran_alert_tcp_conn

flask_url_for_this_node = flask_api_url[node_id]


def discover_neighbours(PING_PORT_NUMBER,available_servers):
    global port_start_range
    PING_INTERVAL    = 1  
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Bind UDP socket to local port so we can receive pings
    sock.bind(('', PING_PORT_NUMBER))

    # main ping loop
    # We use zmq_poll to wait for activity on the UDP socket, since
    # this function works on non-0MQ file handles. We send a beacon
    # once a second, and we collect and report beacons that come in
    # from other nodes:

    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    ping_at = time.time()
    
    #port_start_range = 1100
    while True:
        timeout = ping_at - time.time()
        if timeout < 0:
            timeout = 0
        try:
            events = dict(poller.poll(1000* timeout))
        except KeyboardInterrupt:
            print("interrupted")
            break

        # Someone answered our ping
        if sock.fileno() in events:
            msg, addrinfo = sock.recvfrom(tran_alert_port_number[node_id])
            if addrinfo not in available_servers:
                if str(addrinfo[1]) in str(tran_alert_port_number):
                    if str(addrinfo[1]) != str(tran_alert_port_number[node_id]):
                        val = msg.decode()
                        js = json.loads(val)
                        print(js)
                        #match_json =json.dumps({'data': 'Call Concensus'})
                        #print(match_json)
                        if "block_id" in js:
                            url = flask_url_for_this_node + '/update_concensus_info'
                            #val = {'flag':'True'}
                            r = requests.post(url = url, json = js)
                        else:
                            #js = json.loads(val)
                            #print(js)
                            url = flask_url_for_this_node + '/replicate_transaction'
                            r = requests.post(url = url, json = js)
                            print("high alert")
                else:
                    available_servers.add(addrinfo)
                    val = "http://" + str(addrinfo[0]) + ":" + str(addrinfo[1])
                    print(val)
                    data = {"nodes" : [f'{val}']}
                    url = flask_url_for_this_node + '/nodes/register'
                    r = requests.post(url = url, json = data)
                    print(r)
                    print("Found peer %s:%d" % addrinfo)

        if time.time() >= ping_at:
            # Broadcast our beacon
            print ("Pinging peers…")
            sock.sendto(b'!', 0, (client_map[node_id][0],port_start_range))
            ping_at = time.time() + PING_INTERVAL
        port_start_range = port_start_range + 1

        if port_start_range == port_end_range:
            port_start_range = 1100

def message_for_new_transaction(q,serverlist):
    context = zmq.Context()
    sock = context.socket(zmq.REP)
    sock.bind(tran_alert_tcp_conn[node_id])
    while True:
        message = str(sock.recv().decode())
        sock.send_string("Echo: " + message)
        q.put(message)
        serverlist.put(available_servers)

def broadcast_new_transaction(available_servers,q,serverlist):
    print("here")
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # Ask operating system to let us do broadcasts from socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Bind UDP socket to local port so we can receive pings

        # port number loaded from config according to node id
    sock.bind(('', tran_alert_port_number[node_id]))
    list_of_servers = serverlist.get()
    serverlist.task_done()
    while True:
        while q.qsize() != 0:
            current_message = q.get()
            q.task_done() 
            for servers in list_of_servers: 
                print("servers are" + str(servers))                     
                sock.sendto(json.dumps(current_message).encode('utf-8'), 0, (client_map[node_id][0], servers[1]))
                              

if __name__ == '__main__':
    #gets port number from config
    PING_PORT_NUMBER = int(client_map[node_id][1])
    available_servers = set()
    q = Queue(maxsize=0)
    serverlist = Queue(maxsize=0)
    
    input = (Thread(target=discover_neighbours, args=(PING_PORT_NUMBER,available_servers,)))
    input.start()
    
    alert_for_new_transaction = (Thread(target=message_for_new_transaction, args=(q,serverlist,)))
    alert_for_new_transaction.start()

    broadcast_new_transaction = (Thread(target=broadcast_new_transaction, args=(available_servers,q,serverlist,)))
    broadcast_new_transaction.start()

