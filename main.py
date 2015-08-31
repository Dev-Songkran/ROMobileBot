### Project: DayDreamBot
### 
###
### Section: Main
import Connection, DDFunc, Processor
import sys, time, struct, re
import threading

def logging(msg, logfile):
	f = open(logfile, 'a+')
	f.write(time.asctime() + ': ' + str(msg) + '\r\n')
	f.close()

def pack(msg):
	return ''.join(DDFunc.toHex(DDFunc.toBytes(msg)))
def unpack(msg):
	return ''.join([chr(int(msg[i] + msg[i+1], 16) for i,x in enumerate(msg))])
def dec2hex(num):
	hexVer = '{0:x}'.format(num)
	hexVer = '0'*(4-len(hexVer)) + hexVer
	return hexVer[2:4:] + hexVer[0:2:]
def listServer(servInf):
	codeLength = ord(servInf[0])
	servInf = servInf[1::].split('000001'.decode('hex'))
	for i in range(0, len(servInf)-1):
		serverCode = servInf[i][:codeLength:] + '00'
		serverNameLength = ord(servInf[i][codeLength+2])
		serverName = servInf[i][codeLength+3:codeLength+3+serverNameLength:]
		print '\t[+] ', '(', serverCode, ') ', serverName
	loginKeyLength = ord(servInf[-1][1])
	loginKey = servInf[-1][3:3+loginKeyLength:]
	return loginKey

def listCharacter(charData):
	charData = charData[9::]
	charData = charData.split('ffff'.decode('hex'))
	charInf = {}
	for i,char in enumerate(charData):
		nameLength = ord(char[4])
		charNum = i
		charName = char[5:5+nameLength:]
		charLevel = ord(char[5+nameLength+1])
		charMap = char[5+nameLength+5:5+nameLength+9:]
		print '\t[', charNum, '] ', charName, '(Lv.', charLevel, ')''[', charMap, ']'
		charInf[str(charNum)] = {'num': charNum, 'name': charName, 'level': charLevel, 'map': charMap}
	return charInf
	
def loginLogin(conObject, username, password):
	usrLength = len(username)
	pwdLength = len(password)
	# Build a login packet
	# 40 characters username, 13 characters password
	loginMessage = '\x00' + username + '\x00'*(40-usrLength) + dec2hex(pwdLength).decode('hex') + password + 'MPS02.0.301.0.0' + '\x06' + 'iphone' + '\x00'*(13-pwdLength)
	conObject.send(loginMessage)
	print '[.] Select servers from the list'
	loginKey = listServer(conObject.read()[9::])
	#selectedServer = raw_input('Input server code: ')
	selectedServer = '2W2T100'
	# ---------- News from Server ----------
	conObject.read()
	conObject.send('\x3c\x01')
	conObject.read()
	# ---------- News from Server ----------
	conObject.send(selectedServer)
	_response = conObject.read()
	if not _response:
		return [False, False]
	timestamp = _response[3:7:]
	# Get map server information [ip:port]
	gameServer = [ _response[8:8+ord(_response[7]):], struct.unpack('<h', _response[8+ord(_response[7]):10+ord(_response[7]):])[0] ]
	mapKey = loginKey + '\x00'*(35 - (len(loginKey)-5))
	loginKey = '\x00\x00' + timestamp + loginKey + '\x00'*(35 - (len(loginKey)-5)) + 'PC00'
	return [gameServer, loginKey, mapKey]

