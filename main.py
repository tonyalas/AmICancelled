# my attempt at using the twauth-web source code and manipulating it for my app's use

import os
from requests_oauthlib import OAuth1Session
from flask import Flask, render_template, request, url_for
import oauth2 as oauth
import twitter
import requests
import urllib.request
import urllib.parse
import urllib.error
import json

app = Flask(__name__)

app.debug = False

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
search_url = 'https://api.twitter.com/1.1/tweets/search/30day/search30.json'

# Add your API key here
consumer_key = 'Wt27ZdXJqECb2JMpUCQ5uhWnD'
# Add your API secret key here
consumer_secret = 'LkuUnE65DuGG5oyzbXKd7M3YEGXNLpyLVwWE33KuRvyGE6F2wV'

oauth_store = {}
user_store = {}     # a global dict used to store the authorization variables for the delete_tweet function

# this will be used for the delete tweets function
tweets_global = []
tweets_username_global = []
tweets_ids_global = []

@app.route('/')
def home():
    # note that the external callback URL must be added to the whitelist on
    # the developer.twitter.com portal, inside the app settings
    app_callback_url = url_for('callback', _external=True)

    # Generate the OAuth request tokens, then display them
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer)
    resp, content = client.request(request_token_url, "POST", body=urllib.parse.urlencode({
                                   "oauth_callback": app_callback_url}))

    if resp['status'] != '200':
        error_message = 'Invalid response, status {status}, {message}'.format(
            status=resp['status'], message=content.decode('utf-8'))
        return render_template('cancelMe_Error.html', error_message=error_message)

    request_token = dict(urllib.parse.parse_qsl(content))
    oauth_token = request_token[b'oauth_token'].decode('utf-8')
    oauth_token_secret = request_token[b'oauth_token_secret'].decode('utf-8')
    print("Got OAuth token: {}".format(oauth_token))
    oauth_store[oauth_token] = oauth_token_secret

    # this is to ensure that the lists from the previous user are cleared
    if(len(tweets_global) != 0):
        del tweets_global[:]
    if(len(tweets_ids_global) != 0):
        del tweets_ids_global[:]
    if(len(tweets_username_global) != 0):
        del tweets_username_global[:]

    return render_template('cancelMe.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url)


@app.route('/callback')
def callback():
    # Accept the callback params, get the token and call the API to
    # display the logged-in user's name and handle
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    print("oauth verifier is: {}".format(oauth_verifier))

    # if the OAuth request was denied, delete our local token
    # and show an error message
    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        print("the OAuth request was denied by this user")
        return render_template('cancelMe_Error.html', error_message="the OAuth request was denied by this user")

    if not oauth_token or not oauth_verifier:
        print("callback param(s) missing")
        return render_template('cancelMe_Error.html', error_message="callback param(s) missing")

    # unless oauth_token is still stored locally, return error
    if oauth_token not in oauth_store:
        print("oauth_token not found locally")
        return render_template('cancelMe_Error.html', error_message="oauth_token not found locally")

    oauth_token_secret = oauth_store[oauth_token]

    # if we got this far, we have both callback params and we have
    # found this token locally

    # store the user's access key and secret in the global dict
    # this should replace the keys everytime a new user logs in 
    user_store['access_token'] = oauth_token
    user_store['access_token_secret'] = oauth_token_secret

    consumer = oauth.Consumer(consumer_key, consumer_secret)
    token = oauth.Token(oauth_token, oauth_token_secret)
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urllib.parse.parse_qsl(content))

    screen_name = access_token[b'screen_name'].decode('utf-8')
    user_id = access_token[b'user_id'].decode('utf-8')

    print("screen name is: ")
    print(screen_name)
    print("user_id is:")
    print(user_id)

    tweets = []  # a list that stores the tweet's text
    tweets_usernames = []  # a list that stores the tweet's author
    tweets_ids = []  # a list that stores the tweet's id

    # These are the tokens you would store long term, someplace safe
    real_oauth_token = access_token[b'oauth_token'].decode('utf-8')
    real_oauth_token_secret = access_token[b'oauth_token_secret'].decode(
        'utf-8')

    # fill the global lists with filler items in the first spots so that it can be used easily when deleting tweets
    # this is because the index received from the html file start counting at 1 instead of 0
    tweets_global.append("filler")
    tweets_ids_global.append("filler")
    tweets_username_global.append("filler")

    # Call api.twitter.com/1.1/users/show.json?user_id={user_id}
    headers = {"Authorization":"Bearer AAAAAAAAAAAAAAAAAAAAALyrDAEAAAAAmy%2F1oHMkGuirodRGpXt1SorL3mU%3DGN4H2cLxc2jQad2s7yCxNpiOxVRmfwQQ1nnVDmJrgUnkph0prS", "Content-Type": "application/json"} 
    data = '{"query": "(gay OR fuck OR nig OR year OR feel OR bad OR nigga OR niggas OR retard OR slut OR whore OR skank OR bitch OR shit OR shitty OR fucking OR fucker OR motherfucker OR cunt OR faggot OR fag OR queer OR homo OR homos OR stupid OR kill OR suicide OR die) from:' + screen_name + '"}' # WORKING QUERY (TESTING MULTIPLE TERMS IN ONE REQUEST)

    real_token = oauth.Token(real_oauth_token, real_oauth_token_secret)
    real_client = oauth.Client(consumer, real_token)

    response = requests.post(search_url, data=data, headers=headers)
    if response.encoding is None:
        response.encoding = "utf-8"
    for data in response.iter_lines(decode_unicode=True):
        if data:
            jdata = json.loads(data)
    # check to make sure results isn't empty. if it is, send to an error page
    try:
        results = jdata["results"]
    # catch the potential KeyError and send user to an error page
    except KeyError as e:
        print("Key error raised. Given reason: %s" % str(e))
        return render_template('cancelMe_Error.html', error_message="key error thrown")
    #print(results)
    #print("just printed the results array!")
    for item in results:
        print("------------------")
        print("tweet found")
        tweet_username = item['user']['screen_name']
        print(tweet_username)
        tweet_text = item['text']
        print(tweet_text)
        tweet_id = item['id_str']
        print(tweet_id)
        print("------------------")
        # add the above items to their corresponding lists
        tweets.append(tweet_text) # add username to the corresponding list
        tweets_ids.append(tweet_id) # add the tweet id to the corresponding list
        tweets_usernames.append(tweet_username) # add the tweet's author (username) to the corresponding list
        # add the same values to the global lists for the delete function at the end of the file
        tweets_global.append(tweet_text)
        tweets_ids_global.append(tweet_id)
        tweets_username_global.append(tweet_username)

    # this will check to see if they have any tweets that match the criteria. Output will change depending on this
    if(len(tweets) == 0):
        naughtyBool = False
        naughtyCount = 0
    else: 
        naughtyBool = True
        naughtyCount = len(tweets)

    # don't keep this token and secret in memory any longer
    del oauth_store[oauth_token]

    return render_template('cancelMe_Callback.html', zipped=zip(tweets, tweets_ids, tweets_usernames), naughty=naughtyBool, naughtyCount=naughtyCount, screen_name=screen_name)


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('cancelMe_Error.html', error_message='uncaught exception'), 500

