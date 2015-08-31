### Project: DayDreamBot
### 
###
### Section: Processor 
"""
Monsters Packet
b048 0000 0000 0000 0000 0000 b400 0000 3804 a005 04 ffff ffff
[id]                          [hp]      [cx] [cy]     [target]
Items Packet
bc0f1d00 1000 0000 0000 0000  0c   0000 84032c06 f1d3 1b00 ffff 0000 00
[uid]                       [type] [id] [owner]  [cx] [cy]
"""
import DDFunc
import threading 
import time, Queue, struct, re, types

DEBUG = False

VisionMemory = Queue.Queue(maxsize=0)
CortexMemory = Queue.Queue(maxsize=0)
PlayerMemory = {}
MonsterMemory = {}
MonsterMemoryLatestUpdate = 0
ItemMemory = {}
MonsterList = {}
Inventory = {}

def loadData(src):
	f = open(src, 'r+')
	l = []
	while True:
		d = f.readline().split(';')
		if d[0] == 'END':
			break
		l.append(d)
	return l
# Define character attributes
Character = {'maxhp': 0, 'hp': 0, 'maxsp': 0, 'sp': 0, 'pos': (0,0), 'aspd': 0, 'uid': 0, 'map': 0, 'money': 0, 'emergency': False}

#
# Limbic Station is responsible for executing diffrent behaviors based on situations (from config.ini) of robot.
#
class LimbicStation( threading.Thread ):
	def __init__(self, conObject, cortexObject):
		threading.Thread.__init__(self, target=self.run)
		self.connection = conObject
		self.cortex = cortexObject
		# Define configuration variables
		self.targetMonster = []
		self.avoidMonster = []
		self.targetItem = []
		self.avoidItem = []
		self.hpLowerBorder = 0
		self.allowChannel = 6
	# main function of thread
	def run(self):
		global MonsterMemory, ItemMemory, Inventory, Character
		hpLow = False
		latestCharacterPos = Character['pos']
		startCharacterPos = Character['pos']
		noMonsterCount = 0
		noTargetCount = 0
		twoHandTime = time.time() - 270
		while True:
			if self.cortex.busyFlag:
				continue
			#
			# Check difference of time from beginning, time comes -> switch channel
			#
			#if (time.time() - self.cortex.timer) >= 20:
			if Character['emergency']:
				if self.allowChannel == 6:
					self.allowChannel = 7
				else:
					self.allowChannel = 6
				self.cortex.warp(self.allowChannel, Character['map'].lower(), self.connection.mapKey)
				Character['emergency'] = False
			#
			# If HP is lower than critical point, send robot back to the town
			#
			if hpLow:
				if Character['hp'] == Character['maxhp']:
					#self.cortex.warp(6, 'f107', self.connection.mapKey)
					self.cortex.walk([latestCharacterPos[0], latestCharacterPos[1]])
					hpLow = False
				print '[.] Resting... HP:', Character['hp'], '/', Character['maxhp']
				self.connection.send('\x0a\x60\x10')
				time.sleep(4.0)
				continue
			#
			# Casting Two-handed quicken
			#
			#
			if time.time() - twoHandTime > 270:
				print '[.] Casting Two-handed Quicken!'
				self.cortex.attack( {'uid': Character['uid'], 'pos': Character['pos']}, 0, [10, 10] )
				twoHandTime = time.time()
				time.sleep(3.0)				
			#
			# Looking for target monsters in Memory
			#
			# There's no monster within area
			if not len(MonsterMemory):
				print '[.] No monsters within area'
				self.connection.send('\x0a\x60\x10')
				noMonsterCount += 1
				time.sleep(4.0)
				if noMonsterCount == 10:
					self.cortex.walk([startCharacterPos[0], startCharacterPos[1]])
					noMonsterCount = 0
				continue
			# Filter monster list, 'id', 'distance' and match the list in configuration variable
			_monsterList = filter(lambda m: m['id'] in self.targetMonster, filter(lambda n: 'id' in n, MonsterMemory.values()))
			_monsterList = filter(lambda m: 'distance' in m, _monsterList)
			_monsterList = filter(lambda m: m['hp'][1] > 0, filter(lambda n: 'hp' in n, _monsterList))
			# There's no target monster within area
			if not len(_monsterList):
				print '[.] No target monsters within area'
				self.connection.send('\x0a\x60\x10')
				noTargetCount += 1
				time.sleep(4.0)
				if noTargetCount == 10:
					self.cortex.walk([startCharacterPos[0], startCharacterPos[1]])
					noTargetCount = 0
				continue
			# Sort target monsters, using distance as a compared variable, get the nearest
			_monsterList.sort(key=lambda k: k['distance'])
			_ruid = _monsterList[0]['uid']
			# Double check that monster actually exists in area (Maybe it disappears before we reach)
			if not str(_ruid) in MonsterMemory:
				print '[.] Monster (' + str(_ruid) + ') disappeared from sight'
				continue
			print '[.] Lock target: ' + MonsterMemory[str(_ruid)]['name'] + '(' + str(_ruid) +')'
			# Attack nearest monster till it's death
			self.cortex.walk( [MonsterMemory[str(_ruid)]['pos'][0], MonsterMemory[str(_ruid)]['pos'][1]] )
			time.sleep(0.2)
			state = 1
			print '[>] Current time:', time.time()
			while str(_ruid) in MonsterMemory and MonsterMemory[str(_ruid)]['hp'][1] > 0:
				print '[.] Attacking ' + MonsterMemory[str(_ruid)]['name'] + '(' + str(_ruid) +') with ASPD (' + str(Character['aspd']) +')'
				"""if Character['sp'] > 30:
					state = 0
					self.cortex.attack( MonsterMemory[str(_ruid)], state, [5, 10] )
					state = -1
				else:"""
				self.cortex.attack( MonsterMemory[str(_ruid)], state )
				# There's 3 states of attacking.
				state += 1
				if state == 4:
					state = 1
				time.sleep( (160-Character['aspd'])/50 ) #default = 170/50
				if str(_ruid) in MonsterMemory:
					print '[.] Its HP: ' + str(MonsterMemory[str(_ruid)]['hp'][1])
				else:
					print '[.] Target monster is DEATH!'
				if Character['hp'] <= self.hpLowerBorder:
					# Do something
					print '[.] HP is lower than critical point,', Character['hp']
					latestCharacterPos = Character['pos']
					self.cortex.walk( [0, 0] )				
					hpLow = True					
			# Looking for Target Items
			_itemList = filter(lambda m: [m['type'], m['id']] in self.targetItem, filter(lambda n: 'type' in n and 'id' in n, ItemMemory.values()))
			while len(_itemList):
				self.cortex.pick(_itemList.pop(0))
				time.sleep(0.3)
			self.cortex.viewInventory()
			time.sleep(0.2)
			for _item in Inventory.values():
				if isinstance(_item, dict):
					if _item['type'] == 24:
						print '[.] Registering item to auction machine'
						self.connection.send('\x0a\x10\x33' + chr(_item['slot']) + '\x10\x27\x00\x00\x02\x01')
						self.connection.send('\x0a\x00\x33')
						time.sleep(0.3)
						self.connection.send('\x0a\x60\x33\xff\xff\xff\xff\xff\xff\xff\xff')
						self.connection.send('\x0a\x40\x33')
						time.sleep(0.2)
						Inventory.pop(str(_item['slot']), None)
						continue
					if [_item['type'], _item['id']] in self.avoidItem:
						print '[.] Item (type: ' + str(_item['type']) + ', ' + str(_item['id']) + ') were kept'
						print '[.] Disassembling item'
						self.connection.send('\x0a\x87\x41' + chr(_item['slot']))
						continue
					if ([_item['type'], _item['id']] in self.targetItem):
						self.cortex.sellItem(_item)
						time.sleep(0.5)
			print '[.] Character Money:', Character['money']
			# Exploring self
			if Character['hp'] <= self.hpLowerBorder:
				# Do something
				print '[.] HP is lower than critical point,', Character['hp']
				latestCharacterPos = Character['pos']
				self.cortex.walk( [0, 0] )				
				hpLow = True
			time.sleep(0.3)
	# Read user configs from config.ini, assign them in declared variables
	def readConfiguration(self):
		config = open('config.ini', 'r+')
		config.readline() # Skip the first line
		config.readline() # Server
		config.readline() # Channel
		config.readline() # Character
		# Target Monsters
		_targetMonster = config.readline().split(';')
		if len(_targetMonster) > 1:
			self.targetMonster = [int(m) for m in _targetMonster[1::]]
		# Avoid Monsters
		_avoidMonster = config.readline().split(';')
		if len(_avoidMonster) > 1:
			self.avoidMonster = [int(m) for m in _avoidMonster[1::]]
		# Target Items
		_targetItem = config.readline().split(';')
		if len(_targetItem) > 1:
			self.targetItem = [[int(n) for n in m.split('.')] for m in _targetItem[1::]]
		# Avoid Items
		_avoidItem = config.readline().split(';')
		if len(_avoidItem) > 1:
			self.avoidItem = [[int(n) for n in m.split('.')] for m in _avoidItem[1::]]
		# HP Lower Border
		self.hpLowerBorder = int(config.readline().split(';')[1])
		
