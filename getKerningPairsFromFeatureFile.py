#!/usr/bin/python
import sys
import os
import re
import itertools


__doc__ = '''\

Prints a list of all kerning pairs to be expected from a kern feature file; 
which has to be passed to the script as an argument. 
Has the ability to use a GlyphOrderAndAliasDB file for translation of "friendly" 
glyph names to final glyph names.

Usage:
------
python getKerningPairsFromFeatureFile.py <path to kern feature file>
python getKerningPairsFromFeatureFile.py -go <path to GlyphOrderAndAliasDB file> <path to kern feature file>

'''

# Regular expressions for parsing individual kerning commands:
x_range_range = re.compile(r'\s*(enum)?\s+?pos\s*\[\s*(.+?)\s*\]\s+?\[\s*(.+?)\s*\]\s+?(-?\d+?);')
x_range_glyph = re.compile(r'\s*(enum)?\s+?pos\s*\[\s*(.+?)\s*\]\s+?(.+?)\s+?(-?\d+?);')
x_glyph_range = re.compile(r'\s*(enum)?\s+?pos\s+?(.+?)\s+?\[\s*(.+?)\s*\]\s+?(-?\d+?);')        
x_item_item = re.compile(r'\s*(enum)?pos\s+?(.+?)\s+?(.+?)\s+?(-?\d+?);')
expressions = [x_range_range, x_range_glyph, x_glyph_range, x_item_item]



class KernFeatureReader(object):

    def __init__(self, options):
        
        self.goadbPath = None
        self.options = options

        if "-go" in self.options:
            self.goadbPath =  self.options[self.options.index('-go')+1]

        self.featureFilePath = self.options[-1]

        self.featureData = self.readFile(self.featureFilePath)
        self.kernClasses = self.readKernClasses()

        self.singleKerningPairs = {}
        self.classKerningPairs = {}

        self.foundKerningPairs = self.parseKernLines()
        self.flatKerningPairs = self.makeFlatPairs()

        if self.goadbPath:
            self.glyphNameDict = {}
            self.readGOADB()
            self.flatKerningPairs = self.convertNames(self.flatKerningPairs)


        self.output = []
        for (left, right), value in self.flatKerningPairs.items():
            self.output.append('/%s /%s %s' % (left, right, value))
        self.output.sort()


    def readFile(self, filePath):
        # reads raw file, removes commented lines
        lineList = []
        inputfile = open(filePath, 'r')
        data = inputfile.read().splitlines()
        inputfile.close()
        for line in data:
            if '#' in line: 
                line = line.split('#')[0]
            if line:
                lineList.append(line)

        lineString = '\n'.join(lineList)
        return lineString


    def convertNames(self, pairDict):
        newPairDict = {}
        for (left, right), value in pairDict.items():
            newLeft = self.glyphNameDict.get(left)
            newRight = self.glyphNameDict.get(right)

            # in case the glyphs are not in the GOADB:
            if not newLeft:
                newLeft = left
            if not newRight:
                newRight = right
            
            newPair = (newLeft, newRight)
            newPairDict[newPair] = value

        return newPairDict


    def readKernClasses(self):
        allClassesList = re.findall(r"(@\S+)\s*=\s*\[([ A-Za-z0-9_.]+)\]\s*;", self.featureData)

        classes = {}
        for name, glyphs in allClassesList:
            classes[name] = glyphs.split()

        return classes


    def allCombinations(self, left, right):
        if len(left.split()) > 1:
            # The left kerning object is something like [ a b c ] or [ a @MMK_x c ]:
            leftGlyphs = []
            leftItems = left.split()
            for item in leftItems:
                classFound = self.kernClasses.get(item, None)
                if classFound:
                    leftGlyphs.extend(classFound)
                else:
                    leftGlyphs.append(item)

        else:
            # The left kerning object is something like x or @MMK_x:
            leftGlyphs = self.kernClasses.get(left, [left])
        
        if len(right.split()) > 1:
            # The right kerning object is something like [ a b c ] or [ a @MMK_x c ]:
            rightGlyphs = []
            rightItems = right.split()
            for item in rightItems:
                classFound = self.kernClasses.get(item, None)
                if classFound:
                    rightGlyphs.extend(classFound)
                else:
                    rightGlyphs.append(item)
        else:
            # The right kerning object is something like x or @MMK_x:
            rightGlyphs = self.kernClasses.get(right, [right])
        

        combinations = list(itertools.product(leftGlyphs, rightGlyphs))
        return combinations


    def parseKernLines(self):
        featureLines = self.featureData.splitlines()
        foundKerningPairs = []
        for line in featureLines:
            for expression in expressions:
                match = re.match(expression, line) 
                if match:
                    foundKerningPairs.append([match.group(1),match.group(2),match.group(3),match.group(4)])
                    break
                else:
                    # a line that is not found by any of the expressions
                    continue
        return foundKerningPairs


    def makeFlatPairs(self):
        flatKerningPairs = {}

        for enum, left, right, value in self.foundKerningPairs:
            if enum:
                # shorthand for enumerating a single line into multiple single pairs
                for combo in self.allCombinations(left, right):
                    self.singleKerningPairs[combo] = value

            elif not '@' in left and not '@' in right:
                # glyph-to-glyph kerning
                self.singleKerningPairs[(left, right)] = value

            else:
                # class-to-class, class-to-glyph, or glyph-to-class kerning
                for combo in self.allCombinations(left, right):
                    self.classKerningPairs[combo] = value


        flatKerningPairs.update(self.classKerningPairs)
        flatKerningPairs.update(self.singleKerningPairs) # overwrites any given class kern values with exceptions.

        return flatKerningPairs


    def readGOADB(self):
        goadbData = self.readFile(self.goadbPath)
        allNamePairs = re.findall(r"(\S+?)\t(\S+?)(\t\S+?)?\n", goadbData)

        for finalName, workingName, override in allNamePairs:
            self.glyphNameDict[workingName] = finalName


if len(sys.argv) > 1:

    options = sys.argv[1:]
    kernFile = options[-1]

    if os.path.exists(kernFile) and os.path.splitext(kernFile)[-1] in ['.fea', '.kern']:
        kfr=KernFeatureReader(options)

        # print kfr.flatKerningPairs

        print '\n'.join(kfr.output)
        print
        print 'single kerning pairs:', len(kfr.singleKerningPairs)
        print ' class kerning pairs:', len(kfr.classKerningPairs)
        print '\nTotal number of kerning pairs:\n', len(kfr.flatKerningPairs)

    else:
        print "No valid kern feature file provided."

else:
    print "No valid kern feature file provided."

