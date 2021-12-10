import socket
import os
import selectors
import struct
import hashlib
import signal
import errno
import re
import sys
import argparse
from urllib.parse import urlparse


sel = selectors.DefaultSelector()

###############################################################
########### Global Variables 
###############################################################

# Setup UDP socket
CLIENT_SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

STREAM_BUFFER_SIZE =1024
MAX_STRING_SIZE = 256
SEQUENCE_NUMBER = 0

HOST = ""
PORT = ""

USER_NAME = "Client"


'''
Packet structure
[0] = sequence number (I) -> Either 0 or 1
[1] = size (I)
[2] = data (256 S)
[3] = ACK (I) -> 0 or 1 corresponding to packet # or 3 if not an ACK
[4] = checksum
'''
unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s I 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s I')


#
###############################################################
########### Functions 
###############################################################

# Prevent client from using "server" as their username
def check_user_name(USER_NAME):
    if "server" in USER_NAME.lower() or "all" in USER_NAME.lower():
        er_str = "\n#############################################################\n######################### ERROR #############################\n#############################################################\n"
        print(f"{er_str}The username you chose: ' {USER_NAME} '\n\nYour username can't be any derivative of the string 'Server' or 'all'!!\n{er_str}")
        sys.exit()

# Parse username, server hostname, server port from command line args
def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("USER_NAME", help="USER_NAME name for this USER_NAME on the chat service")
    parser.add_argument("server", help="Server URL: chat://host:port")
    args = parser.parse_args()
    try:
        server_address = urlparse(args.server)
        if ((server_address.scheme != 'chat') or (server_address.port == None) or (server_address.hostname == None)):
            raise ValueError
        HOST = server_address.hostname
        PORT = server_address.port
        USER_NAME = args.USER_NAME
        return (USER_NAME, HOST, PORT)
    except ValueError:
        print('Error:  Invalid server.  Enter a URL of the form: chat://host:port')
        sys.exit()

# Invert sequence number 
def flip_sequence_number():
    global SEQUENCE_NUMBER
    SEQUENCE_NUMBER = (SEQUENCE_NUMBER + 1)%2

def get_sequence_number():
    global SEQUENCE_NUMBER
    return SEQUENCE_NUMBER

# unpack 5 field packet and return encoded data
def unpack_packet(packed_packet):
    UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s I 32s')
    packet = UDP_packet_structure.unpack(packed_packet)
    # return values in packet
    sequence_number = packet[0]
    size = packet[1]
    encoded_data = packet[2] # need to decode it
    ACK = packet[3]
    checksum = packet[4]
    return (sequence_number, size, encoded_data, ACK, checksum)

# return decoded text
def unpack_packet_decoded_text(packed_packet):
    sequence_number, size, encoded_data, ACK, checksum = unpack_packet(packed_packet)
    data = encoded_data
    decoded_text = data[:size].decode()
    return (sequence_number, size, decoded_text, ACK, checksum)

# return true if corrupt packet
def is_corrupt(packed_packet):
    # get 5 fields, last field is checksum
    fields = unpack_packet(packed_packet)
    recv_checksum = fields[4]
    # new tuple excluding checksum field
    # exclude checksum in computation
    values = (fields[0], fields[1], fields[2], fields[3])
    packer = struct.Struct(f'I I {MAX_STRING_SIZE}s I') #pack data
    packed_data = packer.pack(*values)
    computed_checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")
    # compare recieved and computed checksum
    if recv_checksum != computed_checksum:
        return True
    else:
        return False

# check if ack received corresponds to previous packet sent
# Return true if current inbound packet (from server) acknowledges the previous outgoing packet (from client to server)
def is_ack(sent_packed_packet, received_packed_packet):
    # check if inbound packet is corrupt
    if(is_corrupt(received_packed_packet)==True):
        return False
    # Extract fields from previous outgoing packet & the new inbound packet
    sent_values = unpack_packet(sent_packed_packet)
    recv_values = unpack_packet(received_packed_packet)
    # sequence # of outgoing packet must equal inbound ack
    sent_sequence_num = sent_values[0]
    recv_ack = recv_values[3]
    if(sent_sequence_num==recv_ack):
        return True
    else:
        return False

