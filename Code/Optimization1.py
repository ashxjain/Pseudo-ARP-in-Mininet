"""
Optimization Phase 1
"""
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_bool
from pox.lib.addresses import EthAddr
import time
import pox.lib.packet.arp as arp
import pox.lib.packet as pkt
import pox.lib.packet.ethernet as ethernet
log = core.getLogger()

# We don't want to flood immediately when a switch connects.
# Can be overriden on commandline.
_flood_delay = 0

class LearningSwitch (object):

  def __init__ (self, connection, transparent):
    self.connection = connection
    self.transparent = transparent
    # Our address/port table
    self.macToPort = {}
    # Ip to Mac table
    self.ipToMac = {}
    # We want to hear PacketIn messages, so we listen
    # to the connection
    connection.addListeners(self)

    # We just use this to know when to log a helpful message
    self.hold_down_expired = _flood_delay == 0

    #log.debug("Initializing LearningSwitch, transparent=%s",
    #          str(self.transparent))

  def _handle_PacketIn (self, event):
    packet = event.parsed 
    def flood (message = None):
      """ Floods the packet """
      msg = of.ofp_packet_out()
      if time.time() - self.connection.connect_time >= _flood_delay:
        # Only flood if we've been connected for a little while...

        if self.hold_down_expired is False:
          # Oh yes it is!
          self.hold_down_expired = True
          log.info("%s: Flood hold-down expired -- flooding",
              dpid_to_str(event.dpid))

        if message is not None: log.debug(message)
        #log.debug("%i: flood %s -> %s", event.dpid,packet.src,packet.dst)
        # OFPP_FLOOD is optional; on some switches you may need to change
        # this to OFPP_ALL.
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      else:
        pass
        #log.info("Holding down flood for %s", dpid_to_str(event.dpid))
      msg.data = event.ofp
      msg.in_port = event.port
      self.connection.send(msg)
      

    def drop (duration = None):
      """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id is not None:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)

    #Controller sends flow_mod packet to switch   
    def send_packet(packet,event,port):
      msg = of.ofp_flow_mod()
      msg.match = of.ofp_match.from_packet(packet, event.port)
      msg.idle_timeout = 10
      msg.hard_timeout = 30
      msg.actions.append(of.ofp_action_output(port = port))
      msg.data = event.ofp 
      self.connection.send(msg)

    #Controller instructing switch to repy to the ARP request
    def send_arp_response(packet,match,event,dstMac):
      r = arp()
      r.opcode = arp.REPLY
      r.hwdst = match.dl_src
      r.protosrc = match.nw_dst
      r.protodst = match.nw_src
      r.hwsrc = dstMac
      e = ethernet(type=ethernet.ARP_TYPE, src=r.hwsrc, dst=r.hwdst)
      e.set_payload(r)
      msg = of.ofp_packet_out()
      msg.data = e.pack()
      msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
      msg.in_port = event.port
      event.connection.send(msg)

    #Function to extract source IP address from incoming packet
    def getSrcIp(packet):
      ipsrc = None
      arp = packet.find('arp')
      if arp is not None:
        ipsrc = str(arp.protosrc)
	return ipsrc
      ip = packet.find('ipv4')
      if ip is not None:
        ipsrc = str(ip.srcip)
        return ipsrc

    #Function to extract destination IP address from the packet
    def getDstIp(packet):
      arp = packet.find('arp')
      if arp is not None:
        ipdst = str(arp.protodst)
        return ipdst
      ip = packet.find('ipv4')
      if ip is not None:
        ipdst = str(ip.dstip)
        return ipdst

    #Function to add IP to MAC mapping entry in ipToMac table
    def addIpMac(packet):
      macsrc = packet.src
      ipsrc = getSrcIp(packet)
      if ipsrc is not None:
        self.ipToMac[ipsrc] = macsrc

    #if self.macToPort.get(packet.src) is None:
    #Adding IP to MAC entry for the incoming the packet in ipToMac table
    addIpMac(packet)
    self.macToPort[packet.src] = event.port 
    
    if not self.transparent: 
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
        drop() 
        return
    #Checking if packet's destination MAC address is broadcast address
    if packet.dst.is_multicast:
	match = of.ofp_match.from_packet(packet)
	dstMac = self.ipToMac.get(getDstIp(packet))
	#If packet's dst MAC address is found in ipToMac table the instruct switch to send ARP response packet
	if dstMac is not None and match.dl_type == ethernet.ARP_TYPE and match.nw_proto == arp.REQUEST:
	  send_arp_response(packet,match,event,dstMac)
	else:
	  flood()
    else:
      #Checking for packet's dstMAC in macToPort table
      if packet.dst not in self.macToPort: 
	flood("Port for %s unknown -- flooding" % (packet.dst,)) 
      else:
        port = self.macToPort[packet.dst]
        if port == event.port: 
          log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
              % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
          drop(10)
          return
	send_packet(packet,event,port)

class l2_learning (object):
  """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """
  def __init__ (self, transparent):
    core.openflow.addListeners(self)
    self.transparent = transparent

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    LearningSwitch(event.connection, self.transparent)


def launch (transparent=False, hold_down=_flood_delay):
  """
  Starts an L2 learning switch.
  """
  try:
    global _flood_delay
    _flood_delay = int(str(hold_down), 10)
    assert _flood_delay >= 0
  except:
    raise RuntimeError("Expected hold-down to be a number")

  core.registerNew(l2_learning, str_to_bool(transparent))
