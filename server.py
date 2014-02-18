import ConfigParser
import pymongo
from flask import Flask, render_template, request, redirect, url_for, Response
import json
from datetime import datetime
from bson.son import SON
import apiconstants
from operator import itemgetter,attrgetter
import re
from numpy import random
import pandas as pd
import vincent

api = Flask(__name__)

def addFriendlyCountry(inArray):
  for eachCountry in inArray:
    if eachCountry['_id'] in apiconstants.country_code_remap:
      eachCountry['friendly_name'] = apiconstants.country_code_remap[eachCountry['_id']]
    else:
      eachCountry['friendly_name'] = 'Error'
    if eachCountry['_id'] in apiconstants.country_code_3_remap:
      eachCountry['abr3'] = apiconstants.country_code_3_remap[eachCountry['_id']]
    else:
      eachCountry['abr3'] = 'Error'
  return inArray

def addFriendlyIndustry(inArray):
  for eachIndustry in inArray:
    try:
      eachIndustry['friendly_name'] = apiconstants.industry_remap[eachIndustry['_id']]
    except:
      eachIndustry['friendly_name'] = 'Error'
  return inArray

def aggregateIndustry(inArray):
  returnArray = [{'_id':'31-33','friendly_name':'Manufacturing','count':0},
                 {'_id':'44-45','friendly_name':'Retail','count':0},
                 {'_id':'48-49','friendly_name':'Transportation','count':0},
                 {'_id':'52,55','friendly_name':'Finance','count':0}]
  
  for eachIndustry in inArray:
    if eachIndustry['_id'] in ['31','32','33']:
      returnArray[0]['count'] += eachIndustry['count']
      continue
    if eachIndustry['_id'] in ['44','45']:
      returnArray[1]['count'] += eachIndustry['count']
      continue
    if eachIndustry['_id'] in ['48','49']:
      returnArray[2]['count'] += eachIndustry['count']
      continue
    if eachIndustry['_id'] in ['52','55']:
      returnArray[3]['count'] += eachIndustry['count']

    if eachIndustry['_id'] in apiconstants.industry_remap:
        eachIndustry['friendly_name'] = apiconstants.industry_remap[eachIndustry['_id']]
    else:
        eachIndustry['friendly_name'] = 'Error'
    returnArray.append(eachIndustry)

  for idx, eachIndustry in enumerate(returnArray):
    if eachIndustry['count'] == 0:
      del(returnArray[idx])
      
  returnArray = sorted(returnArray,key=itemgetter('count'),reverse=True)
  return returnArray
  

@api.route('/api/get_one')
def getOne():
  return json.dumps(collection.find_one({},{'_id':0}))

@api.route('/api/get_one/pretty')
def getPrettyOne():
  incident = json.dumps(collection.find_one({},{'_id':0}),sort_keys=True, indent=2)
  incident = incident.replace(' ', '&nbsp;')
  incident = incident.replace('\n', '<br />')
  return incident

@api.route('/api/incident_year')
def getIncidentYear():
  answer = {}
  fillzero = []
  years = collection.aggregate([{'$group':{'_id':'$timeline.incident.year','count':{'$sum':1}}},
                                {'$sort' : SON([('count',-1)]) }
                                ]);
  answer['years_by_count'] = years['result']
  answer['years_by_year'] = sorted(answer['years_by_count'],key=itemgetter('_id'),reverse=True)
  answer['count'] = collection.count()
  answer['datetime'] = datetime.utcnow().isoformat()
  maxyear = answer['years_by_year'][0]['_id']
  minyear = answer['years_by_year'][-1]['_id']
  for each in range(maxyear,minyear-1,-1):
    fillzero.append({'_id':each})
  for each in fillzero:
    each['count'] = 0
    for year in answer['years_by_year']:
      if year['_id'] == each['_id']:
        each['count'] = year['count']
  answer['years_by_year_fill_zero'] = fillzero
  
  return json.dumps(answer)

@api.route('/viz/incident_year')
def showIncidentYear():
  return render_template('incident_year.html')

