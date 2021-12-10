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
# if server receives non corrupt packet & correct expected_seq num -> send ack to client and set timer 
# if server receives corrupt packet or wrong expected_seq num -> send nak to client 
## sender must retransmit corrupt packet upon receiving nak from server


server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

# Buffer size
STREAM_BUFFER_SIZE =1024
MAX_STRING_SIZE = 256

expected_seq = 0
server_seq = 0



sel = selectors.DefaultSelector()




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



'''
Functions
'''
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


# Check if packet recieved is duplicate by comparing its sequence number to the expected sequence number
def is_duplicate(packet):
    fields = unpack_packet(packet)
    recieved_num = fields[0]
    
    if(get_expected_seq()==recieved_num):
         return False
    else:
        print(f"Expected{get_expected_seq()} but got{recieved_num}")
        print("\n duplicate")
        return True

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


def increment_expected_seq():
    global expected_seq
    expected_seq = expected_seq+1

def get_expected_seq():
    return expected_seq%2

def increment_server_seq():
    global server_seq
    server_seq = server_seq+1

def get_server_seq():
    return server_seq%2

def get_opposite(num):
    if num ==0:
        return 1
    else:
         return 0

def make_ack(sequence):
    ack = sequence
    # formatting of message string
    msg = "Server:"
    # Encode message
    msg_encoded = msg.encode()
    # Size of encoded message
    size_msg_encoded = len(msg_encoded)

    # calculate checksum of 4 fields
    packet_tuple = (get_server_seq(),size_msg_encoded,msg_encoded, ack)
    packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s I')
    packed_data = packet_structure.pack(*packet_tuple)
    checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")

    # Construct packet with checksum field
    packet_tuple = (get_server_seq(),size_msg_encoded,msg_encoded,ack,checksum)
    UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s I 32s')
    UDP_packet = UDP_packet_structure.pack(*packet_tuple)
    
    return UDP_packet


def get_packet(sock, mask):
    global client_list, server_seq
    server_sock.setblocking(True)
    # Receive the packet and address of client
    received_packet, addr = sock.recvfrom(STREAM_BUFFER_SIZE)
    # if packet is good then send an ack
    if is_corrupt(received_packet)==False and is_duplicate(received_packet)==False:
        fields = unpack_packet_decoded_text(received_packet)
        print(f"{fields[2]}")
        ack_msg = make_ack(fields[0])
        server_sock.sendto(ack_msg, addr)
        increment_expected_seq()
        print(f"Next will expect: {get_expected_seq()}")   
        print("Sending ack") 
    else:
        print("Bad msg")
        num = get_expected_seq()
        num1 = get_opposite(num)
        ack_msg = make_ack(num1)
        server_sock.sendto(ack_msg, addr)
    increment_server_seq()
    server_sock.setblocking(False)
  

def main():
    global server_sock

    server_sock.bind(('localhost', 55555))
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