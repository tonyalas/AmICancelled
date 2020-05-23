from requests_oauthlib import OAuth1Session
import os
import json
from flask import Flask, render_template, request, url_for, jsonify
import requests

app = Flask(__name__)

# the necessary URL's to authenticate the user logging in
request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'

# Add your API key here
consumer_key = 'Wt27ZdXJqECb2JMpUCQ5uhWnD'
# Add your API secret key here
consumer_secret = 'LkuUnE65DuGG5oyzbXKd7M3YEGXNLpyLVwWE33KuRvyGE6F2wV'

oauth_store = {}    # a global dict used to access variables in different app.route's

@app.route("/")
def home():
    app_callback_url = url_for('callback', _external=True)
    # STEP 1: obtain a request token
    # create an OAuth1 session for signing and posting
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)
    # fetch_request_token is the same as using a signed POST. TYPE: Dict
    fetch_response = oauth.fetch_request_token(request_token_url)
    # get the value for the key in the dict, key = "oauth_token"
    resource_owner_key = fetch_response.get("oauth_token")
    # get the value for the key in the dict, key = "oauth_token_secret"
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    # print the oauth_token to the output
    print("Page initially loaded. Got OAuth token: {}".format(resource_owner_key))
    # store the resource_owner_key and resource_owner_secret into the global dict
    oauth_store[resource_owner_key] = resource_owner_secret

    # STEP 2: Get authorization
    # returns the authorization URL with new parameters embedded
    authorization_url = oauth.authorization_url(authorize_url)

    # return the template with the necessary variables so that the user can click on the Twitter log-in button and go to the authentication page
    return render_template('cancelMe.html', authorize_url=authorize_url, oauth_token=resource_owner_key, request_token_url=request_token_url)


