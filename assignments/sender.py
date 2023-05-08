"""
    Sample code for Sender (multi-threading)
    Python 3
    Usage: python3 sender.py receiver_port sender_port FileToSend.txt max_recv_win rto
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
import random
from threading import Thread  # (Optional)threading will make the timer easily implemented

BUFFERSIZE = 1024


class Sender:
    def __init__(self, sender_port: int, receiver_port: int, filename: str, max_win: int, rot: int) -> None:
        '''
        The Sender will be able to connect the Receiver via UDP
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver
        :param receiver_port: the UDP port number on which receiver is expecting to receive PTP segments from the sender
        :param filename: the name of the text file that must be transferred from sender to receiver using your reliable transport protocol.
        :param max_win: the maximum window size in bytes for the sender window.
        :param rot: the value of the retransmission timer in milliseconds. This should be an unsigned integer.
        '''
        self.sender_port = int(sender_port)
        self.receiver_port = int(receiver_port)
        self.sender_address = ("127.0.0.1", self.sender_port)
        self.receiver_address = ("127.0.0.1", self.receiver_port)
        self.rot = int(rot)/1000
        self.seq_dict = dict()
        self.prev_isn = 0
        self.isn = random.randint(0, 65536)
        self.last_seq = None
        self.fin_seq = 0
        self.cur_ack_seq = 0
        self.check_last_seq = False
        self.check_fin_seq = False
        self.max_win = int(max_win)
        self.ack_list = list()
        self.listen_list = list()
        self.timer = 0
        self.filename = filename
        open("Sender_log.txt", "w").close()

        # init the UDP socket
        logging.debug(f"The sender is using the address {self.sender_address}")
        self.sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sender_socket.setblocking(0)
        self.sender_socket.bind(self.sender_address)
        # handshake here
        self.sender_handshake(self.rot)
        # (Optional) start the listening sub-thread first
        self._is_active = True  # for the multi-threading
        # listen_thread = Thread(target=self.listen)
        # listen_thread.setDaemon(True)
        # listen_thread.start()
        pass

    def sender_handshake(self, rot):
        # sent out SYN message
        new_message = self.encode_message(typ=2, seqno=self.isn, data='')
        self.sender_socket.sendto(new_message, self.receiver_address)
        self.timer = time.time()
        self.write_file(0, 2, self.isn, 0)
        start = time.time()
        logging.debug(f"send out SYN, seqno: {self.isn}")
        timeout = 0
        # check whether receive the SYN ACK
        retrans_num = 0
        incoming_message = None
        while True:
            try:
                incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)  
                self.write_file(time.time()-self.timer, 1, self.isn, 0)                
            except:
                end = time.time()
                timeout = end - start
                if timeout > self.rot:
                    if retrans_num < 3:
                        retrans_num += 1
                        self.sender_socket.sendto(new_message, self.receiver_address)
                        self.write_file(time.time()-self.timer, 2, self.isn, 0)
                        start = time.time()
                        logging.debug(f"retrainsmit SYN {retrans_num} times")
                        continue
                    else:
                        new_message = self.encode_message(typ=4, seqno=0, data='')
                        self.sender_socket.sendto(new_message, self.receiver_address)
                        self.write_file(time.time()-self.timer, 4, self.isn, 0)
                        exit(1)
            if incoming_message:
                tep, seq, data = self.decode_message(incoming_message)
                self.cur_ack_seq = seq
                logging.debug(f"receive SYN ACK from receiver, successfully handshake")
                break
        # if successfully receive the SYN ACK, isn + 1 for the SYN message
        self.isn = (self.isn + 1)%65536        
        pass

    def ptp_open(self):
        # todo add/modify codes here
        # send a greeting message to receiver
        message = "Greetings! COMP3331."
        self.sender_socket.sendto(message.encode("utf-8"), self.receiver_address)
        pass

    def encode_message(self, typ: int, seqno: int, data: str):
        return typ.to_bytes(length = 2, byteorder = 'big') + seqno.to_bytes(length = 2, byteorder = 'big') + data.encode()

    def decode_message(self, msg):
        return int.from_bytes(msg[0:2], byteorder = 'big'), int.from_bytes(msg[2:4], byteorder ='big'), msg[4:].decode()

    def ptp_send(self):
        # send a file
        sent_first_pck = False
        with open(self.filename,"r") as file:
            i = 0
            end = 0
            start = time.time()
            timeout = 0
            retrans_num = dict()
            new_message = None
            remain_window = None        
            counter = 1
            incoming_message = None
            while True:
                if self.last_seq != None and len(self.ack_list) == 0:
                    break
                try:
                    incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)
                    self.write_file(time.time()-self.timer, 1, self.isn, 0)     
                    tep, seq, data = self.decode_message(incoming_message)
                    try:
                        self.ack_list.remove(seq)
                    except: 
                        pass 
                    # check the current ACK seq
                    self.cur_ack_seq = seq
                    # Last DATA ACK
                    logging.debug(f"[listen] last seq = {self.last_seq}, seq = {seq}")
                    logging.debug(f"[listen] receive {counter} DATA ACK {seq} from receiver")
                    counter += 1
                except:
                    pass
                if self.check_last_seq == True:
                    break
                end = time.time()
                timeout = end - start 
                # read 1000 bytes at once
                if timeout <= self.rot:
                    if len(self.ack_list) == 0:
                        remain_window = self.max_win
                    else:
                        remain_window =  self.max_win - (self.isn - min(self.ack_list))
                    if sent_first_pck == False or (remain_window > 0 and  remain_window <= self.max_win and self.last_seq == None):
                        content = file.read(1000)
                        if content: 
                            new_message = self.encode_message(typ=0, seqno=self.isn, data=content)
                            
                            self.isn = (self.isn + len(content))%65536
                            self.sender_socket.sendto(new_message, self.receiver_address)
                            self.write_file(time.time()-self.timer, 0, self.isn, len(content))
                            sent_first_pck = True
                            self.seq_dict[self.isn] = new_message
                            retrans_num[self.isn] = 0
                            self.ack_list.append(self.isn)
                            start = time.time()
                            logging.debug(f"sent out {i+1} data seqno: {self.isn}")
                            i += 1
                        # if no more content to be sent, move to close stage
                        else:
                            logging.debug(f"sent {i} packets, done.")   
                            self.last_seq = (self.isn)%65536
                            self.fin_seq = self.last_seq+2
                # timeout and retransmit
                # if we didnt receive the ACK, the return of current ACK seq < data isn that we want to sent out
                elif len(self.ack_list) > 0:
                    if retrans_num[min(self.ack_list)] < 3:
                        retrans_num[min(self.ack_list)] += 1
                        self.sender_socket.sendto(self.seq_dict[min(self.ack_list)], self.receiver_address)
                        self.write_file(time.time()-self.timer, 0, self.isn, len(content))
                        start = time.time()
                        logging.debug(f"retrainsmit DATA {retrans_num[min(self.ack_list)]} times")
                        continue
                    else:
                        new_message = self.encode_message(typ=4, seqno=0, data='')
                        self.sender_socket.sendto(new_message, self.receiver_address)
                        self.write_file(time.time()-self.timer, 4, self.isn, 0)
                        logging.debug(f"exit the program")
                        exit(1)

    def ptp_close(self):
         # FIN
        new_message = self.encode_message(typ=3, seqno=self.isn + 1, data='')
        self.isn = self.isn + 2
        self.sender_socket.sendto(new_message, self.receiver_address)
        self.write_file(time.time()-self.timer, 3, self.isn, 0)
        start = time.time()
        logging.debug(f"sender sent FIN, seq {self.isn}")
        timeout = 0
        retrans_num = 0
        while True:
            try:
                incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)
                self.write_file(time.time()-self.timer, 1, self.isn, 0)
                tep, seq, data = self.decode_message(incoming_message)

                logging.debug(f"seqno = {seq}, isn = {self.isn}")
                if seq == self.isn:
                    logging.debug(f"receive both data ACK and FIN ACK, Close connection")
                    break
            except:
                pass
            end = time.time()
            timeout = end - start 
            if timeout > self.rot:
                if retrans_num < 3:
                    retrans_num += 1
                    self.sender_socket.sendto(new_message, self.receiver_address)
                    self.write_file(time.time()-self.timer, 3, self.isn, 0)
                    start = time.time()
                    logging.debug(f"retrainsmit FIN {retrans_num} times")
                    continue
                else:
                    new_message = self.encode_message(typ=4, seqno=0, data='')
                    self.sender_socket.sendto(new_message, self.receiver_address)
                    self.write_file(time.time()-self.timer, 4, self.isn, 0)
                    exit(1)
        self._is_active = False  # close the sub-thread

    def write_file(self, time: float, typ: int, seq: int, data: int):
        with open ("Sender_log.txt", "a") as file:
            time = time * 1000
            # DATA
            if typ == 0:
                file.write(f"snd\t{time:.2f}\tDATA\t{seq}\t{data}\n")
            # ACK
            if typ == 1:
                file.write(f"rcv\t{time:.2f}\tACK\t{seq}\t{data}\n")
            # SYN
            if typ == 2:
                file.write(f"snd\t{time}\tSYN\t{seq}\t{data}\n")
            # FIN
            if typ == 3:
                file.write(f"snd\t{time:.2f}\tFIN\t{seq}\t{data}\n")
            # RESET
            if typ == 4:
                file.write(f"snd\t{time:.2f}\tRESET\t{seq}\t{data}\n")

    def listen(self):
        '''(Multithread is used)listen the response from receiver'''
        logging.debug("Sub-thread for listening is running")
        counter = 1
        incoming_message = None
        while self._is_active:
            #if self.last_seq != None and len(self.ack_list) > 0 and min(self.ack_list) >= self.last_seq:
                #self.check_last_seq = True
            #if len(self.ack_list) > 0 and min(self.ack_list) >= self.fin_seq:
                #self.check_fin_seq = True
            if self.check_last_seq == True and self.check_fin_seq == True:
                break 
            
            try:
                incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)
                self.write_file(self.timer-time.time(), 1, self.isn, 0) 
            except: 
                continue  
            tep, seq, data = self.decode_message(incoming_message)
            # check the current ACK seq
            self.cur_ack_seq = seq
            # FIN ACK
            if  seq == self.fin_seq:
                self.check_fin_seq = True
                logging.debug(f"[listen] receive FIN ACK {seq}, Close connection")
            else:
                # Last DATA ACK
                logging.debug(f"[listen] last seq = {self.last_seq}, seq = {seq}")
                if self.last_seq != None and seq == self.last_seq:
                    self.check_last_seq = True
                    logging.debug(f"[listen] receive Last DATA ACK {seq}, Ready to sent FIN")
                else:
                    logging.debug(f"[listen] receive {counter} DATA ACK {seq} from receiver")
                    counter += 1
                self.listen_list.append(seq)
        logging.debug(f"stop listening")  
                
  
    def run(self):
        '''
        This function contain the main logic of the receiver
        '''
        # todo add/modify codes here
        self.ptp_open()
        self.ptp_send()
        self.ptp_close()


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        # filename="Sender_log.txt",
        stream=sys.stderr,
        level=logging.WARNING,
        format='%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 sender.py sender_port receiver_port FileReceived.txt max_win rot ======\n")
        exit(0)

    sender = Sender(*sys.argv[1:])
    sender.run()