#
# Cortex Station is responsible for processing self awareness and also basic survival functions of robot
#
class CortexStation( threading.Thread ):
	def __init__(self, conObject, relayObject):
		threading.Thread.__init__(self, target=self.run)
		self.connection = conObject
		self.relaystation = relayObject
		self.busyFlag = False
		self.timer = time.time()
		
	def run(self):
		global CortexMemory
		while True:
			if CortexMemory.empty():
				continue
			data = CortexMemory.get()
			# Sort out signals
			backupData = data[::]
			# 4010 = Character Packet
			# print '[>] ' + ''.join(DDFunc.toHex(DDFunc.toBytes(backupData)))
			if data[:2:] == '\x40\x10':
				Character['aspd'] = struct.unpack('<h', data[12:14:])[0]
				if data[2:4:] == '\x00\x00':
					data = data[33::]
				else:
					# UID of character
					if data[2:4:] == '\x00\x20':
						Character['uid'] = struct.unpack('<i', data[18:22:])[0]
						Character['money'] = struct.unpack('<i', data[14:18:])[0]
					# Playing safe with regex
					_next = re.search(r'' + data[2:10:], data[10::], flags=re.DOTALL)
					if isinstance(_next, types.NoneType):
						continue
					_next = _next.start() + 10
					data = data[_next+15::]
				# Assign latest attributes of character
				Character['maxhp'] = struct.unpack('<h', data[1:3:])[0]
				Character['maxsp'] = struct.unpack('<h', data[3:5:])[0]
				Character['hp'] = struct.unpack('<h', data[5:7:])[0]
				Character['sp'] = struct.unpack('<h', data[7:9:])[0]
				Character['pos'] = (struct.unpack('<h', data[9:11:])[0], struct.unpack('<h', data[11:13:])[0])
				# It seems like this robot is death?
				if Character['hp'] <= 0:
					print 'Error packet: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(backupData)))
				"""print 'HP:', Character['maxhp'], '/', Character['hp']
				print 'SP:', Character['maxsp'], '/', Character['sp']
				print 'POS:', Character['pos']"""
				
	def warp(self, ch, mapCode, mapKey):
		global PlayerMemory, MonsterMemory, ItemMemory, CortexMemory, VisionMemory
		# Stop reading packet from relay station
		self.relaystation.stop()
		self.busyFlag = True
		print '[.] Pause RelayStation'
		time.sleep(3.0)
		print 'Monster: ', MonsterMemory
		print 'Vision', VisionMemory
		# Wipe out all memories
		PlayerMemory = {}
		MonsterMemory = {}
		ItemMemory = {}
		CortexMemory.queue.clear()
		VisionMemory.queue.clear()
		print '[.] Waiting other threads to shutdown'		
		print 'Monster: ', MonsterMemory
		print 'Vision', VisionMemory
		time.sleep(3.0)
		# Declare sending packets
		print '[.] Request travelling to', mapCode
		# Switch channel, or change map?
		if Character['map'].lower() != mapCode.lower():
			mapPacket = '0a901001'.decode('hex') + mapCode
			mapPacket2 = '0a007001' + '0' + str(ch)
		else:
			mapPacket = '0a901003'.decode('hex') + mapCode
			mapPacket2 = '0a007003' + '0' + str(ch)
		mapPacket2 = mapPacket2.decode('hex') + mapCode
		# Send packets
		self.connection.send(mapPacket)
		self.connection.send(mapPacket2)
		# If a map server is changed, try make connection with new one
		print '[.] Getting map server'
		while True:
			_response = self.connection.read()
			if _response == False:
				gameServer = [ self.connection.dest, self.connection.port ]
				break
			if _response[1:3:] == '\x10\x70':
				gameServer = [ _response[15:15+ord(_response[14]):], struct.unpack('<h', _response[15+ord(_response[14]):17+ord(_response[14]):])[0] ]
				break
		self.connection.send('\x02')
		while True:
			_response = self.connection.read()
			if not _response:
				break
		self.connection.close()
		self.connection.dest = gameServer[0]
		self.connection.port = gameServer[1]
		self.connection.connect()
		self.connection.getKey()
		self.connection.send(mapKey)
		while True:
			_response = self.connection.read()
			print DDFunc.toHex(DDFunc.toBytes(_response))
			if _response[:3:] == '\x01\xe9\x03':
				break
		self.connection.mapKey = self.connection.mapKey[:2:] + _response[::-1][:4:][::-1] + self.connection.mapKey[6::]
		self.connection.multipleSend(['\x0a\x81\x10', '\x0a\x95\x10', '\x0a\x50\x30', '\x0a\x40\x62', '\x0a\x18\x10'])
		print '[.] Waking up...'
		self.relaystation.restart()
		self.timer = time.time()
		print '[.] Opening both eyes...'
		time.sleep(3.0)
		self.busyFlag = False

	def walk(self, dest):
		print '[.] Walking to:', dest[0], dest[1]
		x = struct.pack('<h', dest[0])
		y = struct.pack('<h', dest[1])
		d = '\x06'
		walkPacket = '\x0a\x50\x10\x00\x00\x00\x00\x00\x00\x00\x00' + d + x + y + '\x00'
		self.connection.send(walkPacket)
		
	def attack(self, targetMonster, state, skill=False):
		_uid = targetMonster['uid']
		_x = targetMonster['pos'][0]
		_y = targetMonster['pos'][1]
		self.connection.send('\x0a\x00\x20' + struct.pack('<i', _uid)) # changed from '\x00\x00'
		if skill:
			skill_id = struct.pack('<h', skill[0])
			skill_level = chr(skill[1])
			print '[.] Using skill (' + str(skill[0]) + ', ' + str(skill[1]) + ')'
			self.connection.send('\x0a\x80\x30' + skill_id + skill_level)
			state = 0
		else:
			self.connection.send('\x0a\x50\x10\x02\x00\x00\x00\x00\x00\x00\x00\x06' + struct.pack('<h', _x) + struct.pack('<h', _y) + chr(state))
		self.connection.send('\x0a\x50\x10\x00\x00\x00\x00\x00\x00\x00\x00\x06' + struct.pack('<h', _x) + struct.pack('<h', _y) + chr(state))
		
	def pick(self, targetItem):
		print '[.] Picked item (type: ' + str(targetItem['type']) + ', id: ' + str(targetItem['id']) + ')'
		_uid = targetItem['uid']
		self.connection.send('\x0a\x40\x30' + struct.pack('<i', _uid))
	
	def viewInventory(self):
		global Inventory
		if not 'latestUpdated' in Inventory:
			Inventory['latestUpdated'] = time.time()
		self.connection.send('\x0a\x20\x40')
		print '[.] Requesting Inventory from Server'
		time.sleep(1.5)
		
	def sellItem(self, item):
		global Inventory
		_slot = chr(int(item['slot']))
		_num = chr(int(item['num']))
		self.connection.send('\x0a\x30\x40' + _slot + _num)
		print '[.] Item (type: ' + str(item['type']) + ', ' + str(item['id']) + ') were sold'
		Inventory.pop(str(item['slot']), None)
