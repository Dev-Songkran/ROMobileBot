### Project: DayDreamBot
### 
###
### Section: Functions Module

import random
import ctypes
# Essential functions
def toBytes( str ):
	return [ord(x) for x in str]
def toHex(str):
	return ['0' + x if len(x) == 1 else x for x in ['{0:x}'.format(x) for x in str]]
def signByte(byte): # Two's complement
	if ( (byte & 128) != 0 ):
		byte = byte - 256
	return byte
def unsignByte(byte): # My method, need improvement
	if( (byte < 0 ) ):
		byte = byte + 256
	return byte%256	

# Encryption functions
# Functions Selection 
# : Calculate whether functions to use for encryption based on Key sent from server
def functionSelection(key, lastBytes):
	keyIndex = lastBytes%16
	checkKey = key[keyIndex]
	x = ctypes.c_int16(( ( 0x38E38E39*lastBytes )>>32 )>>1).value
	x = ctypes.c_int16(x + (x<<3)).value
	y = ctypes.c_int16(( 0x55555556*checkKey )>>32).value
	x = ctypes.c_int16(lastBytes - x).value
	lastBytes = ctypes.c_int16(lastBytes + y + x).value
	if ( lastBytes<<16 ) >= 0x79180001:
		lastBytes = ctypes.c_int16(lastBytes + 0x86E8).value
	z = ctypes.c_int16(( 0x2AAAAAAB*lastBytes )>>32).value
	z = ctypes.c_int16(z + (z>>31)).value
	z = ctypes.c_int16(lastBytes - ( z + ( z*2 ) )*2).value
	return [z,lastBytes]
