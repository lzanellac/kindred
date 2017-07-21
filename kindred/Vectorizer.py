
from collections import Counter
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from scipy.sparse import coo_matrix, csr_matrix, lil_matrix, hstack, vstack

import kindred
from kindred.VERSE_vectorizer import VERSEVectorizer

class Vectorizer2:
	"""
	Vectorizes set of candidate relations into scipy sparse matrix.
	"""
	
	def __init__(self,featureChoice=None,tfidf=True):
		self.verseVectorizer = None
		self.featureChoice = featureChoice
		self.tfidf = tfidf
		
	def getFeatureNames(self):
		assert not self.verseVectorizer is None, "Must have fit data first"
		return self.verseVectorizer.getFeatureNames()
				
	def fit_transform(self,corpus):
		assert self.verseVectorizer is None, "Vectorizer has already been fit. Use transform() instead"
		assert isinstance(corpus,kindred.Corpus)
			
		self.verseVectorizer = VERSEVectorizer(corpus,self.featureChoice,self.tfidf)
		return self.verseVectorizer.getTrainingVectors()
		
	def transform(self,corpus):
		assert not self.verseVectorizer is None, "Vectorizer has not been fit. Use fit() or fit_transform() first"
		assert isinstance(corpus,kindred.Corpus)
		
		return self.verseVectorizer.vectorize(corpus)
		



class Vectorizer:
	"""
	Vectorizes set of candidate relations into scipy sparse matrix.
	"""
	
	def __init__(self,featureChoice=None,tfidf=True):
		self.fitted = False
		
		validFeatures = ["selectedTokenTypes","ngrams_betweenEntities"]
		if featureChoice is None:
			self.chosenFeatures = validFeatures
		else:
			for f in featureChoice:
				assert f in validFeatures, "Feature (%s) is not a valid feature" % f
			self.chosenFeatures = featureChoice
		
		self.tfidf = tfidf

		self._registerFunctions()
		self.dictVectorizers = {}
		self.tfidfTransformers = {}

	def _registerFunctions(self):
		self.featureInfo = {}
		self.featureInfo['selectedTokenTypes'] = {'func':Vectorizer.doSelectedTokenTypes,'never_tfidf':True}
		self.featureInfo['ngrams_betweenEntities'] = {'func':Vectorizer.doNGramsBetweenEntities,'never_tfidf':False}
		
	def getFeatureNames(self):
		assert self.fitted == True, "Must have fit data first"
		featureNames = []
		for feature in self.chosenFeatures:
			featureNames += self.dictVectorizers[feature].get_feature_names()
		return featureNames
		

	def doSelectedTokenTypes(self,corpus):
		entityMapping = corpus.getEntityMapping()
		data = []
		for cr in corpus.getCandidateRelations():
			tokenInfo = {}
			for argI,eID in enumerate(cr.entityIDs):
				eType = entityMapping[eID].entityType
				argName = "selectedtokentypes_%d_%s" % (argI,eType)
				tokenInfo[argName] = 1
			data.append(tokenInfo)
		return data
	
	def doNGramsBetweenEntities(self,corpus):
		entityMapping = corpus.getEntityMapping()
		data = []	
		for doc in corpus.documents:
			for sentence in doc.sentences:
				for cr,_ in sentence.candidateRelationsWithClasses:
					dataForThisCR = Counter()

					assert len(cr.entityIDs) == 2
					pos1 = sentence.entityIDToLoc[cr.entityIDs[0]]
					pos2 = sentence.entityIDToLoc[cr.entityIDs[1]]
					
					if max(pos1) < min(pos2):
						startPos,endPos = max(pos1)+1,min(pos2)
					else:
						startPos,endPos = max(pos2)+1,min(pos1)

					tokenData = [ sentence.tokens[i].word.lower() for i in range(startPos,endPos) ]
					for t in tokenData:
						dataForThisCR[u"ngrams_betweenentities_%s" % t] += 1
					data.append(dataForThisCR)

		return data

	def _vectorize(self,corpus,fit):
		assert isinstance(corpus,kindred.Corpus)
			
		matrices = []
		for feature in self.chosenFeatures:
			assert feature in self.featureInfo.keys()
			featureFunction = self.featureInfo[feature]['func']
			never_tfidf = self.featureInfo[feature]['never_tfidf']
			data = featureFunction(self,corpus)
			if fit:
				self.dictVectorizers[feature] = DictVectorizer()
				if self.tfidf and not never_tfidf:
					self.tfidfTransformers[feature] = TfidfTransformer()
					intermediate = self.dictVectorizers[feature].fit_transform(data)
					matrices.append(self.tfidfTransformers[feature].fit_transform(intermediate))
				else:
					matrices.append(self.dictVectorizers[feature].fit_transform(data))
			else:
				if self.tfidf and not never_tfidf:
					intermediate = self.dictVectorizers[feature].transform(data)
					matrices.append(self.tfidfTransformers[feature].transform(intermediate))
				else:
					matrices.append(self.dictVectorizers[feature].transform(data))

		mergedMatrix = hstack(matrices)
		return mergedMatrix
			
	def fit_transform(self,corpus):
		assert self.fitted == False
		self.fitted = True
		return self._vectorize(corpus,True)
	
	def transform(self,corpus):
		assert self.fitted == True
		return self._vectorize(corpus,False)
		
		
	
