# vcdb-api
an API to return JSON data from the VCDB. This API will make it easier to query live data for use in visualizations.

# Setup
You'll need a mongo server that you can access. Once the server is setup, put all of the VCDB incidents into a collection
on the server. The VCDB repo has a utility called into-mongo.py which can automate this for you.  

Next edit the file sample-database.cfg and rename the file to database.cfg. This is the configuration that the api
will read to set up the application.  

Finally, invoke the server by typing

    python server.py

# Methods
## Returning a single incident
Used primarily for testing database connectivity. This will return a single document from the database. Use the /pretty option to have
the output formatted nicer.


    GET /api/get_one
    GET /api/get_one/pretty

## Getting victim demographics
You can query for all aggregate victim demographics, and you can filter down to get aggregate statistics for a particular country.
Country code should be the two-character ISO country code. Results for employee count, industry, and country are sorted descending. So 
if you want the top ten affected countries, you can grab the victims and take the first ten results in the country array.

    GET /api/victims
    GET /api/victims/country/<country_code>
    GET /api/victims/naics/<naics_code>
    GET /api/victims/industry/<naics_code>
    
The API returns the same data if you request /victim/naics or /victim/industry. The alias is provides solely for conveniene.

## What year has the most incidents
You can query the year for incidents with one request. This will return the list of incident years and the count of incidents in each year
sorted by count of incidents (years\_by\_count). The response also includes the list of years sorted by year (descending)(years\_by\_year). 
Finally, the answer includes the list of years sorted by year (descending) and including any missing years with a zero count (years\_by\_year\_fill\_zero).

    GET /api/incident_year
    
## Biggest incidents by data loss
You can get a list of the largest data breaches in the data set which includes the year, victim name, data total, and actions in the incident.
The default returns the top ten largest incidents, or you can specify the top n incidents. There is also a specific query to get the largest
payment card breaches.

    GET /api/data_total
    GET /api/data_total/top/<integer>
    GET /api/data_total/payment/top/<integer>

# Testing
I need to write tests for many of these things but I'm not going to do it right now. I know, that's not very TDD of me. Anyway,
I want to keep track of some of the things I should be testing

+ test that you get valid results when you give valid input
+ how does it handle mixed case input
+ how does it react when you give it a string and it expected an integer
+ how does it react when you give an integer and it expected a string
+ how does it react when you give valid input that has no results