# An Encryption function
def messageEncryption(nfunc, key, msg):
	#Key Operation
	# : Add a constant value to each key byte 
	oldMsg = msg[::]
	oldKey = key[::]
	_4randomByte = 0
	if nfunc == 0: #sub_f6b4
		key[::2] = [x+55 for x in key[::2]] #even
		key[1::2] = [x+147 for x in key[1::2]] #odd
	elif nfunc == 1: #sub_f7a8
		key[::2] = [unsignByte(x+127) for x in key[::2]] #even
		key[1::2] = [unsignByte(x+179) for x in key[1::2]] #odd
	elif nfunc == 2: #sub_f8e4
		for i in range(0, len(key)):
			_r1 = ctypes.c_long((i*0x55555556)>>32).value
			_r1 = ctypes.c_long(_r1 + (_r1>>31)).value
			_r1 = ctypes.c_long(_r1 + (_r1<<1)).value
			_r1 = ctypes.c_long(i - _r1).value
			if _r1:
				if _r1 == 1:
					key[i] = unsignByte(key[i]*key[i])
				else:
					key[i] = 0
			else:
				key[i] = unsignByte(key[i]<<1)
	elif nfunc == 3: #sub_fa38
		key[::2] = [unsignByte(x+231) for x in key[::2]] #even
		key[1::2] = [unsignByte(x+12) for x in key[1::2]] #odd
	elif nfunc == 4: #sub_fb20
		_4randomByte = unsignByte(random.randint(1,1<<32))%16
		_4randomByte = unsignByte(_4randomByte)+1
		key[::2] = [unsignByte(x*x) for x in key[::2]] #even
		key[1::2] = [unsignByte((x*(_4randomByte))+x) for x in key[1::2]] #odd
	elif nfunc == 5: #sub_fc2c
		_r9 = 0x55555556
		for i in range(0, len(key)):
			_r1 = (i*_r9)>>32
			_r1 = _r1 + (_r1>>31)
			_r1 = _r1 + (_r1<<1)
			_r1 = i - _r1
			if _r1:
				if _r1 == 1:
					key[i] = key[i] + 0xF3
				else:
					key[i] = key[i] + 0x2A
			else:
				key[i] = key[i] + 0x1B
			key[i] = unsignByte(key[i])		
	# print 'operated key:', toHex(key)
	#Message Operation
	# : Add/Sub a key byte with message byte (a key index is modulated by its length)
	if nfunc == 0:
		msg[::2] = [unsignByte((signByte(x)-signByte(key[(2*i)%16]))) for i, x in enumerate(msg[::2])] #even
		msg[1::2] = [unsignByte((signByte(x)+signByte(key[(2*i+1)%16]))) for i, x in enumerate(msg[1::2])] #odd
	elif nfunc == 1:
		msg[::2] = [unsignByte((signByte(x)+signByte(key[(2*i)%16]))) for i, x in enumerate(msg[::2])] #even
		msg[1::2] = [unsignByte((signByte(x)-signByte(key[(2*i+1)%16]))) for i, x in enumerate(msg[1::2])] #odd
	elif nfunc == 2:
		_r11 = 0
		for i in range(0, len(msg)):
			_r4 = ctypes.c_long((i*0x55555556)>>32).value
			_r1 = ctypes.c_long(_r4 + (_r4>>31)).value
			_r1 = ctypes.c_long(_r1 + (_r1<<1)).value
			_r1 = ctypes.c_long(i - _r1).value
			if _r1 == 0:
				_r11 = msg[i]
				msg[i] = unsignByte(msg[i] + key[i%16])
			else:
				_r4 = ctypes.c_long((i*0x66666667)>>32).value
				_r1 = ctypes.c_long(_r4 >> 1).value
				_r1 = ctypes.c_long(_r1 + (_r4>>31)).value
				_r1 = ctypes.c_long(_r1 + (_r1<<2)).value
				_r1 = ctypes.c_long(i - _r1).value
				if _r1:
					msg[i] = unsignByte(msg[i] - _r11)
				else:
					_r11 = msg[i]
					msg[i] = unsignByte(msg[i] + key[i%16])
	elif nfunc == 3:
		msg = [unsignByte(x^key[i%16]) for i, x in enumerate(msg)]
	elif nfunc == 4:
		msg[::2] = [unsignByte(signByte(x)^signByte(key[(2*i)%16])) for i, x in enumerate(msg[::2])] #even
		msg[1::2] = [unsignByte(signByte(x)^signByte(key[(2*i+1)%16]+signByte(_4randomByte))) for i, x in enumerate(msg[1::2])] #odd
		_swapIndex = len(msg)>>1
		if _swapIndex:
			msg[_swapIndex:_swapIndex*2:], msg[:_swapIndex:] = 	msg[:_swapIndex:], msg[_swapIndex:_swapIndex*2:]
		msg.append(_4randomByte)
	elif nfunc == 5:
		msg = [unsignByte(x-key[i%16]) for i, x in enumerate(msg)]
	# print 'operated msg: ', toHex(msg)
	#Random byte Operation 
	# : Random a byte, add/sub to message byte, put random byte at the end of message
	randomByte = 0
	if nfunc == 0:
		randomByte = unsignByte(random.randint(1,1<<32))
		#randomByte = 5
		msg[::2] = [unsignByte((unsignByte(x)+randomByte)) for x in msg[::2]]
		msg[1::2] = [unsignByte((unsignByte(x)+(randomByte*-1))) for x in msg[1::2]]
	elif nfunc == 1:
		randomByte = unsignByte(random.randint(1,1<<32))
		#randomByte = 19
		randomIndex = len(msg)>>1
		msg.insert(randomIndex, randomByte)
		msg[::2] = [unsignByte(unsignByte(x)+randomByte) for x in msg[::2]] #even
		msg[1::2] = [unsignByte(unsignByte(x)-randomByte) for x in msg[1::2]] #odd	
		msg[randomIndex] = randomByte	
	elif nfunc == 2:
		randomByte = unsignByte(random.randint(1,1<<32))
		#randomByte = -84
		#randomByte = 0x1a #manipulated
		msg[::3] = [unsignByte(x-randomByte) for x in msg[::3]]
		randomByte = randomByte + 0xF9
	elif nfunc == 3:
		_r0 = len(msg) >> 1
		_r2 = len(msg) >> 2
		msg[_r0], msg[_r2] = msg[_r2], msg[_r0]
		randomByte = unsignByte(random.randint(1,1<<32))%16
		#randomByte = 2 #manipulated
		msg.append(randomByte)
		msg.append(oldKey[randomByte])
		randomByte = unsignByte(random.randint(1,1<<32))
		#randomByte = -51 #manipulated
		msg[1::2] = [unsignByte(x + (randomByte^116)) for x in msg[1::2]]
	elif nfunc == 4:
		randomByte = unsignByte(random.randint(1,1<<32))
		_r3 = ctypes.c_long(0xAB000000 ^ (randomByte<<24)).value
		_r6 = ctypes.c_long(_r3>>24).value
		msg[::3] = [unsignByte(x-_r6) for x in msg[::3]]
	elif nfunc == 5:
		randomByte = unsignByte(random.randint(1,1<<32))
		#randomByte = 0x6a
		msg[::2] = [unsignByte((unsignByte(x)+randomByte)) for x in msg[::2]]
		msg[1::2] = [unsignByte((unsignByte(x)+(randomByte*-1))) for x in msg[1::2]]
	# print 'random operated: ', toHex(msg)
	#Sum of every 3 bytes of message, called it checkSum, put it at the end
	checkSum = 0
	if nfunc == 0:
		checkSum = sum(msg[::3])
		msg.append(unsignByte(randomByte))	
	elif nfunc == 1:
		checkSum = sum(oldMsg[1::2]) + sum(msg[:len(oldMsg):2])
	elif nfunc == 2:
		checkSum = sum([unsignByte(0xFFFFFFF9-x) for x in oldMsg[1::2]])
	elif nfunc == 3:
		checkSum = randomByte
	elif nfunc == 4:
		checkSum = randomByte
	elif nfunc == 5:
		checkSum = sum(msg[::2])
		msg.append(unsignByte(randomByte))
	# print 'checksum: ', toHex([checkSum])
	msg.append(unsignByte(checkSum))
	if nfunc == 2:
		msg.append(unsignByte(randomByte))
	elif nfunc == 5:
		randomByte = 0x5189
		_r0 = 0xFF000000
		_r0 = ctypes.c_long(_r0 & (randomByte<<23)).value
		_r0 = ctypes.c_long(_r0 + 0xD6000000).value
		_r2 = ctypes.c_long(_r0 >> 0x18).value
		msg[::3] = [unsignByte(x-_r2) for x in msg[::3]]
		_r3 = _r2 + 0x27
		msg.append(unsignByte(_r3))
		msg[0], msg[-1] = msg[-1], msg[0]
		msg[1], msg[(len(oldMsg)+3)>>1] = msg[(len(oldMsg)+3)>>1], msg[1]
	msgLength = len(msg)
	msg.append(msgLength)
	msg.append(0)	
	# print 'all operated msg: ', toHex(msg)
	# Add a random length, byte tail to an encrypted message
	randomLengthSeed = random.randint(1,1<<32)
	tailLength = ( ( 0x66666667*randomLengthSeed )>>32 )>>2
	tailLength = tailLength + ( tailLength<<2 )
	tailLength = ( randomLengthSeed - ( tailLength<<1 ) )+8
	randomTail = []
	# Tail randomization
	if( tailLength != 1 ):
		for i in range(0, tailLength):
			_randomByte = random.randint(1,1<<32)
			m = ( ( 0x80808081*_randomByte )>>32 )>>7
			m = ( m<<8 ) - m
			_randomByte = _randomByte - m
			randomTail.append(unsignByte(_randomByte))
	#randomTail = [55, 223, 193, 173, 165, 209, 51, 209, 58, 190]
	# Add tail 
	msg = msg + randomTail
	# Swap bytes 
	msg[0],msg[msgLength+1] = msg[msgLength+1],msg[0]
	msg[msgLength],msg[2] = msg[2],msg[msgLength]
	# Finish encryption message (Get it ready for sending)
	finalLength = len(msg)
	# print 'finised msg: ', toHex(msg)	
	if finalLength > 255:
		finalLength = ['0' + x if len(x) == 3 else x for x in ['{0:x}'.format(x) for x in [finalLength]]]
		msg.insert(0,int(finalLength[0][0:2], 16))
		msg.insert(0,int(finalLength[0][2:4], 16))
	else:
		msg.insert(0,0)
		msg.insert(0,finalLength)
	msg.insert(0,15)
	return msg
	
if __name__ == '__main__':
	key = toBytes(raw_input('Input key: ').decode('hex'))
	funcIndex = int(raw_input('Select function: '))
	while True:
		command = raw_input('Input command: ').decode('hex')
		messageEncryption(funcIndex, key, toBytes(command))