def construct_msg_packet(msg):
    # ack field = 3 (not sending ack or nak)
    ack = 3
    sequence_num = get_sequence_number()
    # formatting of message string
    msg = f"{USER_NAME}: {msg}"
    # Encode message
    msg_encoded = msg.encode()
    # Size of encoded message
    size_msg_encoded = len(msg_encoded)

    # calculate checksum of 4 fields
    packet_tuple = (sequence_num,size_msg_encoded,msg_encoded, ack)
    packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s I')
    packed_data = packet_structure.pack(*packet_tuple)
    checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

    # Construct packet with checksum field
    packet_tuple = (sequence_num,size_msg_encoded,msg_encoded,ack,checksum)
    UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s I 32s')
    UDP_packet = UDP_packet_structure.pack(*packet_tuple)
    print(f"used seq{sequence_num}")
    return UDP_packet


def send_msg(sock,mask):
    msg = sys.stdin.readline()
    # set blocking to true
    CLIENT_SOCK.setblocking(True)
    loop = True
    counter = 0
    global HOST, PORT

    # construct packet
    outgoing_packet = construct_msg_packet(msg)

    # Temp vars
    old_seq = get_sequence_number()
    flip_sequence_number()
    new_seq = get_sequence_number()
    

    while loop == True:
        counter = counter + 1
        # send packet to server
        CLIENT_SOCK.sendto(outgoing_packet, (HOST, PORT))

        print(f"\n - - send_msg() - - -Iteration {counter}")
        print(f"{msg}")
        print(f"Sent SEQ-NUM:{old_seq}")
        print(f"New SEQ-NUM:{new_seq}")
        print(" - - waiting... - - -\n")

        # set timeout
        CLIENT_SOCK.settimeout(4)

        print("timeout done..")

        # wait for ack0 or 1 - depends on sequence number
        recv_pkt, adr = CLIENT_SOCK.recvfrom(STREAM_BUFFER_SIZE)
        host = adr[0]
        port = adr[1]
        
        if is_ack(outgoing_packet, recv_pkt)==True:
            loop = False

    CLIENT_SOCK.setblocking(False)
    CLIENT_SOCK.settimeout(None)




def main():
    global SEQUENCE_NUMBER, CLIENT_SOCK, USER_NAME, STREAM_BUFFER_SIZE, MAX_STRING_SIZE, HOST, PORT
    
    # Parse username, host ip, port number from command
    USER_NAME, HOST, PORT = parser()

    # Check to see if user name is valid
    check_user_name(USER_NAME)

    
    CLIENT_SOCK.setblocking(False)

    # Watch for ctrl+ c events
    def signal_handler(sig, frame):
        print('\nInterrupt received, shutting down ...')
        message=f'DISCONNECT CHAT/1.0'
        message.strip('\n')
        # send DC message to server
        send_msg(message)
        # wait for ack before exit
        sys.exit()
        
    # Initialize signal

    signal.signal(signal.SIGINT, signal_handler)


    #sel.register(CLIENT_SOCK, selectors.EVENT_READ, handle_message_from_server)
    sel.register(sys.stdin, selectors.EVENT_READ, send_msg)
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

# Parse username, server hostname, server port from command line args
def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("USER_NAME", help="USER_NAME name for this USER_NAME on the chat service")
    parser.add_argument("server", help="Server URL: chat://host:port")
    args = parser.parse_args()
    try:
        server_address = urlparse(args.server)
        if ((server_address.scheme != 'chat') or (server_address.port == None) or (server_address.hostname == None)):
            raise ValueError
        HOST = server_address.hostname
        PORT = server_address.port
        USER_NAME = args.USER_NAME
        return (USER_NAME, HOST, PORT)
    except ValueError:
        print('Error:  Invalid server.  Enter a URL of the form: chat://host:port')
        sys.exit()                

if __name__ == '__main__':
    main()