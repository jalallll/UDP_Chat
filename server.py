import socket
import os
import selectors
import struct
import hashlib
import signal
import errno
import re
import sys

# IP and Port of server
UDP_IP = "localhost"
UDP_PORT = 54321

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
client_count = 0


unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s')


# todo 
# get_packet() use SEQ_NUM to check if packet is not dupicate

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

def is_duplicate():
    global EXPECTED_SEQ, RECV_SEQ
    if(EXPECTED_SEQ==RECV_SEQ):
         return False
    else:
         return True

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
        
def flip_expected_seq():
    global EXPECTED_SEQ
    
    if EXPECTED_SEQ == 0:
        EXPECTED_SEQ = 1
    else:
        EXPECTED_SEQ = 0

def get_packet(sock, mask):
    # Receive and unpack the packet
    received_packet, addr = sock.recvfrom(STREAM_BUFFER_SIZE)
    UDP_packet = unpacker.unpack(received_packet)
    
    # extract packet fields
    extract_packet_fields(UDP_packet)

    # Packet received is not corrupt or duplicate
    if is_corrupt() == False and is_duplicate()==False:
        print('Received and computed checksums match, so packet can be processed')
        print(f'Message text was:  {RECV_TEXT}')
        print(f"\Initial Seq Num: {EXPECTED_SEQ}")
        # flip expected sequence number 
        flip_expected_seq()
        print(f"\nExpecting Seq Num: {EXPECTED_SEQ}")
        # send ACK to client (positive acknowledgement)
    else:
        if is_corrupt() == True:
            print('\nReceived and computed checksums do not match, so packet is corrupt and discarded\n')
            # send NAK to client (negative acknowledgement)
        if is_duplicate() == True:
            print("\nDuplicate Packet!!\n")
            print(f"\nExpected Sequence Number: {EXPECTED_SEQ}\nSequence Number we got: {RECV_SEQ}")

    print(f"\nConnection from: {addr}")




    

def main():
    global server_sock
    
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    server_sock.bind((UDP_IP, UDP_PORT))
    server_sock.setblocking(False)
    print("~~\nServer set up\n~~")
    sel.register(server_sock, selectors.EVENT_READ, get_packet)
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
    

    

if __name__ == '__main__':
    main()