@app.route('/delete_tweet', methods=["POST"])
def delete_tweet():
    # retrieve the index number of which delete button was clicked by the user
    if request.method == 'POST':
        print("post method found")
        tweet_number = int(request.form['index'])
        print(tweet_number)

    print("clicked!")

    # get the user's access tokens (and secret token) from the global dict that has it stored
    access_token = user_store['access_token']
    access_token_secret = user_store['access_token_secret']

    # create an instance of the twitter-python API 
    api = twitter.Api(consumer_key=consumer_key, consumer_secret=consumer_secret, access_token_key=access_token, access_token_secret=access_token_secret) # python-twitter

    # for debugging purposes, output the tweet that was deleted
    print(tweets_ids_global[tweet_number])
    deleteTweetID = tweets_ids_global[tweet_number]
    print(tweets_global[tweet_number])
    # try to delete the tweet
    try:
        api.DestroyStatus(deleteTweetID) 
    # if user tries to delete tweet twice, catch the error and send them to the error page
    except twitter.error.TwitterError as e:
        print("Twitter error raised. Given reason: %s" % str(e))
        return render_template('cancelMe_Error.html', error_message="Already Deleted Tweet")

    return ('', 204) # do not refresh the page when the user clicks on the trash button
  
if __name__ == '__main__':
    app.run(debug=True)