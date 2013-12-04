import telnetlib
import sys
import getpass
import time
import os
import rrdtool

try:
    rrdpath = sys.argv[1]
    syncimg = sys.argv[2]
    marginimg = sys.argv[3]
except IndexError:
    print >> sys.stderr, "Usage: %s <rrdpath> <syncimg> <marginimg>"
    sys.exit(2)

password = getpass.getpass("Password: ")

tn = telnetlib.Telnet('192.168.1.254')
print tn.read_until('Username : ')
tn.write('Administrator\r\n')
print tn.read_until('Password : ')
tn.write(password + '\r\n')

print tn.read_until('{Administrator}=>')

if not os.path.exists(rrdpath):
    step = 10
    heartbeat = step * 2
    data_sources = [
        'DS:synctx:GAUGE:%s:U:U' % heartbeat,
        'DS:syncrx:GAUGE:%s:U:U' % heartbeat,
        'DS:margintx:GAUGE:%s:U:U' % heartbeat,
        'DS:marginrx:GAUGE:%s:U:U' % heartbeat,
    ]
    rrdtool.create(
        rrdpath,
        '--start', str(int(time.time())),
        '--step', str(step),
        data_sources,
        'RRA:AVERAGE:0.5:6:1000',
        'RRA:AVERAGE:0.5:60:1000')

while True:
    tn.write('xdsl info expand=enabled\r\n')
    data = tn.read_until('{Administrator}=>')
    
    synctx = -1
    syncrx = -1
    margintx = -1
    marginrx = -1

    for line in data.split('\n'):
        line = line.strip()
        if line.startswith('Payload rate [Kbps]:'):
            syncrx, synctx = map(float, line.split()[-2:])
        if line.startswith('Margins [dB]:'):
            marginrx, margintx = map(float, line.split()[-2:])
 
    data = "N:%f:%f:%f:%f" % (synctx, syncrx, margintx, marginrx)
    print "update: %s" % (data,)
    rrdtool.update(rrdpath, data)

    # make pretty graphs
    rrdtool.graph(marginimg,
        '-M', '-l', '0', '--start', '-8h',
        '--width', '800', '--height', '200',
        'DEF:marginrx=%s:marginrx:AVERAGE' % (rrdpath,),
        'LINE1:marginrx#800000:Margin RX',
        'DEF:margintx=%s:margintx:AVERAGE' % (rrdpath,),
        'LINE1:margintx#000080:Margin TX',
        'GPRINT:marginrx:LAST:Current Margin RX\: %1.3lf',
        'GPRINT:margintx:LAST:Current Margin TX\: %1.3lf')
    rrdtool.graph(syncimg,
        '-M', '-l', '0', '--start', '-8h',
        '--width', '800', '--height', '200',
        'DEF:syncrx=%s:syncrx:AVERAGE' % (rrdpath,),
        'LINE1:syncrx#800000:Sync RX',
        'DEF:synctx=%s:synctx:AVERAGE' % (rrdpath,),
        'LINE1:synctx#000080:Sync TX',
        'GPRINT:syncrx:LAST:Current Sync RX\: %1.3lf',
        'GPRINT:synctx:LAST:Current Sync TX\: %1.3lf')


    time.sleep(10)