#
# Visual Station is responsible for processing surrounding objects, sort them out and put them in specified memories
#
class VisualStation( threading.Thread ):
	def __init__(self, conObject):
		threading.Thread.__init__(self, target=self.run)
		self.connection = conObject
		
		# Build monsters list
		monsterList = loadData('monster.dat')
		for monster in monsterList:
			id = monster[0]
			name = monster[4]
			level = int(monster[6])
			MonsterList[id] = {'name': name, 'id': id, 'level': level}
		
	def run(self):
		global VisionMemory, PlayerMemory, ItemMemory, MonsterMemory, Inventory, MonsterMemoryLatestUpdate
		while True:
			if VisionMemory.empty():
				continue
			data = VisionMemory.get()
			# Sort out signal
			# --- 4110 --- Players (START)
			if data[:2:] == '\x41\x10':
				_num = ord(data[2])
				data = data[3::]
				backupData = data[::]
				__num = _num
				#_num = 0
				while _num:
					#print '*'*10
					#print 'Backup: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(backupData)))
					backupData = data[::]
					#print '-'*10
					#print 'Raw: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data)))
					if len(data) == 0:
					#	print '[>] Not complete analysis'
						break
					#handling error
					if len(data) <= 4:
						#print '[>] Stuck at Loop 1'
						data = backupData[1::]
						continue
					id = str(struct.unpack('<i', data[1:5:])[0])
					notmet = 1 if not id in PlayerMemory else 0
					#print 'notmet', notmet
					if not notmet: # double check
						if len(re.findall(PlayerMemory[id]['name'], data)):
							notmet = 1
					if notmet:
						# handling error
						if len(data) <= 18:
							#print '[>] Stuck at Loop 2'
							data = backupData[1::]
							continue
						level = ord(data[13])
						job = data[14:16:]
						_namelen = ord(data[16])
						# handling error
						if _namelen <= 0:
							data = backupData[1::]
							continue
						name = data[17:17+_namelen:]
						try:
							tmp = name.decode('utf-8')
						except:
							data = backupData[1::]
							continue
						data = data[17+_namelen::]
						# handling error
						if len(data) == 0:
							#print '[>] Stuck at Loop 3'
							data = backupData[1::]
							continue
						cursor = 0
						# wearing hat?
						if data[0] == '\xff':
							cursor += 1
						else:
							cursor += 3
						# holding weapon?
						# handling error
						if cursor >= len(data):
							#print '[>] Stuck at Loop 4'
							data = backupData[1::]
							continue
						if data[cursor] == '\xff':
							cursor += 1
						else:
							cursor += 4
						# have a guild?
						if cursor >= len(data):
							#print '[>] Stuck at Loop 5'
							data = backupData[1::]
							continue						
						if data[cursor] == '\x00':
							cursor += 8
						else:
							cursor += 2 + ord(data[cursor]) + 8
						data = data[cursor::]
					else:
						if data[13] == '\xff':
							data = data[20::]
						else:
							if data[14] == '\x00':
								data = data[24::]
							else:
								data = data[25::]
					# handling error
					if len(data) <= 12:
						#print '[>] Stuck at Loop 6'
						data = backupData[1::]
						continue					
					# get player current status
					direction = data[0]
					hp = (struct.unpack('<h', data[1:3:])[0], struct.unpack('<h', data[5:7:])[0])
					sp = (struct.unpack('<h', data[3:5:])[0], struct.unpack('<h', data[7:9:])[0])
					pos = (struct.unpack('<h', data[9:11:])[0], struct.unpack('<h', data[11:13:])[0])
					distance = ((pos[0] - Character['pos'][0])**2 + (pos[1] - Character['pos'][1])**2)**0.5
					#print 'Distance:', distance
					if distance >= 50000:
						#print '[>] Stuck at Distance'
						data = backupData[1::]
						continue
					if (hp[0] <= 0) or (sp[0] <= 0) or (hp[1] > hp[0]) or (sp[1] > sp[0]):
						#print '[>] Stuck at Loop 7'
						data = backupData[1::]
						continue
					if (pos[0] < 0) or (pos[1] < 0):
						#print '[>] Stuck at Loop 8'
						data = backupData[1::]
						continue
					if (notmet == 1) and (level <= 0 or level > 75) :
						#print '[>] Stuck at Loop 9'
						data = backupData[1::]
						continue
					data = data[13::]
					data = data[4::]
					if notmet:
						PlayerMemory[id] = {}
						PlayerMemory[id]['name'] = name
						PlayerMemory[id]['level'] = level
						PlayerMemory[id]['job'] = job
						PlayerMemory[id]['direction'] = direction
						PlayerMemory[id]['hp'] = hp
						PlayerMemory[id]['sp'] = sp
						PlayerMemory[id]['pos'] = pos
						"""try:
							print '[.] Just meet "' + PlayerMemory[id]['name'] + '"'						
						except:
							print '[.] Cannot print'"""
					else:
						PlayerMemory[id]['direction'] = direction
						PlayerMemory[id]['hp'] = hp
						PlayerMemory[id]['sp'] = sp
						PlayerMemory[id]['pos'] = pos
					"""	print '[.] Updating "' + PlayerMemory[id]['name'] + '"'						
					# shout it out loud
					print '   [.] Level: ' + str(PlayerMemory[id]['level'])
					print '   [.] HP:', hp
					print '   [.] SP:', sp
					print '   [.] Pos:', pos"""
					_num -= 1
				# Log each processed packet	
				if DEBUG:
					f = open('logs/player-memory.txt', 'a+')
					for object in PlayerMemory.iteritems():
						f.write(object[0])
						f.write('\n')					
						f.write('[.] ' + object[1]['name'] + ' Lv.' + str(object[1]['level']))
						f.write('\n')
					f.write('*'*20)
					f.close()
			# --- 4110 --- Players (END)
			# --- 4010 --- Monsters (START)
			elif data[:2:] == '\x40\x10':
				_num = ord(data[2])
				data = data[3::]
				backupData = data[::]
				if len(data) < 25*_num:
					continue
				#_num = 0
				_start = time.time()
				if DEBUG:
					_f = open('logs/monster-log.txt', 'a+')
					_f.write('\n' + '-'*10 + '\n')
					_f.write('monsterLarge: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data))) + '\n' + '*'*10 + '\n')
					_f.close()
				fullData = backupData[::]
				while _num:	
					if time.time() - _start > 30:
						print '[.] Program is trapped'
						continue
					backupData = data[::]
					if len(data) < 4:
						data = ''
						_f = open('Character-Emergency.txt', 'a+')
						_f.write( ''.join(DDFunc.toHex(DDFunc.toBytes(fullData))) + '\n' )
						_f.close()
						Character['emergency'] = True
						break
					uid = struct.unpack('<i', data[:4:])[0]
					if uid <= 0:
						data = backupData[1::]
						continue						
					notmet = 1 if not str(uid) in MonsterMemory else 0					
					if notmet:
						dataLength = len(data)						
						if dataLength < 33:
							data = backupData[1::]
							continue							
						id = struct.unpack('<h', data[12:14:])[0]
						level = ord(data[18])
						if data[16:18:] != '\x00\x00':
							level = -1
						hp = (struct.unpack('<h', data[14:16:])[0], struct.unpack('<h', data[20:22:])[0])
						pos = (struct.unpack('<h', data[24:26:])[0], struct.unpack('<h', data[26:28:])[0])
						target = 0 if data[29:33:] == '\xff\xff\xff\xff' or data[31:33:] == '\x00\x00' else struct.unpack('<i', data[29:33:])[0] 
						distance = ((pos[0] - Character['pos'][0])**2 + (pos[1] - Character['pos'][1])**2)**0.5
						if str(id) in MonsterList:
							if MonsterList[str(id)]['level'] != level:
								data = backupData[1::]
								continue
						else:
							data = backupData[1::]
							continue
						if hp[0] < hp[1]:
							data = backupData[1::]
							continue
						if DEBUG:
							_f = open('logs/monster-log.txt', 'a+')
							_f.write('notmet:' + str(notmet) + '\n')
							_f.write('num:' + str(_num) + '\n')
							_f.write('monster: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data))) + '\n' + '*'*10 + '\n')
							_f.close()	
						data = data[33::]				
						if _num > 1:
							_next = re.search(r'.{2}\x00\x00.{2}\x00\x00', data, flags=re.DOTALL)
							if isinstance(_next, types.NoneType):
								data = backupData[1::]
								continue
							else:
								_next = _next.start()
								data = data[_next::]						
						MonsterMemory[str(uid)] = {}
						MonsterMemory[str(uid)]['uid'] = uid
						MonsterMemory[str(uid)]['id'] = id
						MonsterMemory[str(uid)]['level'] = level
						MonsterMemory[str(uid)]['hp'] = hp
						MonsterMemory[str(uid)]['pos'] = pos
						MonsterMemory[str(uid)]['target'] = target
						MonsterMemory[str(uid)]['name'] = MonsterList[str(id)]['name']
						MonsterMemory[str(uid)]['distance'] = distance
					else:
						hp = (MonsterMemory[str(uid)]['hp'][0], struct.unpack('<h', data[12:14:])[0])
						pos = (struct.unpack('<h', data[16:18:])[0], struct.unpack('<h', data[18:20:])[0])
						target = 0 if data[21:25:] == '\xff\xff\xff\xff' or data[23:25:] == '\x00\x00' else struct.unpack('<i', data[21:25:])[0] 						
						distance = ((pos[0] - Character['pos'][0])**2 + (pos[1] - Character['pos'][1])**2)**0.5
						if DEBUG:
							_f = open('logs/monster-log.txt', 'a+')
							_f.write('notmet:' + str(notmet) + '\n')
							_f.write('num:' + str(_num) + '\n')
							_f.write('monster: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data))) + '\n' + '*'*10 + '\n')
							_f.close()
						if hp[0] < hp[1]:
							data = backupData[1::]
							continue
						data = data[25::]
						if _num > 1:
							_next = re.search(r'.{2}\x00\x00.{2}\x00\x00', data, flags=re.DOTALL)
							if isinstance(_next, types.NoneType):
								data = backupData[1::]
								continue
							else:
								_next = _next.start()
								data = data[_next::]
						MonsterMemory[str(uid)]['hp'] = hp
						MonsterMemory[str(uid)]['pos'] = pos
						MonsterMemory[str(uid)]['target'] = target
						MonsterMemory[str(uid)]['distance'] = distance
					"""print str(uid)
					print MonsterMemory[str(uid)]['hp']
					print MonsterMemory[str(uid)]['pos']
					print MonsterMemory[str(uid)]['distance']"""
					_num -= 1
				MonsterMemoryLatestUpdate = time.time()
				_next = re.search(r'.{5}\x10\x00\x00\x00\x00\x00', data, flags=re.DOTALL)
				_next = 12 if isinstance(_next, types.NoneType) else _next.start()
				if _next >= 12:
					_next = re.search(r'.{5}\x00\x00\x00\x00\x00\x00', data, flags=re.DOTALL)
					if isinstance(_next, types.NoneType):
						continue
					else:
						_next = _next.start()
				data = data[_next::]
				"""if len(data) < 14:
					continue
				data = data[:len(data)-3:] + '\x12\x13\x14\x15\x16\x17\x00\x00\x00\x00\x00\x00\x0a'
				_next = re.search(r'.{5}[\x00]{6}[^\x00]', data, flags=re.DOTALL)
				if isinstance(_next, types.NoneType):
					continue
				else:
					_next = _next.start()
				if str(struct.unpack('<i', data[_next-2::][:4:])[0]) in ItemMemory:
					data = data[_next-3::]
				else:
					data = data[_next-2::]"""
				if DEBUG:
					_f = open('logs/item-log.txt', 'a+')
					_f.write('item: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data))) + '\n')
					_f.close()
				_inum = ord(data[0])
				if _inum:
					data = data[1::]
				while _inum:
					dataLength = len(data)
					uid = struct.unpack('<i', data[0:4:])[0]
					# notmet = 1 if not str(uid) in ItemMemory else 0
					notmet = 1 if data[4] == '\x10' else 0
					if notmet:
						type = ord(data[12])
						id = struct.unpack('<h', data[13:15:])[0]
						pos = (struct.unpack('<h', data[15:17:])[0], struct.unpack('<h', data[17:19:])[0])
						owner = struct.unpack('<i', data[19:23:])[0]
						if _num > 1:
							data = data[25::]
						ItemMemory[str(uid)] = {}
						ItemMemory[str(uid)]['type'] = type
						ItemMemory[str(uid)]['id'] = id
						ItemMemory[str(uid)]['pos'] = pos
						ItemMemory[str(uid)]['owner'] = owner
						ItemMemory[str(uid)]['uid'] = uid
					else:
						if _num > 1:
							data = data[12::]
					_inum -= 1
			# --- 4010 --- Monsters (END)
			# --- 4210 --- Monsters out of sight (START)
			elif data[:2:] == '\x42\x10':
				_num = ord(data[2])
				data = data[3::]
				while _num:
					uid = struct.unpack('<i', data[1:5:])[0]
					if str(uid) in MonsterMemory:
						MonsterMemory.pop(str(uid), None)
					elif str(uid) in ItemMemory:
						ItemMemory.pop(str(uid), None)
					data = data[4::]
					_num -= 1
			# --- 4210 --- Monsters out of sight (END)	
			# --- 2540 --- Inventory (START)
			elif data[:2:] == '\x25\x40':
				_num = ord(data[6])
				data = data[7::]
				print _num
				if DEBUG:
					_f = open('logs/inventory-log.txt', 'a+')
					_f.write('inventory: ' + ''.join(DDFunc.toHex(DDFunc.toBytes(data))) + '\n')
					_f.close()
				while _num:
					#print ''.join(DDFunc.toHex(DDFunc.toBytes(data)))
					#print '-'*10
					if len(data) == 0:
						break
					slot = ord(data[0])
					type = ord(data[1])
					id = struct.unpack('<h', data[2:4:])[0]
					num = ord(data[7])
					if not type in [12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24]:
						num = 1
					Inventory[str(slot)] = {}
					Inventory[str(slot)]['slot'] = slot
					Inventory[str(slot)]['type'] = type
					Inventory[str(slot)]['id'] = id
					Inventory[str(slot)]['num'] = num
					if data[8] == '\x00' or data[8] == '\x01':
						data = data[9::]
					else:
						data = data[10::]
					_num -= 1
				Inventory['latestUpdated'] = time.time()
				
			# --- 2540 --- Inventory (END)
#
# Relay Station is acting like sensory system in human body, it's responsible for receiving all sensations from environment.
# Sort them out and send to next proper stations 
#
class RelayStation( threading.Thread ):
	def __init__(self, conObject):
		threading.Thread.__init__(self, target=self.run)
		self.connection = conObject
		self.stopFlag = False
	def stop(self):
		self.stopFlag = True
	def restart(self):
		self.stopFlag = False		
	def run(self):
		lastResponse = ''
		overflow = False
		while True:
			if self.stopFlag:
				continue
			if not overflow:
				response = self.connection.read()
			else:
				response = lastResponse
				overflow = False
			if not response:
				continue
			signal = response[1:3:]
			if signal == '4110'.decode('hex'):
				# re-read to get the rest packet.
				while True:
					_response = self.connection.read()
					if not _response:
						continue
					if _response[0] == '\x0a':
						lastResponse = _response
						overflow = True
						break
					else:
						response += _response
			responseLength = len(response)
			# Transmission signal
			if signal == '4110'.decode('hex'):
				VisionMemory.put(response[1::])
			elif signal == '4010'.decode('hex'):
				_next = 0
				if response[3] == '\x00' and response[4] == '\x00':
					_next = re.search(r'.{2}\x00\x00.{2}\x00\x00', response[50::], flags=re.DOTALL)
					if isinstance(_next, types.NoneType):
						if response[51::][:5:] == '\x00\x00\x00\x00\x00':
							_next = 52
						else:
							if DEBUG:
								_f = open('logs/relay-log.txt', 'a+')
								_f.write('-'*20)
								_f.write('- Error -\n' + ''.join(DDFunc.toHex(DDFunc.toBytes(response))) + '\n')
								_f.close()
					else:
						_next = _next.start() + 50
				else:
					__next = re.search(r'' + response[3:5:], response[11::], flags=re.DOTALL)
					if isinstance(__next, types.NoneType):
						__next = -32
						_f = open('logs/relay-log.txt', 'a+')
						_f.write('-'*20)
						_f.write('- Error -\n' + ''.join(DDFunc.toHex(DDFunc.toBytes(response))) + '\n')
						_f.close()							
					else:
						__next = __next.start() + 11
					_next = re.search(r'.{2}\x00\x00.{2}\x00\x00', response[__next + 32::], flags=re.DOTALL)
					if isinstance(_next, types.NoneType):
						if response[__next + 32::][:5:] == '\x00\x00\x00\x00\x00':
							_next = __next + 33
						else:
							if DEBUG:
								_f = open('logs/relay-log.txt', 'a+')
								_f.write('-'*20)
								_f.write('- Error -\n' + ''.join(DDFunc.toHex(DDFunc.toBytes(response))) + '\n')
								_f.close()	
					else:
						_next = _next.start() + __next + 32
				if not isinstance(_next, types.NoneType):
					CortexMemory.put(response[1:_next-1:])
					VisionMemory.put('\x40\x10' + response[_next-1::])
					if DEBUG:
						_f = open('logs/relay-log.txt', 'a+')
						_f.write('-'*20)
						_f.write('- Cortex -\n' + ''.join(DDFunc.toHex(DDFunc.toBytes(response[1:_next-1:]))) + '\n')
						_f.write('- Vision -\n' + ''.join(DDFunc.toHex(DDFunc.toBytes(response[_next-1::]))) + '\n')
						_f.close()
			elif signal == '4210'.decode('hex'):
				VisionMemory.put(response[1::])
			elif signal == '2540'.decode('hex'):
				VisionMemory.put(response[1::])
			# Log
			if DEBUG:
				self.logging('Length: ' + str(responseLength))
				self.logging('Message: ' + response)
				response = ''.join(DDFunc.toHex(DDFunc.toBytes(response)))
				self.logging(response, 1)
			
	def logging(self, msg, hex=0, display=0):
		f = open('logs/packet-log.txt', 'a+')
		if hex:
			f.write( time.asctime() + '>] Hex:\r\n' )
			for i, j in enumerate(msg):
				if i%4 == 0 and i > 0:
					f.write(' ')
				if i%32 == 0 and i > 0:
					f.write('\n')					
				f.write(j)
			f.write('\n')
		else:
			f.write( time.asctime() + '>] ' + str(msg) + '\n' )
		if display:
			print msg
		f.close()

if __name__ == '__main__':
	print 'Debugging...'