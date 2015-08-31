### Project: DayDreamBot
### 
###
### Section: Connection Modules

import DDFunc
import socket, sys, time

class Connection(object):
	def __init__(self, destination, port):
		self.dest = destination
		self.port = port
		self.mapKey = False
		self.sending = False
		self.activePriority = False
	def connect(self):
		# Create a socket and connect with destination:port
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except socket.error:
			print '[.] Errors occured during creating socket'
			sys.exit()
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) #keep-alive
		self.socket.settimeout(10.0)
		print '[.] Connecting to ' + self.dest, ':', self.port		
		try:
			self.socket.connect( (self.dest, self.port) )
		except socket.timeout:
			print '[.] Connection timeout'
			sys.exit()
		except:
			print '[.] Unknown errors occured during connection'
			sys.exit()
		print '[.] You are now connected to ' + self.dest, ':', self.port
	def getKey(self):
		# Request key from server
		print '[.] Requesting encryption key from server'
		self.socket.sendall('0f08005100646273637068'.decode('hex'))
		print '[.] Sending packet...'
		keyPacket = DDFunc.toBytes(self.socket.recv(65535)[4::])
		# Split to key and 2 significant bytes
		self.sigbytes = int('0x' + ''.join(['{0:x}'.format(x) for x in keyPacket[16:18][::-1]]),0)
		self.key = keyPacket[0:16]	
		print '[.] Got an encryption key, [', ''.join(DDFunc.toHex(self.key)), self.sigbytes, ']'
	def multipleSend(self, msgs):
		while msgs:
			self.send(msgs.pop(0))
	def send(self, msg):
		self.sending = True
		while self.activePriority:
			continue
		msg = DDFunc.toBytes(msg)
		# Figure out what function needed to use
		backupKey = self.key[::]
		funcIndex ,self.sigbytes = DDFunc.functionSelection(self.key, self.sigbytes)
		#print '[>] [', self.sigbytes, funcIndex, ']', time.time()
		# Encrypt message
		encryptedMsg = DDFunc.messageEncryption(funcIndex, self.key, msg)
		self.key = backupKey[::]		
		encryptedMsg = ''.join(DDFunc.toHex(encryptedMsg))
		msgLength = len(encryptedMsg.decode('hex'))		
		# Log about data being sent
		# print '[.] Sending ', msgLength, ' bytes'
		# print '[.] Encrypted Data: ', encryptedMsg
		# Send data
		try:
			self.socket.sendall(encryptedMsg.decode('hex'))
		except:
			# Something went wrong, return False
			print '[.] Errors occured, message has not been sent'
			self.sending = False
			sys.exit()
			return False
		# Successfully sent the message, return True
		# print '[.] Message has been sent'
		self.sending = False
		return True
	def prioritySend(self, msg):
		self.activePriority = True
		_startTime = time.time()
		while self.sending:
			_diffTime = time.time() - _startTime
			if _diffTime > 5:
				# In case two threads start at the same time
				break
			continue
		msg = DDFunc.toBytes(msg)
		# Figure out what function needed to use
		backupKey = self.key[::]
		funcIndex ,self.sigbytes = DDFunc.functionSelection(self.key, self.sigbytes)
		# print '[>] [', self.sigbytes, funcIndex, ']'
		# Encrypt message
		encryptedMsg = DDFunc.messageEncryption(funcIndex, self.key, msg)
		self.key = backupKey[::]		
		encryptedMsg = ''.join(DDFunc.toHex(encryptedMsg))
		msgLength = len(encryptedMsg.decode('hex'))		
		# Log about data being sent
		# print '[.] Sending ', msgLength, ' bytes'
		# print '[.] Encrypted Data: ', encryptedMsg
		# Send data
		try:
			self.socket.sendall(encryptedMsg.decode('hex'))
		except:
			# Something went wrong, return False
			print '[.] Errors occured, message has not been sent'
			self.activePriority = False
			return False
		# Successfully sent the message, return True
		# print '[.] Message has been sent'
		self.activePriority = False
		return True		
	def read(self):
		# Get message length
		try:
			recvLength = self.socket.recv(3)
		except:
			# Got nothing, return false
			return False
		# Something was sent to us
		recvLength = DDFunc.toHex(DDFunc.toBytes(recvLength))
		try:
			recvLength = int( recvLength[2] + recvLength[1], 16 )
		except:
			recvLength = 0
		# Receive remaining data
		if recvLength == 0:
			# Still nothing?
			return False
		recvMsg = self.socket.recv(recvLength)
		return recvMsg
	def close(self):
		try:
			self.socket.close()
		except:
			return False
		return True
		
