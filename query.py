from bs4 import BeautifulSoup
import wikipedia
import nltk.data
from nltk.stem.wordnet import WordNetLemmatizer as wnl
from nltk.tag import pos_tag
from nltk.corpus import wordnet
from nltk.tag import pos_tag
import const
import wikipedia
from collections import OrderedDict
import warnings

warnings.filterwarnings("ignore")

nltk.download('punkt',quiet=True)
nltk.download('wordnet',quiet=True)
nltk.download('averaged_perceptron_tagger',quiet=True)

# Process user question into usable chunks; determine question type, keyword to look for, and caveat to focus on
def process(question):
  if const.showlog==1:
    print("[wiki-buddy] Parsing user question...")
  question=question.replace("?","")
  spquestion=question.split()
  tagwords=pos_tag(spquestion)
  verbindex=[]
  caveat=""
  splitnouns=False
  rawqtype=[word for word, pos in tagwords if pos=='WDT' or pos=='WP' or pos=='WP$' or pos=='WRB']
  rawverb=[word for word, pos in tagwords if pos=='VB' or pos=='VBD' or pos=='VBG' or pos=='VBN' or pos=='VBP' or pos=='VBZ' or pos=='TO']
  for a in range(0,len(spquestion)):
    for n in range(0,len(rawqtype)):
      if rawqtype[n] in spquestion[a]:
        spquestion[a]=""
    for n in range(0,len(rawverb)):
      if rawverb[n] in spquestion[a]:  
        spquestion[a]=""
        verbindex.append(a)
  if verbindex[0]>1:
    for n in range(1,verbindex[0]):
      caveat=caveat+" "+spquestion[n]
    caveat=caveat.strip()
    question=question.replace(caveat," ")
    spquestion=question.split()
    tagwords=pos_tag(spquestion)
  pindex=[word for word, pos in tagwords if pos=='NNP' or pos=='NNPS']
  if len(pindex)>0:
    rawnoun=[word for word, pos in tagwords if pos=='NN' or pos=='NNS' or pos=='NNP' or pos=='NNPS' or pos=='IN' or pos=='CC' or pos=='CD' or pos=='JJ' or pos=='JJR' or pos=='JJS']
  else:
    rawnoun=[word for word, pos in tagwords if pos=='NN' or pos=='NNS' or pos=='IN' or pos=='CC' or pos=='CD' or pos=='JJ' or pos=='JJR' or pos=='JJS']
  useless=[word for word, pos in tagwords if pos=='DT']
  for a in range(0,len(spquestion)):
    for n in range(0,len(rawnoun)):
      if rawnoun[n] in spquestion[a]:
        spquestion[a]=""
    for n in range(0,len(useless)):
      if useless[n] in spquestion[a]:
        spquestion[a]=""
  question=" ".join(spquestion)
  qtype=" ".join(rawqtype)
  for n in range(0,len(rawverb)):
    if rawverb[n] in const.omitverblist:
      rawverb[n]=""
  verb=" ".join(rawverb)
  keyword=" ".join(rawnoun)
  verb=verb.strip()
  caveat=caveat+" "+verb
  qtype=qtype.strip()
  keyword=keyword.strip()
  caveat=caveat.strip()
  qtype="["+qtype.lower()+"]"
  
  keyword=wnl().lemmatize(keyword)
  caveat=caveat.strip()

  if caveat=="" and " " in keyword:
    keyword,caveat=splitkey(keyword)

  tokenizer=nltk.data.load('tokenizers/punkt/english.pickle')
  if const.showlog==1:
    print("[wiki-buddy] Reading Wikipedia articles for keyword '"+keyword+"'...")
  display_url=""
  try:
    rawdata=wikipedia.page(title = keyword,auto_suggest = True)
    fulltext=rawdata.content
    display_url=rawdata.url
  except:
    fulltext=""
  try:
    summary=wikipedia.summary(keyword)
  except:
    summary=""
  try:
    categories=wikipedia.page(title = keyword,auto_suggest = True).categories
  except:
    categories=[]
  if fulltext!="":
    sentences=nltk.sent_tokenize(fulltext)
    for n in range(0,len(const.omitpuctlist)):
      fulltext=fulltext.replace(const.omitpuctlist[n],"")
  elif summary!="":
    sentences=nltk.sent_tokenize(summary)
    for n in range(0,len(const.omitpuctlist)):
      summary=summary.replace(const.omitpuctlist[n],"")
  else:
    qtype="[null]"
    sentences=[]
  words=fulltext.split()
  for n in range(0,len(words)):
    words[n] = wnl().lemmatize(words[n])
  if const.showlog==1:
    print("[wiki-buddy] User question was processed into the following chunks.")
    print("             Question type: "+qtype)
    print("             Keyword: "+keyword)
    print("             Caveat: "+caveat)
  return qtype,keyword,caveat,fulltext,summary,sentences,words,categories,display_url

