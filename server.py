import socket
import os
import selectors
import struct
import hashlib
import signal
import errno
import re
import sys

#todo
# if server receives non corrupt packet & correct seq num -> send ack to client and set timer 
# if server receives corrupt packet or wrong seq num -> send nak to client 
## sender must retransmit corrupt packet upon receiving nak from server


SEQ_OUT = 0
server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

# Buffer size
STREAM_BUFFER_SIZE =1024
MAX_STRING_SIZE = 256

EXPECTED_SEQ = 0

RECV_SEQ = 0
RECV_SIZE = 0
RECV_DATA = 0
RECV_CHECKSUM = 0
RECV_TEXT = 0

sel = selectors.DefaultSelector()


client_list = []
'''
[0] = username,
[1] = addr
[2] = next_num
[3] = follow list []
'''

client_count = 0


unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s')


# todo 


## Functions ##

def extract_packet_fields(UDP_packet):
    global RECV_SEQ, RECV_SIZE, RECV_DATA, RECV_CHECKSUM, RECV_TEXT
    # Extract fields from packet
    RECV_SEQ = UDP_packet[0]
    RECV_SIZE = UDP_packet[1]
    RECV_DATA = UDP_packet[2]
    RECV_CHECKSUM = UDP_packet[3]
    # extract text from RECV_DATA
    RECV_TEXT = RECV_DATA[:RECV_SIZE].decode()

# Check if packet recieved is duplicate by comparing its sequence number to the expected sequence number
def is_duplicate(adr):
    global RECV_SEQ, client_list
    client = get_client(adr)
    expected_num = client[2]
    if(expected_num==RECV_SEQ):
         return False
    else:
         return True
# Check if packet recieved is corrupt by comparing its checksum against the computed checksum
def is_corrupt():
    global RECV_SEQ, RECV_SIZE, RECV_DATA, RECV_CHECKSUM, RECV_TEXT, packer
    # Calculate and confirm checksum
    values = (RECV_SEQ,RECV_SIZE,RECV_DATA)
    packed_data = packer.pack(*values)
    computed_checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

    if RECV_CHECKSUM == computed_checksum:
        return False
    else:
        return True

# Invert the sequence number between 0 and 1        
def flip_sequence_number():
    global EXPECTED_SEQ
    num = EXPECTED_SEQ
    EXPECTED_SEQ = get_opposite(num)

def flip_seq(adr):
    global client_list

    # convert tuple to list, edit, convert list back to tuple
    client = get_client(adr) #tuple
    list_client = list(client) #convert tuple to list
    list_client[2] = get_opposite(client[2])
    client_list.remove(client) # remove tuple
    client = tuple(list_client)
    client_list.append(client)


def get_opposite(num):
    if num ==0:
        return 1
    else:
         return 0

def accept_client(user_name, addr, seq_num):
    send_ack(addr, seq_num)
    global client_list
    client_list.append((user_name,addr, seq_num, ['@all', f"@{user_name}"]))
    client = get_client(addr)
    print(f"Welcome to the server {user_name}")
    print("\n - - - - - -")
    print(f'{RECV_TEXT}')
    print(f"\nSeq Num We got: {client[2]}")
    # flip expected sequence number 
    flip_seq(client[1])
    print(f"\nNext Expecting Seq Num: {get_client(addr)[2]}")
    print("\n - - - - - -\n")

def get_packet(sock, mask):
    global client_list
    # Receive the packet and address of client
    received_packet, addr = sock.recvfrom(STREAM_BUFFER_SIZE)
       
    print(f"\nConnection from:\n{addr[0]}\n{addr[1]}")

    # Get client obj
    client = get_client(addr)

    # Unpack and Extract packet fields
    UDP_packet = unpacker.unpack(received_packet)
    extract_packet_fields(UDP_packet)
    # extract username 
    msg = RECV_TEXT
    msg_split = msg.split(" ")
    user_name = msg_split[0].strip(":")
        
    # Packet not corrupt
    if is_corrupt() == False:
        # Client's first connection
        if client==None:
            accept_client(user_name, addr,RECV_SEQ) # Accept client and flip sequence number 
        # Returning client
        else:
            expected_seq_num = client[2]
            follows = client[3]
            # Duplicate Packet    
            if is_duplicate(addr) == True:
                # Send NAK (sending ack for last good packet)
                send_ack(addr, RECV_SEQ)
                print("\n # # # # # #")
                print("\nDuplicate Packet!!\n")
                print(f"\nExpected Sequence Number: {expected_seq_num}\nSequence Number we got: {RECV_SEQ}")
                print("\n # # # # # #\n")
            # Respond to commands
            else:
                # send ACK to client (positive acknowledgement)
                send_ack(addr, RECV_SEQ)
                # Responding to a DC Request From Client     
                if msg_split[1]=="DISCONNECT" and msg_split[2]=="CHAT/1.0": 
                    farewell = f"Bye {user_name}!"
                    print(f"{farewell} : {client[1]}")
                    # remove from client_list
                    client_list.remove(client)
                    # Check if client successfully removed from list
                    if get_addr_by_username(user_name)==None:
                        print(f"{user_name} Successfully removed")

                # Normal Messaging  Print Message #
                else:
                    print("\n - - - - - -")
                    print(f'{RECV_TEXT}')
                    print(f"\nSeq Num We got: {client[2]}")
                    # flip expected sequence number 
                    flip_seq(client[1])
                    print(f"\nNext Expecting Seq Num: {get_client(addr)[2]}")
                    print("\n - - - - - -\n")
                    
    # Handling corrupt packet
    else:
        print("\n # # # # # #")
        print('\nChecksums DO NOT MATCH!\n')
        print("\n # # # # # #\n")

        # send NAK to client (negative acknowledgement)
        


# Return entire client tuple corresponding to username
def get_client(adr):
    for client in client_list:
        if client[1] == adr:
            return client
    return None


# Get client socket given the username
def get_addr_by_username(user_name):
    for client in client_list:
        if client[0] == user_name:
            return client[1]
    return None

def send_ack(client_adr, sequenceNum):
    #client_adr = get_addr_by_username(user_name)

    if client_adr != None:
        # Extract client host and port info
        client_host = client_adr[0]
        client_port = client_adr[1]
        msg = "Server:ACK"
        # Encode message
        msg_encoded = msg.encode()
        # Size of encoded message
        size_msg_encoded = len(msg_encoded)

        # calculate checksum of 3 fields
        packet_tuple = (sequenceNum,size_msg_encoded,msg_encoded)
        packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s')
        packed_data = packet_structure.pack(*packet_tuple)
        checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

        # Construct packet with checksum field
        packet_tuple = (sequenceNum,size_msg_encoded,msg_encoded,checksum)
        UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
        UDP_packet = UDP_packet_structure.pack(*packet_tuple)
        
        # send msg to client
        server_sock.sendto(UDP_packet, (client_host, client_port))
    

def main():
    global server_sock
    
    
    server_sock.bind(('', 0))
    HOST = server_sock.getsockname()[0]
    PORT = server_sock.getsockname()[1]
    server_sock.setblocking(False)
    print(f"\n- - -\nWaiting For Clients\n- - -\nHost:{HOST}\nPort:{PORT}\n- - -\n")
    sel.register(server_sock, selectors.EVENT_READ, get_packet)
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
    

    

if __name__ == '__main__':
    main()