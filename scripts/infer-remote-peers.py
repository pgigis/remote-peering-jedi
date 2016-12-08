import sys, ujson, gzip
import numpy as np
from Helper import Helper
from Atlas import Atlas


traces_file = sys.argv[1]     # The corpus of the Atlas traceroutes, each Atlas measurement should be a line
ixp_interfaces = sys.argv[2]  # The IXP IP to AS member mapping
target_ixp = sys.argv[3]      # The target IXP for which we extract the paths
pyasn_file = sys.argv[4]      # The pyasn db file to map IP address to ASes: https://github.com/hadiasghari/pyasn
geodata_file = sys.argv[5]    # The mapping of city names to coordinates (latitude, longitude)
ATLAS_API_KEY = sys.argv[6]

helper = Helper(pyasn_file)

ixp_ip_asn = dict()
with open(ixp_interfaces, "r") as fin:
    for line in fin:
        if line.startswith("#"): continue
        lf = line.strip().split("|")
        if len(lf) > 2:
            interfaces = lf[2].split(",")
            for interface in interfaces:
                ixp_ip_asn[interface] = lf[1]

remote_if_neighbors = dict()
remote_if_rtts = dict()
remote_if_asn = dict()

ixp_data = {
    "LINX": {"names": ["LINX Juniper LAN", "LINX Extreme LAN"], "location": {"city": "London", "country": "GB"} },
    "DE-CIX Frankfurt": {"names": ["DE-CIX Frankfurt"], "location": {"city": "Frankfurt", "country": "DE"} },
    "AMS-IX": {"names": ["AMS-IX"], "location": {"city": "Amsterdam", "country": "NL"} },
    "MSK-IX": {"names": ["MSK-IX"], "location": {"city": "Moscow", "country": "RU"} }
}

unresolved_ixp_interfaces = set()
with gzip.open(traces_file) as fin:
    for line in fin:
        try:
            decoded_result = ujson.loads(line.strip())
            if "ixp" in decoded_result:
                if decoded_result["ixp"]["ixp_name"] in ixp_data[target_ixp]["names"]:
                    hop_index = decoded_result["ixp"]["hop_index"]
                    remote_interface = decoded_result["ixp"]["near_end_ip"][0]
                    remote_if_asn[remote_interface] = decoded_result["ixp"]["near_end_member"]
                    if remote_interface not in remote_if_neighbors:
                        remote_if_neighbors[remote_interface] = set()
                        remote_if_rtts[remote_interface] = list()
                    #print line
                    for hop in decoded_result["result"]:
                        if hop["hop"] == hop_index:
                            for reply in hop["result"]:
                                if "from" in reply and 'rtt' in reply:
                                    ixp_hop =reply["from"]
                                    if ixp_hop == decoded_result["ixp"]["ixp_ip"]:
                                        if ixp_hop in ixp_ip_asn:
                                            far_end_asn = ixp_ip_asn[ixp_hop]
                                            remote_if_neighbors[remote_interface].add(far_end_asn)
                                            remote_if_rtts[remote_interface].append(decoded_result["ixp"]["median_rtt_diff"])
                                        else:
                                            unknown_interfaces = ["195.208.208.53","195.208.209.216","195.208.210.13"]
                                            if reply["from"] not in unknown_interfaces :
                                                unresolved_ixp_interfaces.add(reply["from"])
                                                #print decoded_result["ixp"]["near_end_ip"][0], reply["from"], "?"
                                            #print line
                                            continue
                                            #sys.exit(-1)
                                        break
        except ValueError:
            continue

for iface in unresolved_ixp_interfaces:
    print "Unresolved IXP interface: " + iface

atlas = Atlas(ATLAS_API_KEY, geodata_file)
af = 4 # the IP version
description = "Remote Peering Jedi"
packets_num = 3
probes_count = 10
probes_city = ixp_data[target_ixp]["location"]["city"]
probes_country = ixp_data[target_ixp]["location"]["country"]

queried_interfaces = []

try:
    with open("remote-inteface-rtts-%s.txt" % target_ixp) as fin:
        for line in fin:
            lf = line.strip().split("\t")
            if len(lf) > 0:
                queried_interfaces.append(lf[0])
except IOError:
    pass # we haven't yet collected any RTTs

fout = open("remote-inteface-rtts-%s.txt" % target_ixp, "a+", 0)
skipped_counter = 0

print len(remote_if_neighbors)
print len(queried_interfaces)

for remote_interface in remote_if_neighbors:
    trace_median_rtt = np.median(np.array(remote_if_rtts[remote_interface]))
    if remote_interface in queried_interfaces:
        #skipped_counter += 1
        continue
    probes_asn = remote_if_neighbors[remote_interface]
    probes_asn.add(remote_if_asn[remote_interface])
    # If the median RTT is greater than 10 and we have at least 30 different paths
    if trace_median_rtt > 10 and len(remote_if_rtts[remote_interface]) > 30:
        rtts = atlas.ping_measurement(af, remote_interface, description, packets_num, probes_count, probes_city, probes_country, probes_asn)
        if len(rtts) > 0:
            data = np.array(rtts)
            ping_median_rtt = np.median(data)
            outline =  "%s\t%s\t%s\t%s\t%s" % (remote_interface, trace_median_rtt, ping_median_rtt, min(rtts), len(rtts))
            fout.write("%s\n" % outline)
            print outline
        else:
            outline = "%s\t%s\t%s\t%s\t%s" % (remote_interface, trace_median_rtt, "x", "x", "x")
            fout.write("%s\n" % outline)
            print "No RTTs for %s" % remote_interface
        #if counter > 150: break
    else:
        skipped_counter += 1

print skipped_counter

fout.flush()
fout.close()