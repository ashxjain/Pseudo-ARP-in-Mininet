Pseudo-ARP-in-Mininet
=====================

* This is a research project based on the following sigcomm paper:
  "PortLand: A Scalable Fault-Tolerant Layer 2, Data Center Network Fabric, University of California San Diego"
* There are many issues faced in data center technology like fault tolerance and efficiency, which can be overcome by leveraging knowledge about the baseline topology and avoiding broadcast-based routing protocols altogether. We take the approach of SDN in solving these issues. Software Defined Networking (SDN) is an approach to computer networking which allows network administrators to manage network services through abstraction of lower level functionality. To implement SDN we use openflow protocol for the control plane to communicate with the data plane.

* Design requirements of common data centers are easy migration of VMs, minimal switch configuration, efficient communication along forwarding paths, no forwarding loops and fast and effective failure detection. With scaling data centers, there come problems in achieving these requirements. Hence there is a need for a large, layer 2 topology. Such a topology is plug and play and requires minimal configuration.
The approach of fat tree topology introduces many scaling problems:
  - State required to implement the layer 2 forwarding at all the switches in the data center, potentially for all the hosts.
  - Flooding of ARP requests and other broadcast traffic across the entire topology
  - Slow upgradation of address mapping when VMs migrate from part of the data center network to another.
SDN helps to solve many of these problems.

* The goal of this project is to deliver scalable layer 2 routing, forwarding, and addressing for data center network environments. We leverage the observation that in data center environments, the baseline multi-rooted network topology is known and relatively fixed. Building and maintaining data centers with tens of thousands of compute elements requires modularity, advance planning, and minimal human interaction. Thus, the baseline data center topology is unlikely to evolve quickly. When expansion does occur to the network, it typically involves adding more “leaves" (e.g., rows of servers) to the multi-rooted tree topology.

* This project is at its initial phase, final implementation is not yet done. In this initial phase, I have implemented proxy ARP feature to avoid unnecessary broadcasting. 

System architecture
-------------------
* Mininet -Mininet creates a realistic virtual network, running real kernel, switch and application code, on a single machine (VM, cloud or native), in seconds, with a single command
* POX - POX is a networking software platform written in Python. POX started as an OpenFlow controller, but can now also function as an OpenFlow switch, and can be useful for writing networking software in general.
* Wireshark - Wireshark is a network protocol analyzer for Unix and Windows. 

Pseudo code
------------
For each packet from the switch:
  1) Use source address and switch port to update address/port table and IP/MAC table
  2) Is destination broadcast?
     Yes:
        2a) Look for MAC address for the IP address in IP/MAC table
		    2.1) Found:
		    	 Instruct switch to send ARP response that ARP request
		    2.2) Not Found:
				 Flood the packet
  3) Port for destination address in our address/port table?
     No:
        3a) Flood the packet
            DONE
  4) Is output port the same as input port?
     Yes:
        4a) Drop packet and similar ones for a while
  5) Install flow table entry in the switch so that this
     flow goes out the appropriate port
     5a) Send the packet out appropriate port

Results Discussion
------------------
* Considering a tree network topology with a depth of 2 and fanout of 2. 
* Normal l2_learning switch: This code comes with POX
  * h1 ping -c 2 h4:
  * h2 ping -c 4 h4
* For  h2, there is unnecessary flooding of packet, since that MAC address is known to controller, this happened because the ARP request h2 sends contains destination MAC address as broadcast address.
* Optimized L2_learning switch: l2_learning.py code in POX is modified based on the above algorithm
  * h1 ping -c 2 h4
  * h2 ping -c 4 h4
* Unnecessary flooding of packet is removed by maintaining an IP to MAC table, hence when the destination MAC address of the ARP request packet is broadcast address, if that destination IP address is in the IP to MAC table, then controller instructs switch to send an ARP response to the request. 

Conclusion
----------
Efficiency, fault tolerance, flexibility and manageability are all significant concerns with general-purpose Ethernet and IP-based protocols. By using Pseudo-ARP we can overcome all of these. It is my hope that through optimizations like these, data center networks can become more flexible, efficient, and fault tolerant.

Further Enhancements
---------------------
Since I’m new to this field of networking, it took me a while to just understand the concepts. Now that i have understood the concept and implemented the initial step to optimization, following advancements will be done to the project:
  * Understanding ICMP time
  * Final implementation of Pseudo-ARP

Bibliography
---------------
* Online resources:
  * https://github.com/mininet/mininet/wiki/Introduction-to-Mininet
  * https://github.com/noxrepo/pox
  * http://yuba.stanford.edu/cs244wiki/index.php/Overview
  * http://archive.openflow.org/wk/index.php/OpenFlow_Tutorial
* Technical papers:
  * Portland: A Scalable Fault-Tolerant Layer 2, Data Center Network Fabric, University of California San Diego

