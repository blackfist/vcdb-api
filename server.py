import ConfigParser
import pymongo

if __name__ == '__main__':
  config = ConfigParser.RawConfigParser()
  config.read('database.cfg')
  client = pymongo.MongoClient(config.get('database','host'), config.getint('database','port'))
  db = client[config.get('database','db')]
  collection = db[config.get('database','coll')]
  
  print collection.find_one()

                              