# If caveat is expected but not found, attempt to split the keyword into a new keyword and a caveat
def splitkey(keyword):
  spkeyword=keyword.split()
  hasupper=haslower=False
  for n in range(len(spkeyword)):
    if spkeyword[n][0].isupper()==True:
      hasupper=True
    else:
      haslower=True
  if hasupper==True and haslower==False:
    return keyword,""
  tagwords=pos_tag(spkeyword)
  pindex=[word for word, pos in tagwords if pos=='NNP' or pos=='NNPS']
  if len(pindex)>0:
    tempkey=" ".join(pindex)
  caveat=keyword.replace(tempkey,"")
  caveat=caveat.strip()
  keyword=tempkey.strip()
  return keyword,caveat

# Alias caveat into terms used by Wikipedia categories
def alias(caveat):
  if const.showlog==1:
    print("[wiki-buddy] Aliasing search query...")
  aldict=const.aliasdict
  allist=list(aldict.values())
  for n in range(0,len(allist)):
    if caveat in allist[n]:
      caveat=list(aldict.keys())[list(aldict.values()).index(allist[n])]
  return caveat

# Timeline analysis using Wikipedia categories
def timeline(keyword,caveat,categories,answers):
  spcat=[]
  index=-1
  suffix=""
  if const.showlog==1:
    print("[wiki-buddy] Running Timeline query for '"+caveat+"' with '"+keyword+"'...")
  for n in range(0,len(categories)):
    if caveat in categories[n]:
      if index==-1:
        spcat=categories[n].split()
        for i in range(0,len(spcat)):
          if "century" in spcat[i] and spcat[i] not in answers:
            index=i-1
            suffix="century"
          elif spcat[i].isnumeric()==True and spcat[i] not in answers:
            index=i
          elif spcat[i]=="BC" or spcat[i]=="AD" and i==index:
            suffix=suffix+" "+spcat[i]
      else:
        break
  if index!=-1:
    year=spcat[index]+" "+suffix
    year=year.strip()
  else:
    year=""
  return year

# Use synsets to find words on the keyword Wikipedia page that are similar to caveat, word candidates are then processed into finalists
def relation(keyword,caveat,text):
  sptext=text.split()
  for a in range(0,len(const.omitpuctlist)):
    for b in range(0,len(sptext)):
      if const.omitpuctlist[a] in sptext[b]:
        sptext[b]=sptext[b].replace(const.omitpuctlist[a],"")
  candids=[]
  finals=[]
  sscore=0
  fscore=0
  if const.showlog==1 and caveat!="":
    print("[wiki-buddy] Running Relational query for '"+caveat+"' with '"+keyword+"'...")
  elif const.showlog==1 and caveat=="":
    print("[wiki-buddy] Running Definitional query for '"+keyword+"'...")
    sentences=nltk.sent_tokenize(text)
    candids.append(sentences[0])
    return candids
  for n in range(0,len(sptext)):
    try:
      syn1=wordnet.synsets(caveat)[0]
      syn2=wordnet.synsets(sptext[n])[0]
      sscore=wordnet.path_similarity(syn1,syn2)
      if sscore==1:
        finals.append(sptext[n])
      if sscore>=0.25:
        candids.append(sptext[n])
    except:
      if str(caveat).lower() in str(sptext[n]).lower():
        finals.append(sptext[n])
  candids=[x for x in candids ]
  if len(candids)==0:
    try:
      for syn in wordnet.synsets(caveat): 
        for l in syn.lemmas(): 
          synonyms.append(l.name()) 
        for n in range(0,len(synonyms)):
          synonyms[n]=synonyms[n].replace("_"," ")
    except:
      pass
    try:
      for a in range(0,len(synonyms)):
        for b in range(0,len(sptext)):
          syn1=wordnet.synsets(synonyms[a])[0]
          syn2=wordnet.synsets(sptext[b])[0]
          sscore=wordnet.path_similarity(syn1,syn2)
          if sscore>=0.25:
            candids.append(sptext[b])
    except:
      pass
  candids=list(dict.fromkeys(candids)) #remove duplicates from candidates list
  for n in range(0,len(candids)):
    try:
      dictdef=wordnet.synsets(candids[n])[0].definition()
    except:
      dictdef=""
    if caveat in dictdef:
      finals.append(candids[n])
  finals=list(dict.fromkeys(finals))
  if len(finals)>0:
    return finals
  else:
    if const.showlog==1:
      print("[wiki-buddy] Using fuzzy search parameters; this may result in inaccurate results.")
    return candids