@app.route("/callback")
def callback():
    # Accept the callback params, get the token and call the API to
    # display the logged-in user's name and handle
    oauth_token = request.args.get('oauth_token')
    verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    print("oauth verifier is: {}".format(verifier))

    # if the OAuth request was denied, delete our local token
    # and show an error message
    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        print("the OAuth request was denied by this user")
        return render_template('cancelMe_Error.html', error_message="the OAuth request was denied by this user")

    if not oauth_token or not verifier:
        print("callback param(s) missing")
        return render_template('cancelMe_Error.html', error_message="callback param(s) missing")

    # unless oauth_token is still stored locally, return error
    if oauth_token not in oauth_store:
        print("oauth_token not found locally")
        return render_template('cancelMe_Error.html', error_message="Cannot refresh page after logging in.")

    resource_owner_secret = oauth_store[oauth_token]

    # STEP 3: Get the access token
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)
    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # ------------------- Percent Encoding ----------------
    # space = %20
    # " (Quote) = %22
    # + (plus) = %2B
    # = (equal) = %3D
    # @ (ampersand/at) = %40
    # ? (question mark) = %3F
    # -----------------------------------------------------

    # this is necessary to grab the screen name of the person who logged in 
    accountInfo = oauth.get("https://api.twitter.com/1.1/account/verify_credentials.json")
    if accountInfo.encoding is None:
        accountInfo.encoding = "utf-8"
    for data in accountInfo.iter_lines(decode_unicode=True):
        if data:
            jdata = json.loads(data)
    print("retrieved screen name is")
    print(jdata["screen_name"])
    print("---------------")
    # store the screen name from the verified credentials so that the search query uses the appropriate username when searching
    screen_name = jdata["screen_name"]
    print(screen_name)
    print("---------------")

    tweets = []  # a list that stores the tweet's text
    tweets_usernames = []  # a list that stores the tweet's author
    tweets_ids = []  # a list that stores the tweet's id

    # this is the list that is a subset of the words below (inside of data) that are the worst of the worst
    highlyOffensiveWords = ["gay", "faggot", "fag", "queer", "tranny", "dyke", "nigger", "nigga", "chink", "slut", "whore", "feminazi", "retard", "retarded", "tard", "suicide"]

    # from "Integrating premium search twitter developer page"
    endpoint = "https://api.twitter.com/1.1/tweets/search/fullarchive/searchFull.json"
    headers = {"Authorization":"Bearer AAAAAAAAAAAAAAAAAAAAALyrDAEAAAAAmy%2F1oHMkGuirodRGpXt1SorL3mU%3DGN4H2cLxc2jQad2s7yCxNpiOxVRmfwQQ1nnVDmJrgUnkph0prS", "Content-Type": "application/json"} 

    # list of words in order goes: 
    # lgbtq+ slurs
    # racist slurs
    # slut shaming + misogynistic/sexist words
    # disability + mental illness slurs
    # general swear words

    # the query to search for
    data = '{"query": "(gay OR faggot OR fag OR queer OR homo OR homos OR tranny OR fudgepacker OR sissy OR flamer OR twink OR dyke OR lesbo OR heshe OR shemale OR nig OR nigga OR niggas OR nigger OR nazi OR gook OR chink OR beaner OR coon OR darkie OR goy OR guido OR gypsy OR hick OR kike OR kyke OR niglet OR negro OR nigguh OR niggah OR paki OR polack OR raghead OR towelhead OR spook OR spic OR whitey OR zipperhead OR slut OR whore OR skank OR bitch OR feminazi OR cougar OR prude OR hoe OR butch OR bimbo OR hooker OR wanker OR retard OR cripple OR midget OR retarded OR psycho OR schizo OR spaz OR spastic OR tard OR downy OR kill OR suicide OR kys OR shit OR shitty OR fucking OR motherfucker OR cunt OR bastard OR asshole OR goddamn OR prick OR twat) from:' + screen_name + '", "maxResults": "301", "fromDate": "200603220000"}' # WORKING QUERY (TESTING MULTIPLE TERMS IN ONE REQUEST)

    # ALT LIST OF WORDS (for when i go to the free version): gay OR faggot OR homo OR nigga OR nigger OR chink OR beaner OR gypsy OR paki OR towelhead OR slut OR whore OR retard OR retarded
    # the words above are exactly 128 characters long

    nextTokenBool = False

    # call the search API using the endpoint, data and headers parameters
    response = requests.post(endpoint, data=data, headers=headers)
    if response.encoding is None:
        response.encoding = "utf-8"
    for data in response.iter_lines(decode_unicode=True):
        if data:
            jdata = json.loads(data)
            #print(jdata)
    # check to make sure results isn't empty. if it is, send to an error page
    try:
        results = jdata["results"]
        # check to see if there is a next token
        if 'next' in jdata:
            nextToken = jdata["next"]
            print("next token found")
            print(nextToken)
            nextTokenBool = True

    # catch the potential KeyError and send user to an error page
    except KeyError as e:
        print("Key Error raised. Given reason: %s" % str(e))
        return render_template('cancelMe_Error.html', error_message="Max Number of Requests to the Twitter Server reached.")
        #return render_template('cancelMe_Error.html', error_message="Key Error Thrown/Hit Max Number of Requests")
    highlyOffensiveWordCount = 0
    #print(results)
    #print("just printed the results array!")
    for item in results:
        #print("------------------")
        #print("tweet found")
        tweet_username = item['user']['screen_name']
        #print(tweet_username)
        tweet_text = item['text']
        #for badWord in highlyOffensiveWords:
         #   if badWord in tweet_text:
          #      highlyOffensiveWordCount += 1
        #print(tweet_text)
        tweet_id = item['id_str']
        #print(tweet_id)
        #print("------------------")
        # add the above items to their corresponding lists
        tweets.append(tweet_text) # add username to the corresponding list
        tweets_ids.append(tweet_id) # add the tweet id to the corresponding list
        tweets_usernames.append(tweet_username) # add the tweet's author (username) to the corresponding list
        if(len(tweets) == 300):
            break;


    # this will check to see if they have any tweets that match the criteria. Output will change depending on this
    if(len(tweets) == 0):
        naughtyBool = False
        naughtyCount = 0
        print("no tweets found.")
    else: 
        naughtyBool = True
        naughtyCount = len(tweets)
        print(naughtyCount, " tweets found")
        #print(highlyOffensiveWordCount, " highly offensive words found.")

    # don't keep this token and secret in memory any longer. FIXES THE PROBLEM WHEN REFRESHING PAGE
    del oauth_store[oauth_token]

    return render_template('cancelMe_Callback.html', zipped=zip(tweets, tweets_ids, tweets_usernames), naughty=naughtyBool, naughtyCount=naughtyCount, screen_name=screen_name, nextTokenBool=nextTokenBool)


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('cancelMe_Error.html', error_message='uncaught exception'), 500

if __name__ == "__main__":
    app.run(threaded=True)