import os, sys
import inspect
import string
from fontTools import ttLib
import itertools


__doc__ ='''\

	This script is capable of extracting a viable features.kern file from a compiled font.
	To be expanded with multiple options; e.g. AFM-export; and export of all possible (exploded) pairs.

	usage: python getKerning font.otf > outputfile

	'''

kKernFeatureTag = 'kern'

def askForClass(glyph, classes):
	for singleClass in classes:
		if glyph in singleClass:
			return singleClass
			break


class myLeftClass:
	def __init__(self):
		self.glyphs = []
		self.class1Record = 0

class myRightClass:
	def __init__(self):
		self.glyphs = []
		self.class2Record = 0

class collectClasses:
	def __init__(self):
		self.glyphs = []
		self.occurrence = 0

def sortGlyphs(glyphlist):
	# This function is sorting the glyphs in a way that glyphs from the exception list or glyphs starting with 'uni' names don't get 
	# to be key (first) glyphs. Also, an infinite loop is avoided, in case there are only glyphs matching above mentioned properties.
	exceptionList = 'dotlessi dotlessj kgreenlandic ae oe AE OE uhorn'.split()

	glyphs = sorted(glyphlist)
	for i in range(len(glyphs)):
		if glyphs[0] in exceptionList or glyphs[0].startswith('uni') or '_' in glyphs[0]:
			glyphs.insert(len(glyphs), glyphs.pop(0))
		else:
			continue

	return glyphs

def nameClass(glyphlist, flag):
	glyphs = sortGlyphs(glyphlist)	
	if len(glyphs) == 0:
		name = 'error!!!'
	else:
		name = glyphs[0]

	if name in string.ascii_lowercase:
		case = '_LC'
	elif name in string.ascii_uppercase:
		case = '_UC'
	else:
		case = ''

	flag = flag
	
	return '@%s%s%s' % (name, flag, case)


def collectUniqueKernLookupListIndexes(featureRecord):
	uniqueKernLookupListIndexesList = []
	for featRecItem in featureRecord:
# 		print featRecItem.FeatureTag  # GPOS feature tags (e.g. kern, mark, mkmk, size) of each ScriptRecord
		if featRecItem.FeatureTag == kKernFeatureTag:
			feature = featRecItem.Feature
			
			for featLkpItem in feature.LookupListIndex:
				if featLkpItem not in uniqueKernLookupListIndexesList:
					uniqueKernLookupListIndexesList.append(featLkpItem)
	
	return uniqueKernLookupListIndexesList


def main(fontPath):
	font = ttLib.TTFont(fontPath)
	
	gposTable = font['GPOS'].table
	
	glyphPairsList = []
	singlePairsList = []
	classPairsList	= []
	# leftClasses = {}
	# rightClasses = {}
	allClasses = {}

### ScriptList ###
# 	scriptList = gposTable.ScriptList

### FeatureList ###
	featureList = gposTable.FeatureList
	# featureCount = featureList.FeatureCount # integer
	featureRecord = featureList.FeatureRecord
	
	uniqueKernLookupListIndexesList = collectUniqueKernLookupListIndexes(featureRecord)
	
	# Make sure a 'kern' feature was found
	if not len(uniqueKernLookupListIndexesList):
		print "The font has no 'kern' feature"
		return