# Attempt to isolate proper nouns following the focus word that are being looked for
def identity(keyword,focus,text,answers):
  name=""
  if const.showlog==1:
    print("[wiki-buddy] Running Identity query for '"+focus+"' on '"+keyword+"'...")
  if text=="":
    pass
  else:
    sptext=text.split()
    tagwords=pos_tag(sptext)
    rawnames=[word for word, pos in tagwords if pos=='NNP' or pos=='NNPS' or pos=='NN' or pos=='NNS']
    for a in range(0,len(rawnames)):
      for b in range(0,len(const.monthlist)):
        if rawnames[a]==const.monthlist[b]:
          rawnames[a]=""
    names=" ".join(rawnames)
    for a in range(0,len(sptext)):
      if focus.lower() in sptext[a].lower():
        i=1
        try:
          nextwords=" "+sptext[a]
          while i<=10:
            nextwords=nextwords+" "+sptext[a+i]
            i=i+1
        except:
          pass
        if "by " in nextwords:
          b=1
        else:
          b=-2
        while a+b<len(sptext):
          if name!="" and sptext[a+b] not in names:
            break
          elif sptext[a+b] in const.aconjuctlist and sptext[a+b+1] in names and sptext[a+b+1][0].isupper()==True:
            name=name+" "+sptext[a+b]
            b=b+1
          elif sptext[a+b] in names and sptext[a+b][0].isupper()==True:
            if "." in sptext[a+b] or "," in sptext[a+b]:
              try:
                sample=sptext[a+b+2]
                if sample not in names or sample[0].isupper()==False:
                  if sample=="and" or sample=="or":
                    name=name+" "+sptext[a+b]
                    b=b+1
                  else:
                    name=name+" "+sptext[a+b]
                    break
                else:
                  name=name+" "+sptext[a+b]
                  b=b+1
              except:
                name=name+" "+sptext[a+b]
                b=b+1
            elif sptext[a+b].lower() in keyword.lower():
              b=b+1
            else:
              name=name+" "+sptext[a+b]
              b=b+1
          else:
            try:
              nextword=sptext[a+b+1]
              if sptext[a+b] in const.namepreplist and nextword in names and nextword[0].isupper()==True:
                name=name+" "+sptext[a+b]
            except:
              pass
            b=b+1
  #name string cleanup
  for n in range(0,len(const.natnllist)):
    if const.natnllist[n] in name:
      name=name.replace(const.natnllist[n],"")
  for n in range(0,len(const.natnmlist)):
    if const.natnmlist[n] in name:
      name=name.replace(const.natnmlist[n],"")
  for n in range(0,len(answers)):
    if answers[n] in name:
      name=name.replace(answers[n],"")
  name=name.strip()
  if len(name)>0:
    print(name)
    for n in range(0,len(const.omitpuctlist)):
      if len(name)>0:
        while const.omitpuctlist[n]==name[0] or const.omitpuctlist[n]==name[len(name)-1]:
          name=name.strip()
          if len(name)<=1:
            name=""
            break
          if const.omitpuctlist[n]==name[0]:
            name=name[1:]
          if const.omitpuctlist[n]==name[len(name)-1]:
            name=name[:len(name)-1]
          name=name.strip()
          if len(name)<=1:
            name=""
            break
    name=name.strip()
    namelist=[]
    for n in range(0,len(const.aconjuctlist)):
      if const.aconjuctlist[n]==",":
        cj=const.aconjuctlist[n]
      else:
        cj=" "+const.aconjuctlist[n]+" "
      if cj in name:
        namelist.extend(name.split(cj))
        name=""
        for a in range(0,len(namelist)):
          for b in range(0,len(const.aconjuctlist)):
            if const.aconjuctlist[b] in namelist[a]:
              name=name+namelist[a]
    for n in range(0,len(namelist)):
      namelist[n]=namelist[n].strip()
    splimit=1
    for n in range(0,len(const.namepreplist)):
      if " "+const.namepreplist[n]+" " in name:
        splimit=2
    if name.count(" ")>splimit and name.count(".")<1:
      temp=name.split()
      for n in range(0,len(temp),2):
        namelist.append(" ".join(temp[n:n+2]))
    if len(namelist)>1:
      return namelist
  return name