@api.route('/api/timeline')
@api.route('/api/timeline/threshold/<int:thresh>')
def getTimeline(thresh=1000000):
  earliest = int(request.args.get('earliest', '0'))
  answer = {}
  answer['datetime'] = datetime.utcnow().isoformat()
  timesReturned = collection.aggregate([ {'$match':{'attribute.confidentiality.data_total':{'$gte':thresh}}},
                                 {'$match':{'plus.timeline.notification.year':{'$gte':earliest}}},
                                 {'$project':{'_id':0,'year':'$plus.timeline.notification.year','month':'$plus.timeline.notification.month'}}
                                 ])['result']
  times = {}
  timesArray = []
  minyear= 9999
  maxyear=0
  for eachTime in timesReturned:
    if 'year' not in eachTime:
      continue
    if 'month' not in eachTime:
      continue
    if eachTime['year'] < minyear:
      minyear = eachTime['year']
    if eachTime['year'] > maxyear:
      maxyear = eachTime['year']
    timestring = str(eachTime['year']) + str(eachTime['month']).zfill(2)
    times[timestring] = times.get(timestring,0) + 1
  # now we want to add the gap years in
  for year in range(minyear,maxyear+1):
    for month in range(1,13):
      if year == datetime.now().year and month >= datetime.now().month:
        continue
      times[str(year)+str(month).zfill(2)] = times.get(str(year)+str(month).zfill(2),0)
  for eachTime in times.keys():
    timesArray.append({'date':eachTime,'count':times[eachTime]})
  timesArray = sorted(timesArray,key=itemgetter('date'))
  
  observedCounts = []
  for time in timesArray:
    observedCounts.append(time['count'])
  
  # Estimate a lambda for a poisson distribution - just because
  perfectFrequencies = []
  answer['lambda'] = round(float(sum(observedCounts)) / len(timesArray),2)
  perfectPoisson = list(random.poisson(answer['lambda'],5000))
  for i in range( min(perfectPoisson),max(perfectPoisson)):
    perfectFrequencies.append(round(perfectPoisson.count(i) / float(5000),2))
  
  # Build objects for the stats visualization
  categories = ['Poisson','Observed']
  index = []
  observedFrequencies = []
  for i in range(min(min(perfectPoisson),min(observedCounts)),max(max(perfectPoisson),max(observedCounts))):
    index.append(i) # why did I have this as str(i)?
    observedFrequencies.append(round(observedCounts.count(i)/float(len(observedCounts)),2))
  print index
  for i in range(max(index),min(index),-1):
    print "checking if %s is missing from index." % i
    if i not in index:
      print "adding %s to index" % i
      index.insert(i,i)
      perfectFrequencies.insert(i,0.0)
      observedFrequencies.insert(i,0.0)
  # After rounding we sometimes get fields with 0.0 in the observation
  for i in range(max(index),min(index),-1):
    if perfectFrequencies[i] == 0 and observedFrequencies[i] == 0:
      print "popping %s off of the list" % i
      index.pop(i)
      perfectFrequencies.pop(i)
      observedFrequencies.pop(i)
    else:
      break
  #print "observedFrequencies is %s. Sum of that is %s." % (observedFrequencies,sum(observedFrequencies))
  #print "index is %s" % index
  #print "perfectFrequencies is %s. Sum of that is %s." %(perfectFrequencies,sum(perfectFrequencies))

 
  vizData = {'Poisson':perfectFrequencies,'Observed':observedFrequencies}
  df = pd.DataFrame(vizData,index=index)
  #print df
  
  # one last stat
  finalObservedCounts = {}
  for each in observedCounts:
    finalObservedCounts[each] = finalObservedCounts.get(each,0) + 1

  grouped = vincent.GroupedBar(df)
  grouped.width = 800
  grouped.height = 400
  grouped.colors(brew='Set3')
  grouped.axis_titles(x='Number of Breaches', y='Percent')
  grouped.legend(title='Data Category')
  # hack to get the right colors
  grouped.scales[2].range = ['#ED1C24','#4682b4']
  
  answer['count'] = len(times)
  answer['timeline'] = timesArray
  answer['observedCounts'] = finalObservedCounts
  answer['vega'] = grouped.grammar()
  return json.dumps(answer)

@api.route('/api/data_total')
@api.route('/api/data_total/top/<int:returnCount>')
def getDataTotal(returnCount=10):
  answer = {}
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['incidents'] = []
  dataTotal = collection.aggregate([{'$match' : {'attribute.confidentiality.data_total' : {'$gt':1}}}, 
                                    {'$project' : {'_id':0, 
                                                    'year':'$timeline.incident.year',
                                                    'victim':'$victim.victim_id',
                                                    'data_total':'$attribute.confidentiality.data_total',
                                                    'action':1 } },
                                    {'$sort' : SON([("data_total", -1)])},
                                    {'$limit' : returnCount}
                              ]);
  for eachIncident in dataTotal['result']:
    actionArray = []
    for eachAction in eachIncident['action'].keys():
      if 'variety' in eachIncident['action'][eachAction]:
        for eachVariety in eachIncident['action'][eachAction]['variety']:
          actionArray.append(eachAction.title() + ':' + eachVariety)
    # Some incidents have a blank victim. Check for that.
    if 'victim' not in eachIncident.keys():
      eachIncident['victim'] = 'Unknown'
    answer['incidents'].append({'year':eachIncident['year'],
                                'victim':eachIncident['victim'],
                                'actions':actionArray,
                                'data_total':eachIncident['data_total']})

  return json.dumps(answer)