### LookupList ###
	lookupList = gposTable.LookupList
	for kernLookupIndex in sorted(uniqueKernLookupListIndexesList):
		lookup = lookupList.Lookup[kernLookupIndex]
		# Confirm this is a GPOS LookupType 2; or using an extension table (GPOS LookupType 9):
		if lookup.LookupType not in [2, 9]:
			print "This is not a pair adjustment positioning lookup (GPOS LookupType 2); and not using an extension table (GPOS LookupType 9).\nInstead, it is GPOS LookupType %s!" % lookup.LookupType
			continue
		
		# Step through each subtable
		for subtableItem in lookup.SubTable:
			if subtableItem.LookupType == 2: # normal case, not using extension table
				pairPos = subtableItem
			elif subtableItem.LookupType == 9: # If extension table is used
				if subtableItem.ExtensionLookupType == 8:
					continue
					# ExtensionPos == subtable!
					
					# those work!
					# print subtableItem.ExtSubTable
					# print subtableItem.ExtSubTable.convertersByName[1]['Coverage'].name
					# print dir(subtableItem.ExtSubTable.getConverterByName)
					# print subtableItem.ExtSubTable.getConverterByName
					# membersList = inspect.getmembers(subtableItem.ExtSubTable.getConverterByName)
					# for x in membersList:
					# 	print x
					# print
				elif subtableItem.ExtensionLookupType == 2:
					pairPos = subtableItem.ExtSubTable
					

			# if pairPos.Format not in [1]:
			# 	print "WARNING: PairPos format %d is not yet supported" % pairPos.Format
			
			if pairPos.Coverage.Format not in [1,2]:
				print "WARNING: Coverage format %d is not yet supported" % pairPos.Coverage.Format
			
			if pairPos.ValueFormat1 not in [4]:
				print "WARNING: ValueFormat1 format %d is not yet supported" % pairPos.ValueFormat1
			
			if pairPos.ValueFormat2 not in [0]:
				print "WARNING: ValueFormat2 format %d is not yet supported" % pairPos.ValueFormat2
			
			# each glyph in this list will have a corresponding PairSet which will
			# contain all the second glyphs and the kerning value in the form of PairValueRecord(s)
			firstGlyphsList = pairPos.Coverage.glyphs

			if pairPos.Format == 1: # glyph pair adjustment; format 2 is class pair adjustment
			
				# This iteration is done by index so that we have a way to reference the firstGlyphsList list
				for pairSetIndex in range(len(pairPos.PairSet)):
					for pairValueRecordItem in pairPos.PairSet[pairSetIndex].PairValueRecord:
						firstGlyph = firstGlyphsList[pairSetIndex]
						secondGlyph = pairValueRecordItem.SecondGlyph
						kernValue = pairValueRecordItem.Value1.XAdvance
						
						# singlePairsList.append(('%s %s' %( kernLookupIndex, firstGlyph), secondGlyph, kernValue))
						singlePairsList.append((firstGlyph, secondGlyph, kernValue))


			############################################
			############################################
			############################################

			elif pairPos.Format == 2: # class adjustment
				firstGlyphs = {}
				secondGlyphs = {}

				leftClasses = {}
				rightClasses = {}
				
				# Find left class with the Class1Record index="0".
				# This class is weirdly mixed into the "Coverage" (e.g. all left glyphs) 
				# and has no class="X" property, that is why we have to find them that way. 
				lg0 = myLeftClass()
				for leftGlyph in firstGlyphsList:
					if not leftGlyph in pairPos.ClassDef1.classDefs:
						lg0.glyphs.append(leftGlyph)
				# This mixing into the Coverage is true for makeOTF-built fonts. 
				# There are fonts which have all the glyphs properly assgned; therefore this if-statement:
				if not len(lg0.glyphs) == 0:
					leftClasses[lg0.class1Record] = lg0		

				# Find all the remaining left classes:
 				for leftGlyph in pairPos.ClassDef1.classDefs:
 					class1Record = pairPos.ClassDef1.classDefs[leftGlyph]
 					if class1Record in leftClasses:
	 					leftClasses[class1Record].glyphs.append(leftGlyph)
	 				else:
	 					lg = myLeftClass()
	 					lg.class1Record = class1Record
	 					leftClasses[class1Record] = lg
	 					leftClasses[class1Record].glyphs.append(leftGlyph)

				# Same for the right classes:
				for rightGlyph in pairPos.ClassDef2.classDefs:					
 					class2Record = pairPos.ClassDef2.classDefs[rightGlyph]
 					if class2Record in rightClasses:
	 					rightClasses[class2Record].glyphs.append(rightGlyph)
	 				else:
	 					rg = myRightClass()
	 					rg.class2Record = class2Record
	 					rightClasses[class2Record] = rg
	 					rightClasses[class2Record].glyphs.append(rightGlyph)
 				
				for record_l in leftClasses:
					for record_r in rightClasses:
						if pairPos.Class1Record[record_l].Class2Record[record_r]:
							kernValue = pairPos.Class1Record[record_l].Class2Record[record_r].Value1.XAdvance
							if kernValue != 0:

								leftGlyphs = sortGlyphs(leftClasses[record_l].glyphs)

								rightGlyphs = sortGlyphs(rightClasses[record_r].glyphs)

								leftClass = nameClass(leftGlyphs, '_LEFT')
								rightClass = nameClass(rightGlyphs, '_RIGHT')
								
								if (leftClass, rightClass, kernValue) in classPairsList:
									pass
								else:
									# classPairsList.append(('%s %s' % (kernLookupIndex, leftClass), rightClass, kernValue))
									classPairsList.append((leftClass, rightClass, kernValue))
							
						else:
							print 'ERROR'
			
				for i in leftClasses:
			 		glyphs = sortGlyphs(leftClasses[i].glyphs)
					className = nameClass(glyphs, '_LEFT')
					if not className in allClasses:
						allClasses[className] = glyphs
				
				for i in rightClasses:
					glyphs = sortGlyphs(rightClasses[i].glyphs)
					className = nameClass(glyphs, '_RIGHT')
					if not className in allClasses:
						allClasses[className] = glyphs
				

	
	leftGlyphsDict = {}
	rightGlyphsDict = {}
	allLeftClasses = []
	allRightClasses = []
	potentialLeftClasses = []
	potentialRightClasses = []
	leftKeyGlyphs = []
	rightKeyGlyphs = []
	finalLeftClasses = []
	finalRightClasses = []
	
	" Creating dictionaries filled with dictionaries, for all the and right and left glyphs. "
 	for left, right, value in singlePairsList:
		if not left in leftGlyphsDict:
			leftGlyphsDict[left] = {}
		if not right in rightGlyphsDict:
			rightGlyphsDict[right] = {}

	" Filling dicts created above; creating a list of glyphs that are accidentally kerned to the left glyph by _value_. "
	for left, right, value in singlePairsList:
		if not value in leftGlyphsDict[left]:
			leftGlyphsDict[left][value] = [right]
		if not value in rightGlyphsDict[right]:
			rightGlyphsDict[right][value] = [left]
		else:
			leftGlyphsDict[left][value].append(right)
			rightGlyphsDict[right][value].append(left)


	" Sorting aforementioned lists of glyphs; adding them to a list that contains all the right classes. "
	" Same for the other side. "
	for leftGlyph in leftGlyphsDict:
		for kernValue in leftGlyphsDict[leftGlyph]:
			kernClass = sortGlyphs(leftGlyphsDict[leftGlyph][kernValue])
			allRightClasses.append(kernClass)
	for rightGlyph in rightGlyphsDict:
		for kernValue in rightGlyphsDict[rightGlyph]:
			kernClass = sortGlyphs(rightGlyphsDict[rightGlyph][kernValue])
			allLeftClasses.append(kernClass)
			
	" Counting occurrence and length of those classes; throwing out the ones that have length == 1 or occur only once. "
	for c in allRightClasses:
		occurrence = allRightClasses.count(c)
		if occurrence > 1 and len(c) > 1:
		 	if (occurrence, c) not in potentialRightClasses:
		 		potentialRightClasses.append((occurrence, c))
	for c in allLeftClasses:
		occurrence = allLeftClasses.count(c)
		if occurrence > 1 and len(c) > 1:
		 	if (occurrence, c) not in potentialLeftClasses:
		 		potentialLeftClasses.append((occurrence, c))
	
	" Sorting the potential right classes by occurrence; so we can parse them by importance. "
	potentialRightClasses.sort()
	potentialRightClasses.reverse()
	potentialLeftClasses.sort()
	potentialLeftClasses.reverse()
		

	" Creating a list of KeyGlyphs (basically glyph 0 of the class), to find which of those classes potentially belong together. "
	for i in potentialRightClasses:
		keyGlyph = i[1][0]
		if not keyGlyph in leftKeyGlyphs:
			leftKeyGlyphs.append(keyGlyph)
	for i in potentialLeftClasses:
		keyGlyph = i[1][0]
		if not keyGlyph in rightKeyGlyphs:
			rightKeyGlyphs.append(keyGlyph)
			
	potentialRightClasses = sorted([i[1] for i in potentialRightClasses])
	potentialLeftClasses = sorted([i[1] for i in potentialLeftClasses])

	" Going through the keyglphys, which are sorted by occurrence. Building classes. "
	allRightGlyphsInClass = []
	for keyGlyph in leftKeyGlyphs:
		l = []
		for i in potentialRightClasses:
			if i[0] == keyGlyph:
				l.append(i)
		for i in range(len(l)):
			if len(l) > 1:
				baseSet = set(l[0])
			 	final = list(baseSet.intersection(l[i]))
			else:
				final = l[i]

			final = sortGlyphs(final)

		" Going through the class, removing glyphs that have already previously been assigned to another class. "
		" This happens in reverse order, as otherwise we run into problems during removal. " 
		for glyph in final[::-1]:
			if not glyph in allRightGlyphsInClass:
				allRightGlyphsInClass.append(glyph)
			else:
				final.remove(glyph)
		
		if len(final) == 0:
			continue
		if len(final) == 1:
			allRightGlyphsInClass.remove(final[0])
			continue
		else:
			finalRightClasses.append(final)
			# print nameClass(final, '_RIGHT'), final

	" Same for the other side. "
	allLeftGlyphsInClass = []
	for keyGlyph in rightKeyGlyphs:
		l = []
		for i in potentialLeftClasses:
			if i[0] == keyGlyph:
				l.append(i)
		for i in range(len(l)):
			if len(l) > 1:
				baseSet = set(l[0])
			 	final = list(baseSet.intersection(l[i]))
			else:
				final = l[i]

			final = sortGlyphs(final)

		" Going through the class, removing glyphs that have already previously been assigned to another class. "
		" This happens in reverse order, as otherwise we run into problems during removal. " 
		for glyph in final[::-1]:
			if not glyph in allLeftGlyphsInClass:
				allLeftGlyphsInClass.append(glyph)
			else:
				final.remove(glyph)
		
		if len(final) == 0:
			continue
		if len(final) == 1:
			allLeftGlyphsInClass.remove(final[0])
			continue
		else:
			finalLeftClasses.append(final)
			# print nameClass(final, '_LEFT'), final

	
	# print len(finalLeftClasses), finalLeftClasses
	# print len(finalRightClasses), finalRightClasses
	
	explodedClasses = []
	for leftClass, rightClass in list(itertools.product(finalLeftClasses, finalRightClasses)):
		explodedClasses.extend( list(itertools.product(leftClass, rightClass)))
		
	# 19319 to 2630/555: 
	# 16689 pairs saved!
	classKerning = []
	classKerningKey = {}
	for left, right, value in singlePairsList[::-1]:
		if (left, right) in explodedClasses:
			leftClass = nameClass(askForClass(left, finalLeftClasses), '_LEFT')
			rightClass = nameClass(askForClass(right, finalRightClasses), '_RIGHT')

			classKernPair = leftClass, rightClass, value
			singlePairsList.remove((left, right, value))

			classKerningKey[classKernPair] = (value, left, right)
			if not classKernPair in classKerning: 
				classKerning.append(classKernPair)
			else:
				continue
	
	for i in finalLeftClasses:
		print '%s = [ %s ];' % (nameClass(i, '_LEFT'), ' '.join(i))
	for i in finalRightClasses:
		print '%s = [ %s ];' % (nameClass(i, '_RIGHT'), ' '.join(i))
		
	
	for left, right, value in singlePairsList:
		print 'pos %s %s %s;' % (left, right, value)
	
	print
	for left, right, value in classKerning:
		print 'pos %s %s %s;' % (left, right, value)
			

	# print finalRightClasses

if __name__ == "__main__":
	if len(sys.argv) == 2:
		if os.path.exists(sys.argv[1]):
			fontPath = sys.argv[1]
    		main(fontPath)
	else:
		print "No valid font provided."