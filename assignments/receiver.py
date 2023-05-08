"""
    Sample code for Receiver
    Python 3
    Usage: python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp
    coding: utf-8

    Notes:
        Try to run the server first with the command:
            python3 receiver_template.py 9000 10000 FileReceived.txt 1 1
        Then run the sender:
            python3 sender_template.py 11000 9000 FileToReceived.txt 1000 1

    Author: Rui Li (Tutor for COMP3331/9331)
"""
# here are the libs you may find it useful:
import datetime, time  # to calculate the time delta of packet transmission
import logging, sys  # to write the log
import socket  # Core lib, to send packet via UDP socket
from threading import Thread  # (Optional)threading will make the timer easily implemented
import random  # for flp and rlp function

BUFFERSIZE = 1024


class Receiver:
    def __init__(self, receiver_port: int, sender_port: int, filename: str, flp: float, rlp: float) -> None:
        '''
        The server will be able to receive the file from the sender via UDP
        :param receiver_port: the UDP port number to be used by the receiver to receive PTP segments from the sender.
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver.
        :param filename: the name of the text file into which the text sent by the sender should be stored
        :param flp: forward loss probability, which is the probability that any segment in the forward direction (Data, FIN, SYN) is lost.
        :param rlp: reverse loss probability, which is the probability of a segment in the reverse direction (i.e., ACKs) being lost.

        '''
        self.address = "127.0.0.1"  # change it to 0.0.0.0 or public ipv4 address if want to test it between different computers
        self.receiver_port = int(receiver_port)
        self.sender_port = int(sender_port)
        self.server_address = (self.address, self.receiver_port)
        self.filename = filename
        self.flp = float(flp)
        self.rlp = float(rlp)
        self.num = 0
        self.word = dict()
        self.no1 = 0
        self.no2 = 0
        self.no3 = 0
        self.no4 = 0
        self.no5 = 0
        open(self.filename, "w").close()
        open("Receiver_log.txt", "w").close()
        # init the UDP socket
        # define socket for the server side and bind address
        logging.debug(f"The sender is using the address {self.server_address} to receive message!")
        self.receiver_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.receiver_socket.bind(self.server_address)
        self.receiver_socket.setblocking(2)
        # two way hand-shake
        self.receiver_handshake()
        pass

    def run(self) -> None:
        '''
        This function contain the main logic of the receiver
        '''
        while True:
            # try to receive any incoming message from the sender
            self.receive()   
     
    def receive(self):
        try:
            incoming_message, sender_address = self.receiver_socket.recvfrom(BUFFERSIZE)
        except:
            exit(0)
        _ran = random.uniform(0,1)
        if self.flp <= _ran:
            typ, seq, data = self.decode_message(incoming_message)
            # DATA
            if typ == 0:
                self.num += 1
                logging.debug(f"receive {self.num} packets, seqno: {seq}")
                if seq not in self.word:
                    self.word[seq] = data
                    self.no1+= len(data)
                    self.no2+= 1
                else: # dup
                    self.no3+= 1
                # save message into the file
                self.sent(1, (seq +len(data))%65536, sender_address)
            # SYN
            if typ == 2:
                logging.debug(f"receive SYN {seq} from sender ")
                self.sent(1,(seq+1)%65536, sender_address)
            # CLOSE connection
            if typ == 3: 
                logging.debug(f"receive FIN {seq} from sender ")
                self.write_file(self.no1, self.no2, self.no3, self.no4, self.no5)
                self.sent(1, (seq+1)%65536, sender_address)
                with open(self.filename, "a") as file:
                    mykeys = sorted(self.word.keys())
                    for key in mykeys:
                        file.write(self.word[key])
                exit(0)
            # RESET
            if typ == 4:
                print("RESET, close connection")
                exit(1)
        else:
            self.no4 += 1
            logging.DEBUG(f"lost packet")
    def sent(self, typ, seqno, sender_address):
        # reply "ACK" once receive any message from sender
        new_message = self.encode_message(typ, seqno, data = '')
        if self.rlp <= random.uniform(0,1):
            self.receiver_socket.sendto(new_message,
                                        sender_address)
            logging.debug(f"sent ACK seq:{seqno}")
        else:
            self.no5 += 1

    def receiver_handshake(self):
        while True:
            self.receive()
        pass

    def encode_message(self, typ: int, seqno: int, data: str):
        return typ.to_bytes(length = 2, byteorder ='big') + seqno.to_bytes(length = 2, byteorder ='big') + data.encode()

    def decode_message(self, msg):
        return int.from_bytes(msg[0:2], byteorder ='big'), int.from_bytes(msg[2:4], byteorder ='big'), msg[4:].decode()

    def write_file(self, no1: int, no2: int, no3: int, no4: int, no5: int):
        with open ("Receiver_log.txt", "a") as file:

            file.write(f"Amount of(original) Data Received(in bytes):{self.no1}\n")
            file.write(f"Number of(original) Data Segments Received:{self.no2}\n")
            file.write(f"Number of duplicate Data segments received:{self.no3}\n")
            file.write(f"Number of Data Segments Drop:{self.no4}\n")
            file.write(f"Number of ACK segements dropped:{self.no5}\n")


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        # filename="Receiver_log.txt",
        stream=sys.stderr,
        level=logging.WARNING,
        format='%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp ======\n")
        exit(0)

    receiver = Receiver(*sys.argv[1:])
    receiver.run()
