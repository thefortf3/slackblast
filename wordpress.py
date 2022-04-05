from decouple import config, UndefinedValueError
import requests
import json
import base64
from datetime import datetime

app_pass = config("WORDPRESS_APP_PASSWORD")
app_user = config("WORDPRESS_USER")
base_url= config("WORDPRESS_BASE_URL")
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
        return response_json[0]['id']
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
    raise Exception("Unable to create " + type + "error was: \n" + json.dumps(response_json, indent=2))
    
# Normalize the string we search for (AO specific naming convention here)
def normalize(dirty_data):
    dirty_data = dirty_data.replace("ao-", '')
    dirty_data = dirty_data.replace("-", ' ')
    return dirty_data

# Post the data to wordpress.  
#  date: str in 'MM/DD/YYYY' format
#  pax/fngs: comma separated list of names
def postToWordpress(title, date, qic, ao, pax, fngs, backblast):
    ao = normalize(ao)
    ao_id = getIdBySearch("categories", ao)
    if ao_id is None:
        ao_id = getIdFromCreate('categories', ao)
    if fngs.strip() != "None":
        pax = pax + ", " + fngs
    paxlist = str.split(pax, ",")

    tags = []
    for thepax in paxlist: 
        tag_id = getIdBySearch("tags", thepax.strip())
        if  tag_id is not None:
            tags.append(tag_id)
        else:
            tags.append(getIdFromCreate("tags", thepax.strip()))
            
    qic_id = getIdBySearch("tags", qic.strip())
    if  qic_id is not None:
        tags.append(qic_id)
    else:
        tags.append(getIdFromCreate("tags", qic.strip()))

    post = {
        'title'    : title,
        'status'   : 'draft', 
        'content'  : backblast,
        'categories': ao_id, 
        'date'   : datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
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

