import socket
import os
import select
import struct
import hashlib
import signal
import errno
import re
import sys
import argparse
from urllib.parse import urlparse

# todo
# send a packet and wait for ack or NAK (set blocking = true)
# # if NAK then resend prev packet
# # if ack then send new packet

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
PREV_PACKET = ""

USER_NAME = "Client"

PREV_SEQ = 0

unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s')

#
###############################################################
########### Functions 
###############################################################
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
    if(SEQUENCE_NUMBER==0):
        SEQUENCE_NUMBER=1
    else:
        SEQUENCE_NUMBER=0

def send_msg(msg):
    global HOST, PORT, PREV_PACKET, SEQUENCE_NUMBER
    
    # formatting of message string
    msg = f"{USER_NAME}: {msg}"
    # Encode message
    msg_encoded = msg.encode()
    # Size of encoded message
    size_msg_encoded = len(msg_encoded)

    # calculate checksum of 3 fields
    packet_tuple = (SEQUENCE_NUMBER,size_msg_encoded,msg_encoded)
    packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s')
    packed_data = packet_structure.pack(*packet_tuple)
    checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

    # Construct packet with checksum field
    packet_tuple = (SEQUENCE_NUMBER,size_msg_encoded,msg_encoded,checksum)
    UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
    UDP_packet = UDP_packet_structure.pack(*packet_tuple)
    
    # send msg to server
    CLIENT_SOCK.sendto(UDP_packet, (HOST, PORT))
    
    # save the packet
    PREV_PACKET = UDP_packet

    print("\n - - - - - -")
    # print sent message and sequence number
    print(f"{msg}")
    print(f"\nSequence Number:{SEQUENCE_NUMBER}")

    # flip sequence number and print the new sequence number
    flip_sequence_number()
    print(f"\nNew Sequence Number:{SEQUENCE_NUMBER}")
    print(" - - - - - -\n")


    # set blocking to true (so program waits for response) and set a timeout for 1 second

    # wait for ack0 or 1 - depends on sequence number

    # if proper ack received then flip seq num
    #flip sequence number


def main():
    global SEQUENCE_NUMBER, CLIENT_SOCK, USER_NAME, STREAM_BUFFER_SIZE, MAX_STRING_SIZE, HOST, PORT
    
    # Parse username, host ip, port number from command
    USER_NAME, HOST, PORT = parser()

    CLIENT_SOCK.setblocking(False)

    # Watch for ctrl+ c events
    def signal_handler(sig, frame):
        print('\nInterrupt received, shutting down ...')
        message=f'DISCONNECT CHAT/1.0'
        message.strip('\n')

        # send DC message to server
        send_msg(message)
        sys.exit()
        
        
        
    
    # Initialize signal
    signal.signal(signal.SIGINT, signal_handler)


    while 1:
        readers, writers, errors = select.select([sys.stdin, CLIENT_SOCK], [], [])
        for reader in readers:

            # Reading from socket
            if reader == CLIENT_SOCK:
                # Receive and unpack the packet
                received_packet, addr = CLIENT_SOCK.recvfrom(STREAM_BUFFER_SIZE)
                UDP_packet = unpacker.unpack(received_packet)

                # Extract fields from packet
                received_sequence = UDP_packet[0]
                received_size = UDP_packet[1]
                received_data = UDP_packet[2]
                received_checksum = UDP_packet[3]
                print(f"\nConnection from: {addr}\nPacket Data: {received_data}")

                # Calculate and confirm checksum
                values = (received_sequence,received_size,received_data)
                packed_data = packer.pack(*values)
                computed_checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

                if received_checksum == computed_checksum:
                    print('Received and computed checksums match, so packet can be processed')
                    received_text = received_data[:received_size].decode()
                    print(f'Message text was:  {received_text}')
                else:
                    print('Received and computed checksums do not match, so packet is corrupt and discarded')
            # Reading from standard input
            else:
                
                msg = sys.stdin.readline()
                
                send_msg(msg)
                
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