# Query Wikipedia for the answers and validate them depending on whether the keyword itself can be found
def reverse(keyword,caveat,answers):
  occurdict={}
  try:
    spkeyword=str(keyword).split()
    searchtitle=wikipedia.search(keyword)[0]
    spsearch=searchtitle.split()
    for n in range(0,len(spsearch)):
      if "(" in spsearch[n] or ")" in spsearch[n]:
        spsearch[n]=""
    searchtitle=" ".join(spsearch)
    searchtitle=searchtitle.strip()
    for n in range(0,len(spkeyword)):
      if spkeyword[n].lower() not in searchtitle.lower():
        spkeyword[n]=""
    searchkey=" ".join(spkeyword)
    searchkey=searchkey.strip()
    if searchkey=="":
      searchkey=searchtitle
  except:
    searchkey=keyword
  for n in range(0,len(answers)):
    if const.showlog==1:
      print("[wiki-buddy] Running Reverse query for '"+answers[n]+"' on query '"+searchkey+"'...")
    try:
      rawdata=wikipedia.page(title = answers[n],auto_suggest = False)
      fulltext=rawdata.content
      fulltext=fulltext.lower()
    except:
      fulltext=""
    occur=0
    while searchkey.lower() in fulltext:
      fulltext=fulltext.replace(searchkey.lower(),"",1)
      occur=occur+1
    if occur>0:
      occurdict.update({occur:answers[n]})
    else:
      if " " in searchkey:
        tempkey=searchkey.lower()
        spsearchkey=tempkey.split()
        for i in range(0,len(spsearchkey)):
          if spsearchkey[i] in fulltext:
            fulltext=fulltext.replace(spsearchkey[i],"")
            occur=occur+1
        if occur>len(spsearchkey)/2:
          occurdict.update({0:answers[n]})
  finaldict=OrderedDict(sorted(occurdict.items(), reverse=True, key=lambda t: t[0]))
  if const.showlog==1:
      print("[wiki-buddy] ",end="")
  print(finaldict)
  return list(finaldict.values())

# Basic True or False analysis using frequency analysis
def truefalse(keyword,caveat):
  caveat=str(caveat)
  keyword=str(keyword)
  if const.showlog==1:
      print("[wiki-buddy] Running True/False analysis for '"+caveat+"' on '"+keyword+"'...")
  try:
    rawdata=wikipedia.page(title = keyword,auto_suggest = True)
    fulltext=rawdata.content
    fulltext=fulltext.lower()
    words=fulltext.split()
  except:
    return False
  totcount=len(words)
  cavcount=0
  syncount=0
  antcount=0
  if " " not in caveat:
    for a in range(0,len(const.omitpuctlist)):
      for b in range(0,len(words)):
        if const.omitpuctlist[a] in words[b]:
          words[b]=words[b].lower()
          words[b]=words[b].replace(const.omitpuctlist[a],"")
          words[b]=words[b].strip()
    caveat=caveat.lower()
    worddict={}
    decision=False
    for n in range(0,len(words)):
      if words[n] not in worddict:
        worddict.update({words[n]:1})
      else:
        worddict[words[n]]=worddict[words[n]]+1
    if caveat in worddict:
      cavcount=worddict.get(caveat)
    synonyms=[]
    antonyms=[]
    for syn in wordnet.synsets(caveat): 
      for l in syn.lemmas(): 
        synonyms.append(l.name()) 
        if l.antonyms(): 
          antonyms.append(l.antonyms()[0].name()) 
    for n in range(0,len(synonyms)):
      synonyms[n]=synonyms[n].replace("_"," ")
      if synonyms[n] in worddict:
        syncount=worddict.get(synonyms[n])
      else:
        pass
    for n in range(0,len(antonyms)):
      antonyms[n]=antonyms[n].replace("_"," ")
      if antonyms[n] in worddict:
        antcount=worddict.get(antonyms[n])
      else:
        pass
    score=cavcount*5+syncount-antcount
  else:
    while caveat in fulltext:
      fulltext=fulltext.replace(caveat,"",1)
      cavcount=cavcount+1 
    score=cavcount*20
  if score>=totcount/1000:
    return True
  else:
    return False