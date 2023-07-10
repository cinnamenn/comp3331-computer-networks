# comp3331-computer-networks
**Background of Assignment**
----
Purpose: sending STP segment through UDP protocol
There are individual sender and receiver, the sender send out the packet and receiver respond it with the ACK.
Packets might be lost while transferring, user can manipuate the possibility of losing rate by the command.

<img 
  width="849" alt="Screen Shot 2023-07-10 at 2 36 03 pm" src="https://github.com/cinnamenn/comp3331-computer-networks/assets/132876315/8775dd0d-b00f-4c43-8c28-08cf0495bb95"
  />


**Segments to be sent** 
----
STP segments contatin type(2 bytes), seqno(2 bytes), and date(0 to MSS bytes -> depends on window size)

**The types of segment with it states value:**

DATA (0): After the connection build successfully, the data starts to be sent by sender.

ACK (1): When receiver recieve the packet from sender, it send ACK packet with it's corresponding seqno.

SYN(2): The first packet sent by sender to build the connection with receiver.

FIN(3): When sender recieve the last data ACK, it will sent out the FIN to receiver.

RESET(4): If the receiver didnt receive the same segment 3 times, the RESET is sent by receiver and it will close the connection straight after.


**Stages**
----

**Building handshake**
(Open the server of the receiver then sender) ->  the receier will wait for the SYN packet from sender.
The sender random generate the initial seqno and sent out the "SYN packet"
If the receiver recieve the "SYN packet", it sent a "SYN ACK" back to the sender.

