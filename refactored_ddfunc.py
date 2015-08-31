import random
from ctypes import *
"""
	Assemble from ARM ASM
	I have no idea how it works so...

	suit yourself ><"
"""
def select_func(packet_key, func_key):
	X = c_int16(((0x38E38E39*func_key)>>32)>>1).value
	X = c_int16(X + X<<3).value
	Y = c_int16((0x55555556*packet_key[func_key%16])>>32).value
	X = c_int16(func_key - X).value
	new_func_key = c_int16(func_key + X + Y).value
	new_func_key = c_int16(new_func_key + 0x86E8).value if new_func_key<<16 >= 0x79180001 else new_func_key
	func_index = c_int16((0x2AAAAAAB*new_func_key)>>32).value
	func_index = c_int16(func_index + (func_index>>31)).value
	func_index = c_int16(new_func_key - ((func_index + func_index*2)*2)).value
	return func_index, new_func_key
def RO_encryption(_key, packet, func_index):
	key = _key[::] # Fucking python object concept!
	message = packet[::]
	key_length = len(key)
	random_byte = (c_ubyte.(random.randint(1, 1<<32)).value%16)+1
	for key_index in range(0, key_length):
		no_idea = (0x55555556*key_index)>>32
		no_idea = no_idea + (no_idea>>31)
		no_idea = no_idea + (no_idea<<1)
		no_idea = key_index - no_idea
		if func_index in [2, 5]:
			if func_index == 2:
				key[key_index] = c_ubyte(key[key_index]**2).value if no_idea == 1 else 0 if no_idea else c_ubyte(key[key_index]<<1).value
			elif func_index == 5:
				key[key_index] = c_ubyte(key[key_index] + 0xF3).value if no_idea == c_ubyte(key[key_index] + 0x2A) else 0 if no_idea else c_ubyte(key[key_index] + 0x1B).value
		else:
			if func_index == 0:
				key[key_index] = key[key_index]+147 if key_index%2 else key[key_index]+55
			elif func_index == 1:
				key[key_index] = key[key_index]+179 if key_index%2 else key[key_index]+127
			elif func_index == 3:
				key[key_index] = key[key_index]+12 if key_index%2 else key[key_index]+231
			elif func_index == 4:
				key[key_index] = (key[key_index]*random_byte) + key[key_index] if key_index%2 else key[key_index]**2
			key[key_index] = c_ubyte(key[key_index]).value
	message_length = len(message)
	for i, m in enumerate(message):
		key_index = (2*i) if i%2 else (2*i+1)
		key_index = key_index%16		
		if func_index == 0:
			message[i] = c_byte(m).value + c_byte(key[key_index]).value if i%2 else c_byte(m).value - c_byte(key[key_index]).value
		elif func_index == 1:
			message[i] = c_byte(m).value - c_byte(key[key_index]).value if i%2 else c_byte(m).value + c_byte(key[key_index]).value
		elif func_index == 2:
			no_idea = (0x55555556*i)>>32
			no_idea = no_idea + (no_idea>>31)
			no_idea = no_idea + (no_idea<<1)
			no_idea = i - no_idea
			if not no_idea:
				message[i] = m + key[i%16]
			else:
				no_idea = (0x66666667*i)>>32
				no_idea = no_idea>>1
				no_idea = no_idea + (no_idea>>31)
				no_idea = no_idea + (no_idea<<1)
				no_idea = i - no_idea
				if not no_idea:
					message[i] = m + key[i%16]
		elif func_index == 3:
			message[i] = m^key[i%16]
		elif func_index == 4:
			message[i] = c_byte(m).value^c_byte(key[key_index]).value
			message[i] = message[i] + c_byte(random_byte) if i%2 else message[i]
		elif func_index == 5:
			message[i] = m-key[i%16]
		message[i] = c_ubyte(message[i]).value
	if func_index == 4:
		swap_index = message_length>>1
		if swap_index:
			message[swap_index:swap_index*2:], message[:swap_index:] = message[:swap_index:], message[swap_index:swap_index*2:]		
		message.append(random_byte)
	random_msg = c_ubyte(random.randint(1,1<<32)).value%16
	check_sum = 0
	if func_index == 0:
		message[::2] = [c_ubyte(c_ubyte(m) + random_msg).value for m in message[::2]]
		message[1::2] = [c_ubyte(c_ubyte(m) + random_msg*-1).value for m in message[1::2]]
		check_sum = sum(message[::3])
		message.append(random_msg)
	elif func_index == 1:
		insert_index = len(message)>>1
		message.insert(insert_index, random_msg)
		message[::2] = [c_ubyte(c_ubyte(m) + random_msg).value for m in message[::2]]
		message[1::2] = [c_ubyte(c_ubyte(m) - random_msg).value for m in message[1::2]]
		message[insert_index] = random_msg
		check_sum = sum(packet[1::2]) + sum(message[:len(packet):2])
	elif func_index == 2:
		message[::3] = [c_ubyte(m - random_msg).value for m in message[::3]]
		random_msg += 0xF9
		check_sum = sum([c_ubyte(0xFFFFFFF9 - m).value for m in packet[1::2]])
	elif func_index == 3:
		m1, m2 = len(message)>>1, len(message)>>2
		message[m1], message[m2] = message[m2], message[m1]
		message.append(random_msg)
		message.append(_key[random_msg])
		message[1::2] = [c_ubyte(m + random_msg^116).value for m in message[1::2]]
		check_sum = random_msg
	elif func_index == 4:
		add_byte = c_long(c_long(0xAB000000^(random_msg<<24)).value>>24).value
		message[::3] = [c_ubyte(m - add_byte).value for m in message[::3]]
		check_sum = random_msg
	elif func_index == 5:
		message[::2] = [c_ubyte(c_ubyte(m) + random_msg).value for m in message[::2]]
		message[1::2] = [c_ubyte(c_ubyte(m) + random_msg*-1).value for m in message[1::2]]
		check_sum = sum(message[::2])
		message.append(random_msg)
	message.append(c_ubyte(check_sum).value)
	if func_index == 2:
		message.append(random_msg)
	elif func_index == 5:
		no_idea = 0x5189
		no_idea = 0xFF000000 & (no_idea<<23)
		no_idea = (no_idea + 0xD6000000)>>0x18
		message[::3] = [c_ubyte(m - no_idea).value for m in message[::3]]
		message.append(c_ubyte(no_idea + 0x27).value)
		message[0], message[-1] = message[0], message[-1]
		message[1], message[(len(packet)+3)>>1] = message[(len(packet)+3)>>1], message[1]

	message_length = len(message)
	message.append(message_length)
	message.append(0)
	"""
	rtail = random.randint(1,1<<32)
	tail_length =  ((0x66666667*rtail)>>32)>>2
	tail_length = tail_length + (tail_length<<2)
	tail_length = (rtail - (tail_length<<1)) + 8
	"""
	random_tail = [c_ubyte(random.randint(1,1<<32)).value for x in range(10)]
	message = message + random_tail
	message[0], message[message_length+1] = message[message_length+1], message[0]
	message[message_length], message[2] = message[2], message[message_length]
	message_length = len(message)
	if message_length > 255:
		message_length = ['0' + x if len(x) == 3 else x for x in ['{0:x}'.format(x) for x in [message_length]]]
		message.insert(0, int(message_length[0][0:2], 16))
		message.insert(0, int(message_length[0][2:4], 16))
	else:
		message.insert(0,0)
		message.insert(0, message_length)
	message.insert(0, 15)
	return message