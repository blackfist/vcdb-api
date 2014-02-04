import ConfigParser
import pymongo
from flask import Flask, render_template, request, redirect, url_for, Response
import json
from datetime import datetime
from bson.son import SON
import apiconstants
from operator import itemgetter,attrgetter
import re

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
                 {'_id':'48-49','friendly_name':'Transportation','count':0}]
  
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
    answer['incidents'].append({'year':eachIncident['year'],
                                'victim':eachIncident['victim'],
                                'actions':actionArray,
                                'data_total':eachIncident['data_total']})

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
  


                              
