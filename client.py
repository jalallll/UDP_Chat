import socket
import os
import select
import struct
import hashlib
import signal
import errno
import re
import sys

UDP_IP = "localhost"
UDP_PORT = 54321

STREAM_BUFFER_SIZE =1024
MAX_STRING_SIZE = 256
SEQUENCE_NUMBER = 0

USER_NAME = "Client"

PREV_PACKET = 0

unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s')



def flip_sequence_number():
    if(SEQUENCE_NUMBER==0):
        SEQUENCE_NUMBER=1
    if(SEQUENCE_NUMBER==1):
        SEQUENCE_NUMBER=0


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind(('', 0))
    sock.setblocking(False)
    
    while 1:
        readers, writers, errors = select.select([sys.stdin, sock], [], [])
        for reader in readers:

            # Reading from socket
            if reader == sock:
                # Receive and unpack the packet
                received_packet, addr = sock.recvfrom(STREAM_BUFFER_SIZE)
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
                msg = f"{USER_NAME}: {msg}"
                # make sure msg is less than 256 bits
                msg_encoded = msg.encode()
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
                sock.sendto(UDP_packet, (UDP_IP, UDP_PORT))
                PREV_PACKET = UDP_packet

                # set blocking to true (so program waits for response) and set a timeout for 1 second

                # wait for ack0 or 1 - depends on sequence number

                # if proper ack received then flip seq num
                #flip sequence number
                
                

if __name__ == '__main__':
    main()