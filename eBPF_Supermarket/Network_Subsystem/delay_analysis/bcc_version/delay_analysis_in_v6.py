from __future__ import print_function

import os
import sys

sys.path.append(os.path.realpath("../visual"))

import argparse
from socket import inet_ntop, AF_INET6

from bcc import BPF



############## arguments #################
parser = argparse.ArgumentParser(description="Trace time delay in network subsystem",
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--sport", help="trace this source port only")
parser.add_argument("--dport", help="trace this destination port only")
parser.add_argument("-s", "--sample", help="Trace sampling")
parser.add_argument("-c", "--count", type=int, default=99999999, help="count of outputs")
parser.add_argument("--print", action="store_true", help="print results to terminal")
parser.add_argument("--visual", action="store_true", help="enable visualization with influxdb-grafana")
args = parser.parse_args()

bpf_text = open('delay_analysis_in_v6.c').read()

# -------- code substitutions --------
if args.sport:
    bpf_text = bpf_text.replace('##FILTER_SPORT##', 'if (pkt_tuple.sport != %s) { return 0; }' % args.sport)
    
if args.dport:
    bpf_text = bpf_text.replace('##FILTER_DPORT##', 'if (pkt_tuple.dport != %s) { return 0; }' % args.dport)
    
if args.sample:
    bpf_text = bpf_text.replace('##SAMPLING##', 'if (((pkt_tuple.seq + pkt_tuple.ack + skb->len) << (32-%s) >> (32-%s)) != ((0x01 << %s) - 1)) { return 0;}' % (args.sample, args.sample, args.sample))

if args.visual:
    from utils import export_delay_analysis_in_v6

bpf_text = bpf_text.replace('##FILTER_SPORT##', '')
bpf_text = bpf_text.replace('##FILTER_DPORT##', '')
bpf_text = bpf_text.replace('##SAMPLING##', '')


################## printer for results ###################
def print_event(cpu, data, size):
    event = b["timestamp_events"].event(data)
    if args.print:
        print("%-42s %-42s %-12s %-12s %-20s %-10s %-10s %-10s %-10s" % (
            "%s:%d" % (inet_ntop(AF_INET6, event.saddr), event.sport),
            "%s:%d" % (inet_ntop(AF_INET6, event.daddr), event.dport),
            "%d" % (event.seq),
            "%d" % (event.ack),
            "%f" % (event.mac_timestamp*1e-9),
            "%d" % (event.total_time/1000),
            "%d" % (event.mac_time/1000),
            "%d" % (event.ip_time/1000),
            "%d" % (event.tcp_time/1000)
        ))
    if args.visual:
        export_delay_analysis_in_v6(event)


################## start tracing ##################
b = BPF(text=bpf_text)

if args.print:
    # -------- print header --------
    print("%-42s %-42s %-12s %-12s %-20s %-10s %-10s %-10s %-10s" % \
        ("SADDR:SPORT", "DADDR:DPORT", "SEQ", "ACK", "TIME", "TOTAL", "MAC", "IP", "TCP"))

# -------- read events --------
b["timestamp_events"].open_perf_buffer(print_event)

count = 0

while 1:
    
    count += 1
    if count > args.count:
        break

    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()