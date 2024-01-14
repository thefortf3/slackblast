from decouple import config, UndefinedValueError
import requests
import json
import base64
import pytz
from utilities import constants
import os
from datetime import datetime
OPTIONAL_INPUT_VALUE = "None"

app_pass = os.environ.get(constants.WORDPRESS_APP_PASSWORD, "123")
app_user = os.environ.get(constants.WORDPRESS_USER, "123")
base_url= os.environ.get(constants.WORDPRESS_BASE_URL, "123")
creds = app_user + ":" + app_pass
token = base64.b64encode(creds.encode())

# Need to pretend to be a browser because some caching in front of the server rejects
# calls without it.
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Authorization': 'Basic ' + token.decode('utf-8'),
            'Content-type': 'application/json'}

# We search for tag/category ID via the API to match up with the existing as best we can
def getIdBySearch(type, query):
    url = base_url + type + "?search="
    response = requests.get(url + query, headers=headers)
    response_json = json.loads(response.content.decode('utf-8'))
    #print(json.dumps(response_json, indent=2))
    if len(response_json) > 0:
        for result in response_json:
            if result['name'].lower() == query.lower():
                return result['id']
    return None

# Creates a tag/category and returns the ID from it.
def getIdFromCreate(type, name):
    url = base_url + type
    data = {'name'  : name}
    response = requests.post(url, headers=headers, json=data)
    response_json = json.loads(response.content.decode('utf-8'))
    #print(json.dumps(response_json, indent=2))
    if 'id' in response_json:
        return response_json['id']
    raise Exception("Unable to create " + type + " error was: \n" + json.dumps(response_json, indent=2))
    
# Normalize the string we search for (AO specific naming convention here)
def normalize(dirty_data):
    dirty_data = dirty_data.replace("ao-", '')
    dirty_data = dirty_data.replace("-", ' ')
    return dirty_data

# Post the data to wordpress.  
#  date: str in 'MM/DD/YYYY' format
#  pax/fngs/qic: comma separated list of names
def postToWordpress(title, date, qic, ao, pax, fngs, backblast, preblast=False):
    if base_url == "123" or base_url is None:
        retval = {"error" : "Wordpress was not configured"}
        return retval
    ao = normalize(ao)
    ao_id = getIdBySearch("categories", ao)
    qlist = str.split(qic,",")
    tags = []

    if ao_id is None:
        ao_id = getIdFromCreate('categories', ao)
    if preblast:
        pb_id = getIdBySearch('categories', "Pre-Blast")
        if pb_id is None:
            raise Exception("Unable to find pre-blast category")
        new_ids = []
        new_ids.append(pb_id)
        new_ids.append(ao_id)
        ao_id = new_ids

    else:
        if fngs is not None and fngs.strip() != "None":
            pax = pax + ", " + fngs
        paxlist = str.split(pax, ",")
        
        for thepax in paxlist: 
            if thepax.strip() != "":
                tag_id = getIdBySearch("tags", thepax.strip())
                if  tag_id is not None:
                    tags.append(tag_id)
                else:
                    tags.append(getIdFromCreate("tags", thepax.strip()))

    for theq in qlist:
        qic_id = getIdBySearch("tags", theq.strip())
        if  qic_id is not None:
            tags.append(qic_id)
        else:
            tags.append(getIdFromCreate("tags", theq.strip()))

    post = {
        'title'    : title,
        'status'   : 'publish', 
        'content'  : backblast,
        'categories': ao_id, 
        'date'   : datetime.now(pytz.timezone('America/New_York')).strftime("%Y-%m-%d %H:%M:%S"), 
        'tags' : tags,
        'qic' : qic,
        'workout_date' : date
    }
    # print(str(ao_id))
    # print(str(tags))
    #response = requests.get(url + "&status=draft", headers=headers)
    url = base_url + "posts"
    response = requests.post(url, headers=headers, json=post)
    response_json = json.loads(response.content.decode('utf-8'))
    return response_json
    

