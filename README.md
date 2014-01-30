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
    GET /api/victims/naics/<naics_code>
    GET /api/victims/industry/<naics_code>
    
The API returns the same data if you request /victim/naics or /victim/industry. The alias is provides solely for conveniene.

# Testing
I need to write tests for many of these things but I'm not going to do it right now. I know, that's not very TDD of me. Anyway,
I want to keep track of some of the things I should be testing

+ test that you get valid results when you give valid input
+ how does it handle mixed case input
+ how does it react when you give it a string and it expected an integer
+ how does it react when you give an integer and it expected a string
+ how does it react when you give valid input that has no results