@api.route('/api/data_total/bins')
def getDataBreachBins():
  answer = {}
  bins = {}
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['count'] = collection.find({'attribute.confidentiality.data_total':{'$gt':1}}).count()
  dataBins = collection.aggregate([ {'$match':{'attribute.confidentiality.data_total':{'$gt':1}}},
                                   {'$project':{'_id':0,'data_total':'$attribute.confidentiality.data_total'}}
                                   ]);
  for eachNumber in dataBins['result']:
    binNumber = eachNumber['data_total']/1000
    bins[binNumber] = bins.get(binNumber,0) + 1
  answer['bins'] = bins
  return json.dumps(answer)
  

@api.route('/api/data_total/payment')
@api.route('/api/data_total/payment/top/<int:returnCount>')
def largestPaymentBreaches(returnCount=10):
  answer = {}
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['incidents'] = []
  largestBreaches = collection.aggregate([ {'$unwind':'$attribute.confidentiality.data'},
                                          {'$match':{'attribute.confidentiality.data.variety':'Payment',
                                                     'attribute.confidentiality.data.amount':{'$gt':0}}},
                                          {'$project':{'_id':0,
                                                       'year':'$timeline.incident.year',
                                                       'amount':'$attribute.confidentiality.data.amount',
                                                       'victim':'$victim.victim_id',
                                                       'action':1}},
                                          {'$sort' : SON([("amount", -1)])},
                                          {'$limit' : returnCount}
                                          ]);
  for eachIncident in largestBreaches['result']:
    actionArray = []
    for eachAction in eachIncident['action'].keys():
      if 'variety' in eachIncident['action'][eachAction]:
        for eachVariety in eachIncident['action'][eachAction]['variety']:
          actionArray.append(eachAction.title() + ':' + eachVariety)
    # Some incidents have a blank victim. Check for that.
    if 'victim' not in eachIncident.keys():
      eachIncident['victim'] = 'Unknown'
    answer['incidents'].append({'year':eachIncident['year'],
                                'victim':eachIncident['victim'],
                                'actions':actionArray,
                                'data_total':eachIncident['amount']})
  return json.dumps(answer)

@api.route('/viz/data_total')
@api.route('/viz/data_total/top/<int:returnCount>')
def showDataTotal(returnCount=10):
  return render_template('top-breaches.html',returnCount=returnCount)

@api.route('/api/victims')
def victims():
  answer = {}
  employee_count = collection.aggregate([{"$group":{"_id":"$victim.employee_count","count":{"$sum":1}}},
                                         {"$sort": SON([("count", -1)])}])
  country_count = collection.aggregate([{"$group":{"_id":"$victim.country","count":{"$sum":1}}},
                                        {"$sort": SON([("count", -1)])}])
  industry = collection.aggregate([{'$project':{'pair':{'$substr':['$victim.industry',0,2]}}},
                                   {'$group':{'_id':'$pair','count':{'$sum':1}}},
                                   {"$sort": SON([("count", -1)])}])
  answer['count'] = collection.count()
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['country'] = addFriendlyCountry(country_count['result'])
  answer['employee_count'] = employee_count['result']
  answer['industry'] = addFriendlyIndustry(industry['result'])
  answer['aggregate_industry'] = aggregateIndustry(industry['result'])
    
  answer = json.dumps(answer)
  resp = Response(answer,status=200, mimetype='application/json')
  resp.headers['Access-Control-Allow-Origin'] = '*'
  return resp

