import ConfigParser
import pymongo
from flask import Flask, render_template, request, redirect, url_for, Response
import json
from datetime import datetime
from bson.son import SON
from collections import defaultdict

api = Flask(__name__)

industry_remap = {'11':'Agriculture','21':'Mining','22':'Utilities',
                  '23':'Construction','31':'Manufacturing','32':'Manufaturing',
                  '33':'Manufacturing','42':'Wholesale Trade','44':'Retail',
                  '45':'Retail','48':'Transportation','49':'Transportation',
                  '51':'Information','52':'Finance','53':'Real Estate',
                  '54':'Professional Services','56':'Administrative services',
                  '61':'Educational Services','62':'Health Care',
                  '71':'Recreation','72':'Hospitality',
                  '81':'Other Services','92':'Public','00':'Unknown'}

@api.route('/get_one')
def getOne():
  return json.dumps(collection.find_one({},{'_id':0}))

@api.route('/get_one/pretty')
def getPrettyOne():
  incident = json.dumps(collection.find_one({},{'_id':0}),sort_keys=True, indent=2)
  incident = incident.replace(' ', '&nbsp;')
  incident = incident.replace('\n', '<br />')
  return incident

@api.route('/victims')
def victims():
  answer = {}
  answer['count'] = collection.count()
  answer['datetime'] = datetime.utcnow().isoformat()
  employee_count = collection.aggregate([{"$group":{"_id":"$victim.employee_count","count":{"$sum":1}}}])
  answer['employee_count'] = employee_count['result']
  country_count = collection.aggregate([{"$group":{"_id":"$victim.country","count":{"$sum":1}}},{"$sort": SON([("count", -1)])}])
  answer['country'] = country_count['result']
  industry = collection.aggregate([{'$project':{'pair':{'$substr':['$victim.industry',0,2]}}},{'$group':{'_id':'$pair','count':{'$sum':1}}},{"$sort": SON([("count", -1)])}])
  answer['industry'] = industry['result']
  for eachIndustry in answer['industry']:
    try:
      eachIndustry['friendly_name'] = industry_remap[eachIndustry['_id']]
    except:
      eachIndustry['friendly_name'] = 'Error'
  answer = json.dumps(answer)
  resp = Response(answer,status=200, mimetype='application/json')
  resp.headers['Access-Control-Allow-Origin'] = '*'
  return resp

if __name__ == '__main__':
  config = ConfigParser.RawConfigParser()
  config.read('database.cfg')
  client = pymongo.MongoClient(config.get('database','host'), config.getint('database','port'))
  db = client[config.get('database','db')]
  collection = db[config.get('database','coll')]
  
  api.run(debug=True,host=config.get('server','host'),port=config.getint('server','port'))
  


                              
