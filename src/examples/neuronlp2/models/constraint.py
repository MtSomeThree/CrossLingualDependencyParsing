import math

class Constraint():
	def __init__(self, id1, id2, ratio, weightFactor=0):
		self.leftPos = id1
		self.rightPos = id2
                self.leftPosStr = 'UNK'
                self.rightPosStr = 'UNK'
		self.ratio = ratio
		self.direction = 1
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
		return self.PRFunction(indicator) * self.weightFactor
	def PRFunction(self, indicator):
		if indicator * self.direction == 1:
			return self.PRPos()
		if indicator * self.direction == -1:
			return self.PRNeg()
		return 0
	def PRPos(self):
		return 1.0 - self.ratio
	def PRNeg(self):
		return -self.ratio
        def output_to_file(self, logFile, data = 0.0):
		logFile.write('ID1: %s, ID2: %s, Ratio: %f, data: %f, WeightFactor: %f\n'%(self.leftPosStr, self.rightPosStr, self.ratio, data, self.weightFactor))
	def output(self, data = 0.0):
		print ('ID1: %d, ID2: %d, Ratio: %f, data: %f, WeightFactor: %f, direction: %d'%(self.leftPos, self.rightPos, self.ratio, data, self.weightFactor, self.direction))