def gameLogin(conObject, charInf, ch, mapKey):
	# Declare sending packets
	mapCode = charInf['map']
	mapPacket = '0a901000'.decode('hex') + mapCode
	mapPacket2 = '0a007000' + '0' + str(ch)
	mapPacket2 = mapPacket2.decode('hex') + mapCode
	charPacket = '0a1010' + '0' + str(charInf['num']) + '0' + str(ch) + '01'
	# Send packets
	conObject.send(mapPacket)
	conObject.send(charPacket.decode('hex'))
	conObject.read()
	conObject.read()
	conObject.send(mapPacket2)	
	_response = ''
	while True:
		_response = conObject.read()
		if _response[1:3:] == '\x10\x70':
			break	
	gameServer = [ _response[15:15+ord(_response[14]):], struct.unpack('<h', _response[15+ord(_response[14]):17+ord(_response[14]):])[0] ]
	# If a map server is changed
	if conObject.dest != gameServer[0]:
		conObject.send('02'.decode('hex'))
		conObject.close()
		conObject.dest = gameServer[0]
		conObject.port = gameServer[1]
		conObject.connect()
		conObject.getKey()
		conObject.send(conObject.mapKey)
		while True:
			_response = conObject.read()
			if _response[:3:] == '\x01\xe9\x03':
				break
		conObject.mapKey = conObject.mapKey[:2:] + _response[::-1][:4:][::-1] + conObject.mapKey[6::]
	conObject.multipleSend(['\x0a\x81\x10', '\x0a\x95\x10', '\x0a\x50\x30', '\x0a\x40\x62', '\x0a\x18\x10'])
	
if __name__ == '__main__':
	gameServer = False
	loginKey = False
	mapKey = False
	while not (gameServer and loginKey):
		RConnect = Connection.Connection('103.4.157.135', 8000)
		RConnect.connect()
		RConnect.getKey()
		gameServer, loginKey, mapKey = loginLogin(RConnect, 'username', 'password')
		if not (gameServer or loginKey or mapKey):
			print '[.] Login failed, try again'
	print '[.] Login successfully, connecting to game server'
	RConnect.close()
	RConnect.dest = gameServer[0]
	RConnect.port = gameServer[1]
	RConnect.connect()
	#RConnect = Connection.Connection(gameServer[0], gameServer[1])
	RConnect.getKey()
	RConnect.send(loginKey)
	mapKey = '\x00\x01' + RConnect.read()[::-1][:4:][::-1] + mapKey
	RConnect.mapKey = mapKey
	charInf = listCharacter(RConnect.read())
	#charNum = raw_input("Choose your character: ")
	charNum = '0'
	Processor.Character['map'] = charInf[charNum]['map']
	gameLogin(RConnect, charInf[charNum], 6, RConnect.mapKey)
	relay = Processor.RelayStation(RConnect)
	vision = Processor.VisualStation(RConnect)
	cortex = Processor.CortexStation(RConnect, relay)
	limbic = Processor.LimbicStation(RConnect, cortex)
	relay.daemon = True
	vision.daemon = True
	cortex.daemon = True
	limbic.daemon = True
	limbic.readConfiguration()
	relay.start()
	cortex.start()
	print '[.] Waking up...'
	while Processor.Character['maxhp'] == 0:
		continue
	vision.start()
	print '[.] Opening both eyes...'
	time.sleep( 3.0 )
	limbic.start()
	while True:
		command = raw_input('Input your command: ')
		if len(re.findall('warp', command)):
			mapcode = command.split(' ')[1]
			cortex.warp(6, mapcode, RConnect.mapKey)
		elif len(re.findall('attack', command)):
			cortex.attack()
			print '[.] Attacking'
		else:
			RConnect.send(command.decode('hex'))
			logging( command, 'command-log.txt' )
			logging( '---End of command---', 'command-log.txt' )
		
"""
Walk to position
0a 5010 00 00 00 00 00 00 00 00 [06] [23 05] [b6 08] 00
                            [direction] [x]    [y]


# connect to another map server
# 0f20000a 1070 e903 46313033 0132 05a000 0d3130332e342e3135372e3134320a200000

Pickup Item
0a 4030 db342a00
        [  id  ]

Talk to NPC
0a 0040 9002 0000
        [id]

Sell Item
0a 3040 01 01
      [slot][num]

Request Backpack List
0a 2040

Buy Item
0a 5040 0c 0400 01
0a 5040 0c 0400 05
       [t] [id] [n]

Use Item
0a a030 03
       [slot]

Register Item
0a 1033 09 dc05 0000 02 01
       [s] [ price ] [d] [n]
0a 0033 --- OK

Give all sold items
0a 6033 ffff ffffffff ffff
0a 4033

Disassemble Item
0a 8741 08
       [slot]
"""