@api.route('/api/victims/country/<country_code>')
def victimByCountry(country_code):
  country_code = country_code.upper()
  if country_code not in apiconstants.country_code_remap:
    return "{None}"
  answer = {}
  employee_count = collection.aggregate([ {'$match':{'victim.country':country_code}},
                                         {"$group":{"_id":"$victim.employee_count","count":{"$sum":1}}},
                                         {"$sort": SON([("count", -1)])}
                                         ])
  country = collection.aggregate([ {'$match':{'victim.country':country_code}},
                                  {"$group":{"_id":"$victim.country","count":{"$sum":1}}},
                                  {"$sort": SON([("count", -1)])}
                                  ])
  industry = collection.aggregate([ {'$match':{'victim.country':country_code}},
                                   {'$project':{'pair':{'$substr':['$victim.industry',0,2]}}},
                                   {'$group':{'_id':'$pair','count':{'$sum':1}}},
                                   {"$sort": SON([("count", -1)])}
                                   ])
                                                                       
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['employe_count'] = employee_count['result']
  if len(country['result']) > 0:
    answer['country'] = addFriendlyCountry(country['result'])
  else:
    answer['country'] = []
  if len(industry['result']) > 0:
    answer['industry'] = addFriendlyIndustry(industry['result'])
    answer['aggregate_industry'] = aggregateIndustry(industry['result'])
  else:
    answer['industry'] = []
    answer['aggregate_industry'] = []
  if len(country['result']) > 0:
    answer['count'] = country['result'][0]['count']
  else:
    answer['count'] = 0
  return json.dumps(answer)

@api.route('/api/victims/payment')
def getPaymentVictims():
  answer = {'country':[]}
  answer['datetime'] = datetime.utcnow().isoformat()
  paymentVictims = collection.aggregate([ {'$unwind':'$attribute.confidentiality.data'},
                                          {'$match':{'attribute.confidentiality.data.variety':'Payment',
                                                     'attribute.confidentiality.data.amount':{'$gt':0}}},
                                          {"$group":{"_id":"$victim.country","count":{"$sum":1}}},
                                          {"$sort": SON([("count", -1)])}
                                          ])
  if len(paymentVictims['result']) > 0:
    answer['country'] = addFriendlyCountry(paymentVictims['result'])
  else:
    answer['country'] = []
  return json.dumps(answer)

@api.route('/api/victims/big')
def getBigVictims():
  answer = {}
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['count'] = collection.find({'attribute.confidentiality.data_total':{'$gt':1000000}}).count()
  bigVictims = collection.aggregate([ {'$match':{'attribute.confidentiality.data_total':{'$gt':1000000}}},
                                      {'$project':{'country':'$victim.country','_id':0}},
                                      {'$group':{'_id':'$country','count':{'$sum':1}}},
                                      {'$sort': SON([('count',-1)])}
                                      ])
  if len(bigVictims['result']) > 0:
    answer['country'] = addFriendlyCountry(bigVictims['result'])
  else:
    answer['country'] = []
  return json.dumps(answer)
  

@api.route('/api/victims/naics/<naics>')
@api.route('/api/victims/industry/<naics>')
def victimByEmployee(naics):
  try:
    naics = str(int(naics))
  except:
    return json.dumps({'count':0})
  answer = {}
  regx = re.compile("^"+naics+".*")
  employee_count = collection.aggregate([{'$match':{'victim.industry':{'$regex':regx}}},
                                         {"$group":{"_id":"$victim.employee_count","count":{"$sum":1}}},
                                         {"$sort": SON([("count", -1)])}
                                         ])
  country = collection.aggregate([{'$match':{'victim.industry':{'$regex':regx}}},
                                         {"$group":{"_id":"$victim.country","count":{"$sum":1}}},
                                         {"$sort": SON([("count", -1)])}
                                         ])
  industry = collection.aggregate([{'$match':{'victim.industry':{'$regex':regx}}},
                                   {'$project':{'pair':{'$substr':['$victim.industry',0,2]}}},
                                   {'$group':{'_id':'$pair','count':{'$sum':1}}},
                                   {"$sort": SON([("count", -1)])}
                                   ])
  
  answer['count'] = collection.find({'victim.industry':{'$regex':regx}}).count()
  answer['datetime'] = datetime.utcnow().isoformat()
  answer['employee_count'] = employee_count['result']
  if len(country['result']) > 0:
    answer['country'] = addFriendlyCountry(country['result'])
  else:
    answer['country'] = []
  if len(industry['result']) > 0:
    answer['industry'] = addFriendlyIndustry(industry['result'])
    answer['aggregate_industry'] = aggregateIndustry(industry['result'])
  else:
    answer['industry'] = []
    answer['aggregate_industry'] = []
  return json.dumps(answer)

@api.route('/viz/demo')
def getDemographics():
  return render_template('demo.html')

if __name__ == '__main__':
  config = ConfigParser.RawConfigParser()
  config.read('database.cfg')
  client = pymongo.MongoClient(config.get('database','host'), config.getint('database','port'))
  db = client[config.get('database','db')]
  collection = db[config.get('database','coll')]
  
  api.run(debug=True,host=config.get('server','host'),port=config.getint('server','port'))
  


                              
