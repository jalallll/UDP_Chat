import socket
import struct
import hashlib

# Hard code location of the server.  Not what we'll want to be doing in the assignment,
# but okay for an example like this.

UDP_IP = "localhost"
UDP_PORT = 54321

# Define a maximum string size for the text we'll be sending along.

MAX_STRING_SIZE = 256

# The test data we want to be sending.  In this case, some text.

TEST_DATA = "This is some test data.  Whee!"

# Our main function.

def main(): 

    

    sequence_number = 0
    data = TEST_DATA.encode()
    size = len(data)
 
   

    packet_tuple = (sequence_number,size,data)
    packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s')
    packed_data = packet_structure.pack(*packet_tuple)
    checksum =  bytes(hashlib.md5(packed_data).hexdigest(), encoding="UTF-8")


    # Now we can construct our actual packet.
    packet_tuple = (sequence_number,size,data,checksum)
    UDP_packet_structure = struct.Struct(f'I I {MAX_STRING_SIZE}s 32s')
    UDP_packet = UDP_packet_structure.pack(*packet_tuple)


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

    # send msg to server
    sock.sendto(UDP_packet, (UDP_IP, UDP_PORT))

if __name__ == '__main__':
    main()
