from flask import Flask, render_template, request, redirect
import time
import query
import const

answers=[]

# Guess the answer to a given question using a predetermined ruleset based on question type
def guess(qtype,keyword,caveat,text,categories):
  if const.showlog==1:
    print("[wiki-buddy] Guessing answer(s)...")
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
      alcaveat=query.alias(caveat)
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
      alcaveat=query.alias(caveat)
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

# Flask app handling
app = Flask('app')

@app.route('/')
def hello_world():
  print("\033[H\033[J")
  global answers
  answers=[]
  return render_template('index.html',question="",display_result="",display_url="")

@app.route('/submit', methods=['GET','POST'])
def sumbit():
  global answers
  answers=[]
  question=request.form["question"]
  start=time.time()
  try:
    qtype,keyword,caveat,fulltext,summary,sentences,words,categories,display_url=query.process(question)
  except:
    return render_template('index.html', question=question,display_result="This question structure is unsupported.", display_url="")
  if "how" in qtype:
    return render_template('index.html', question=question,display_result="This question is too vague.", display_url="")
  if const.showlog==1:
    print("[wiki-buddy] Analyzing summary...")
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
      print("[wiki-buddy] Analyzing full text; this may be a lengthy process...")
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
    print("[wiki-buddy] Took " + str(duration) + " seconds to answer this question.")

  display_result=", ".join(answers)
  display_result=display_result.strip()
  if display_result=="":
    display_result="None were found for this question."
  return render_template('index.html', question=question,display_result=display_result,display_url=display_url)

if 'app'=='__main__':
    app.run()

app.run(host='0.0.0.0',port=5000)