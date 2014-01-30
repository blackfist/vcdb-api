import ConfigParser
import pymongo
from flask import Flask, render_template, request, redirect, url_for, Response
import json
from datetime import datetime
from bson.son import SON
from collections import defaultdict
import apiconstants
from operator import itemgetter,attrgetter
api = Flask(__name__)

def addFriendlyCountry(inArray):
  for eachCountry in inArray:
    try:
      eachCountry['friendly_name'] = apiconstants.country_code_remap[eachCountry['_id']]
    except:
      eachCountry['friendly_name'] = 'Error'
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
    try:
      eachIndustry['friendly_name'] = apiconstants.industry_remap[eachIndustry['_id']]
      returnArray.append(eachIndustry)
    except:
      eachIndustry['friendly_name'] = 'Error'
      returnArray.append(eachIndustry)
    # Neither of these sorting options work properly. The output is sorted, but 
    # the value of some fields gets set to zero
    #returnArray = sorted(returnArray,key=itemgetter('count'),reverse=True)
    returnArray.sort(key=itemgetter('count'),reverse=True)
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

@api.route('/api/victims')
def victims():
  answer = {}
  answer['count'] = collection.count()
  answer['datetime'] = datetime.utcnow().isoformat()
  employee_count = collection.aggregate([{"$group":{"_id":"$victim.employee_count","count":{"$sum":1}}},{"$sort": SON([("count", -1)])}])
  answer['employee_count'] = employee_count['result']
  country_count = collection.aggregate([{"$group":{"_id":"$victim.country","count":{"$sum":1}}},{"$sort": SON([("count", -1)])}])
  answer['country'] = addFriendlyCountry(country_count['result'])
  industry = collection.aggregate([{'$project':{'pair':{'$substr':['$victim.industry',0,2]}}},{'$group':{'_id':'$pair','count':{'$sum':1}}},{"$sort": SON([("count", -1)])}])
  answer['industry'] = addFriendlyIndustry(industry['result'])
  answer['aggregate_industry'] = aggregateIndustry(industry['result'])
    
  answer = json.dumps(answer)
  resp = Response(answer,status=200, mimetype='application/json')
  resp.headers['Access-Control-Allow-Origin'] = '*'
  return resp

@api.route('/api/victims/country/<country_code>')
def victimByCountry(country_code):
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
  answer['country'] = addFriendlyCountry(country['result'])
  answer['industry'] = addFriendlyIndustry(industry['result'])
  answer['aggregate_industry'] = aggregateIndustry(industry['result'])
  answer['count'] = country['result'][0]['count']
  return json.dumps(answer)


if __name__ == '__main__':
  config = ConfigParser.RawConfigParser()
  config.read('database.cfg')
  client = pymongo.MongoClient(config.get('database','host'), config.getint('database','port'))
  db = client[config.get('database','db')]
  collection = db[config.get('database','coll')]
  
  api.run(debug=True,host=config.get('server','host'),port=config.getint('server','port'))
  


                              
