import praw
import datetime
from flask import Flask, render_template, request, redirect
from bs4 import BeautifulSoup
import wikipedia
import time
import nltk.data
from nltk.stem.wordnet import WordNetLemmatizer as wnl
from nltk.tag import pos_tag
import query
import warnings
import const

warnings.filterwarnings("ignore")

nltk.download('punkt',quiet=True)
nltk.download('wordnet',quiet=True)
nltk.download('averaged_perceptron_tagger',quiet=True)

answers=[]

# Process user question into usable chunks; determine question type, keyword to look for, and caveat to focus on
def process(question):
  if const.showlog==1:
    print("[WikiBot] Parsing user question...")
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
    print("[WikiBot] Reading Wikipedia articles for keyword '"+keyword+"'...")
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
    print("[Wikibot] User question was processed into the following chunks.")
    print("          Question type: "+qtype)
    print("          Keyword: "+keyword)
    print("          Caveat: "+caveat)
  return qtype,keyword,caveat,fulltext,summary,sentences,words,categories,display_url

# If caveat is expected but not found, attempt to split the keyword into a new keyword and a caveat
def splitkey(keyword):
  spkeyword=keyword.split()
  hasupper=haslower=0
  for n in range(len(spkeyword)):
    if spkeyword[n][0].isupper()==True:
      hasupper=1
    else:
      haslower=1
  if hasupper==1 and haslower!=1:
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
    print("[WikiBot] Aliasing search query...")
  aldict=const.aliasdict
  allist=list(aldict.values())
  for n in range(0,len(allist)):
    if caveat in allist[n]:
      caveat=list(aldict.keys())[list(aldict.values()).index(allist[n])]
  return caveat

# Guess the answer to a given question using a predetermined ruleset based on question type
def guess(qtype,keyword,caveat,text,categories):
  if const.showlog==1:
    print("[WikiBot] Guessing answer(s)...")
  answers=[]
  if "[when]" in qtype or "year" in caveat:
    if caveat=="":
      caveat="event"
    elif "year" in caveat:
      caveat=caveat.replace("year","")
      caveat=caveat.strip()
    answer=query.timeline(keyword,caveat.lower(),categories,answers)
    answers.append(answer)
    answers=list(filter(lambda c: c!="",answers))
    if len(answers)==0 and caveat!="":
      alcaveat=alias(caveat)
      answer=query.timeline(keyword,alcaveat.lower(),categories,answers)
      answers.append(answer)
    answers=list(filter(lambda c: c!="",answers))
    if len(answers)==0:
      focus=query.relation(keyword,caveat,text)
      for n in range(0,len(focus)):
        answer=query.timeline(keyword,focus[n].lower(),categories,answers)
        answers.append(answer)
    answers=list(filter(lambda c: c!="",answers))
    answers=query.reverse(keyword,caveat,answers)
  elif "[who]" in qtype:
    focus=query.relation(keyword,caveat.lower(),text)
    focus=list(filter(lambda c: c!="",focus))
    if len(focus)==0 and caveat!="":
      alcaveat=alias(caveat)
      focus=query.relation(keyword,alcaveat.lower(),text)
    for n in range(0,len(focus)):
      name=query.identity(keyword,focus[n].lower(),text,answers)
      if type(name)==str:
        answers.append(name)
      elif type(name)==list:
        answers.extend(name)
    answers=list(filter(lambda c: c!="",answers))
    answers=query.reverse(keyword,caveat,answers)
  elif "[null]" in qtype:
    answers.append(query.truefalse(keyword,caveat))
    if answers[0]==False:
      answers[0]=query.truefalse(caveat,keyword)
  else:
    answers=query.relation(keyword,caveat,text)
    answers=list(filter(lambda c: c!="",answers))
  return answers

# Compile valid 'answer's into the 'answers' list
def record(answer):
  answers.append(answer)

# Log into reddit.com using praw then navigate to a target subreddit
bot = praw.Reddit(user_agent='',
                  client_id='',
                  client_secret='',
                  username='',
                  password='')

subreddit = bot.subreddit('')

# Read new comments and reply with an answer
comments = subreddit.stream.comments()
for comment in comments:
  text=comment.body
  text=text.strip()
  author=comment.author
  if '!wiki-buddy' in text.lower() and "Greetings u/" not in comment.replies:
    answers=[]
    question=text.replace("!wiki-buddy","")
    start=time.time()
    try:
      qtype,keyword,caveat,fulltext,summary,sentences,words,categories,display_url=process(question)
    except:
      message="Greetings u/{0}, I was unable to understand your question.".format(author)
      comment.reply(message)

    if const.showlog==1:
      print("[WikiBot] Analyzing summary...")
    answers=guess(qtype,keyword,caveat,summary,categories)
    try:
      for n in range(0,len(answers)):
        answers[n]=str(answers[n])
        if answers[n].isnumeric()==False:
          answers[n] = wnl().lemmatize(answers[n])
    except:
      pass
    if len(answers)==0 or "[who]" in qtype:
      if const.showlog==1:
        print("[WikiBot] Analyzing full text; this may be a lengthy process...")
      guesses=guess(qtype,keyword,caveat,fulltext,categories)
      if type(guesses)==str:
        answers.append(guesses)
      elif type(guesses)==list:
        answers.extend(guesses)
      try:
        for n in range(0,len(answers)):
          answers[n]=str(answers[n])
          if answers[n].isnumeric()==False:
            answers[n] = wnl().lemmatize(answers[n])
      except:
        pass
    answers=list(dict.fromkeys(answers))
    answers=list(filter(lambda c: c!="",answers))
    done=time.time()
    duration=done-start
    if const.showlog==1:
      print("[WikiBot] Took " + str(duration) + " seconds to query this question.")
    if len(answers)==0:
      message="Greetings u/{0}, I was unable to find an answer for your question.".format(author)
    else:
      message="Greetings u/{0}, here are your answers: ".format(author)
      answerstr=", ".join(answers)
      message=message+answerstr
    comment.reply(message)