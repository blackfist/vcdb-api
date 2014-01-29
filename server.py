import ConfigParser
import pymongo
from flask import Flask, render_template, request, redirect, url_for
import json

api = Flask(__name__)

@api.route('/get_one')
def getOne():
  return json.dumps(collection.find_one({},{'_id':0}))

@api.route('/get_one/pretty')
def getPrettyOne():
  incident = json.dumps(collection.find_one({},{'_id':0}),sort_keys=True, indent=2)
  incident = incident.replace(' ', '&nbsp;')
  incident = incident.replace('\n', '<br />')
  return incident

if __name__ == '__main__':
  config = ConfigParser.RawConfigParser()
  config.read('database.cfg')
  client = pymongo.MongoClient(config.get('database','host'), config.getint('database','port'))
  db = client[config.get('database','db')]
  collection = db[config.get('database','coll')]
  
  api.run(debug=True,host=config.get('server','host'),port=config.getint('server','port'))
  


                              
