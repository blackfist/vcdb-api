# vcdb-api
an API to return JSON data from the VCDB.

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