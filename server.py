import socket
import os
import selectors
import struct
import hashlib
import signal
import errno
import re
import sys

UDP_IP = "localhost"
UDP_PORT = 54321


sel = selectors.DefaultSelector()
client_list = []
client_count = 0

STREAM_BUFFER_SIZE =1024
MAX_STRING_SIZE = 256

unpacker = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
packer = struct.Struct(f'I I {MAX_STRING_SIZE}s')


def verify_packet(UDP_packet):
# Extract fields from packet
    received_sequence = UDP_packet[0]
    received_size = UDP_packet[1]
    received_data = UDP_packet[2]
    received_checksum = UDP_packet[3]

    # Calculate and confirm checksum
    values = (received_sequence,received_size,received_data)
    packed_data = packer.pack(*values)
    computed_checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

    if received_checksum == computed_checksum:
        print('Received and computed checksums match, so packet can be processed')
        received_text = received_data[:received_size].decode()
        print(f'Message text was:  {received_text}')
        # send ACK to client (positive acknowledgement)
    else:
        print('Received and computed checksums do not match, so packet is corrupt and discarded')
        # send NAK to client (negative acknowledgement)


def get_packet(sock, mask):
    # Receive and unpack the packet
    received_packet, addr = sock.recvfrom(STREAM_BUFFER_SIZE)
    UDP_packet = unpacker.unpack(received_packet)

    verify_packet(UDP_packet)
    print(f"\nConnection from: {addr}")


    

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    sel.register(sock, selectors.EVENT_READ, get_packet)
    print("Server set up")

    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

if __name__ == '__main__':
    main()