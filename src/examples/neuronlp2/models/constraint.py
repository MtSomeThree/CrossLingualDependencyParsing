import math

class Constraint():
	def __init__(self, id1, id2, ratio, weightFactor=0, margin=0.01):
		self.leftPos = id1
		self.rightPos = id2
                self.leftPosStr = 'UNK'
                self.rightPosStr = 'UNK'
		self.ratio = ratio
		self.direction = 1
		self.margin = margin
		self.weightFactor = weightFactor

	def load(self, pos_str1, pos_str2, ratioFile, alphabet):
		self.leftPosStr = pos_str1
		self.rightPosStr = pos_str2
		self.leftPos = alphabet.get_index(pos_str1)
		self.rightPos = alphabet.get_index(pos_str2)
		cFile = open(ratioFile, 'r')
		for line in cFile:
			pos1, pos2, r = line.strip().split('\t')
			if pos1 == pos_str1 and pos2 == pos_str2:
				self.ratio = float(r)
				self.weightFactor = 0
				print ("Load Constraint (%s, %s, %.4f) from %s"%(pos1, pos2, self.ratio, ratioFile))
				return	

	def load_WALS(self, feature_id, feature, alphabet, method='PR'):
		if ' ' not in feature:
			feature = 3
		else:
			feature = int(feature.split()[0])
		if feature_id == '85A':
			self.leftPos = alphabet.get_index('NOUN')
			self.rightPos = alphabet.get_index('ADP')
			self.leftPosStr = 'NOUN'
			self.rightPosStr = 'ADP'
		if feature_id == '87A':
			self.leftPos = alphabet.get_index('ADJ')
			self.rightPos = alphabet.get_index('NOUN')
			self.leftPosStr = 'ADJ'
			self.rightPosStr = 'NOUN'
		if feature_id == '89A':
			self.leftPos = alphabet.get_index('NUM')
			self.rightPos = alphabet.get_index('NOUN')
			self.leftPosStr = 'NUM'
			self.rightPosStr = 'NOUN'

		if feature == 1:
			if method == 'PR':
				self.ratio = 0.75
				self.direction = -1
			else:
				self.ratio = 0.875
				self.margin = 0.125
		elif feature == 2:
			if method == 'PR':
				self.ratio = 0.25
				self.direction = 1
			else:
				self.ratio = 0.125
				self.margin = 0.125
		elif feature == 3:
			if method == 'PR':
				extra_const = Constraint(0, 0, 0)
				extra_const.leftPos = self.leftPos
				extra_const.rightPos = self.rightPos
				extra_const.leftPosStr = self.leftPosStr
				extra_const.rightPosStr = self.rightPosStr
				self.ratio = 0.75
				self.direction = 1
				extra_const.ratio = 0.25
				extra_const.direction = -1
				print ("Load Constraint (%s, %s, %.4f) from WALS %s)"%(extra_const.leftPosStr, extra_const.rightPosStr, extra_const.ratio, feature_id))
				return extra_const		
			else:
				self.ratio = 0.5
				self.margin = 0.25

		
		print ("Load Constraint (%s, %s, %.4f) from WALS %s)"%(self.leftPosStr, self.rightPosStr, self.ratio, feature_id))
		return None

	def load_WALS_unary(self, features, alphabet, margin=0.05, method='PR'):
		self.leftPos = alphabet.get_index('NOUN')
		self.rightPos = self.leftPos
		self.leftPosStr = 'NOUN'
		self.rightPosStr = 'NOUN'
		X = []
		for feature_id in ['82A','83A','84A','85A','86A','87A','88A','89A']:
			if feature_id not in features:
				X.append(0.5)
				continue
			feature = features[feature_id]
			if len(feature) <= 1:
				X.append(0.5)
			else:
				flag = int(feature.split()[0])
				if flag == 1:
					X.append(0.75)
				elif flag == 2:
					X.append(0.25)
				else:
					X.append(0.5)
		ratio = -0.13 * X[0] + 0.76 * X[1] - 0.14 * X[2] + 0.34 * X[3] + 0.27 * X[4] + 0.05 * X[5] + 0.05 * X[6] + 0.2 * X[7] -0.19
		print ("Load Unary Constraint (NOUN, %.4f) from WALS"%(ratio))
		if method == 'PR':
			self.ratio = ratio + margin
			self.direction = 1
			extra_const = Constraint(self.leftPos, self.rightPos, ratio - margin)
			extra_const.leftPosStr = self.leftPosStr
			extra_const.rightPosStr = self.rightPosStr
			extra_const.direction = -1
			return extra_const
		else:
			self.ratio = ratio
			self.margin = margin
			return None

	def count(self, par, pos, length):
		total = 0
		sat_con = 0
		for i in range(1, length):
			res = self.pair_count(pos.data[i], pos.data[par[i]], i, par[i])
			if res != 0:
				total += 1
			if res == 1:
				sat_con += 1
			'''
			if pos.data[i] == self.leftPos and pos.data[par[i]] == self.rightPos:
				total += 1
				if i < par[i]:
					sat_con += 1
			if pos.data[i] == self.rightPos and pos.data[par[i]] == self.leftPos:
				total += 1
				if i > par[i]:
					sat_con += 1
			'''
		return total, sat_con
        def pair_count(self, pos1, pos2, id1=0, id2=0):
		if self.leftPos == self.rightPos:
			if pos1 == self.leftPos:
				if id1 < id2:
					return 1
				else:
					return -1
			return 0
                if pos1 == self.leftPos and pos2 == self.rightPos:
			if id1 < id2:
				return 1
			else:
				return -1
		if pos1 == self.rightPos and pos2 == self.leftPos:
			if id1 < id2:
				return -1
			else:
				return 1
		return 0
	def LagrangeOffset(self, indicator):
		if indicator == 1:
			return self.LagrangePos()
		if indicator == -1:
			return self.LagrangeNeg()
		return 0
	def LagrangePos(self):
		return self.weightFactor * (1.0 - self.ratio)
	def LagrangeNeg(self):
		return -self.weightFactor * self.ratio
	def PROffset(self, indicator):
		return -self.PRFunction(indicator) * self.weightFactor
	def PRFunction(self, indicator):
		if indicator == 1:
			return self.direction * self.PRPos()
		if indicator == -1:
			return self.direction * self.PRNeg()
		return 0
	def PRPos(self):
		return 1.0 - self.ratio
	def PRNeg(self):
		return -self.ratio
        def output_to_file(self, logFile, data = 0.0):
		logFile.write('ID1: %s, ID2: %s, Ratio: %f, data: %f, WeightFactor: %f\n'%(self.leftPosStr, self.rightPosStr, self.ratio, data, self.weightFactor))
	def output(self, data = 0.0):
		print ('ID1: %d, ID2: %d, Ratio: %f, data: %f, WeightFactor: %f, direction: %d'%(self.leftPos, self.rightPos, self.ratio, data, self.weightFactor, self.direction))
