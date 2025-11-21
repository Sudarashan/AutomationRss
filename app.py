from flask import Flask, redirect, url_for, request, render_template, session
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime, timedelta
import tweepy
from agents import SocialMediaAgents  # Assuming this is your agents.py file
import feedparser
from helpers import post_to_linkedin, post_to_twitter, extract_image_url, extract_link_from_rss_entry
import random
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

ngrok_link = os.getenv("Ngrok_Link")

app = Flask(__name__)
app.secret_key = '12345678765'  # Replace with a secure key

scheduler = BackgroundScheduler()
scheduler.start()

api_key = os.getenv("Gemini_key")

agents = SocialMediaAgents(api_key)

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

posts = []
temp_posts = {}

@app.route('/')
def home():
    connected_platforms = {
        'linkedin': 'linkedin_access_token' in session and 'linkedin_id' in session,
        'twitter': 'twitter_access_token' in session and 'twitter_access_token_secret' in session
    }

    name ={
        'name':session.get('linkedin_name'),
        'tw_name':session.get('twitter_name')
    }


    return render_template('home.html', connected_platforms=connected_platforms,name=name)

@app.route('/connect_all')
def connect_all():
    session['connect_all'] = True
    return redirect(url_for('linkedin_auth'))

@app.route('/linkedin/auth')
def linkedin_auth():
    redirect_uri = f'{ngrok_link}/linkedin/callback'
    scope = 'openid profile w_member_social'
    auth_url = (
        f'https://www.linkedin.com/oauth/v2/authorization?'
        f'response_type=code&client_id={LINKEDIN_CLIENT_ID}&redirect_uri={redirect_uri}&'
        f'scope={scope}&state=randomstring'
    )

    return redirect(auth_url)

@app.route('/linkedin/callback')
def linkedin_callback():
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code provided"
    
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': f'{ngrok_link}/linkedin/callback',
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return "Error: Could not get LinkedIn access token"
    token_data = response.json()
    session['linkedin_access_token'] = token_data.get('access_token')
    profile_url = 'https://api.linkedin.com/v2/userinfo'
    headers = {'Authorization': f'Bearer {session["linkedin_access_token"]}'}
    profile_response = requests.get(profile_url, headers=headers)
    if profile_response.status_code != 200:
        return "Error: Could not fetch LinkedIn profile"
    user_info = profile_response.json()

    session['linkedin_name'] = user_info['name']
    session['linkedin_id'] = user_info.get('sub')
    
    if session.get('connect_all') and 'twitter_access_token' not in session:
        return redirect(url_for('twitter_auth'))
    return redirect(url_for('home'))

@app.route('/twitter/auth')
def twitter_auth():
    auth = tweepy.OAuth1UserHandler(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, f'{ngrok_link}/twitter/callback')
    try:
        redirect_url = auth.get_authorization_url()
        session['request_token'] = auth.request_token
        return redirect(redirect_url)
    except tweepy.TweepyException as e:
        return f"Error starting Twitter auth: {e}"

@app.route('/twitter/callback')
def twitter_callback():
    request_token = session.pop('request_token', None)
    if not request_token:
        return "Error: Request token not found in session. <a href='/twitter/auth'>Please try logging in again</a>."
    verifier = request.args.get('oauth_verifier')
    if not verifier:
        return "Error: No OAuth verifier provided"
    auth = tweepy.OAuth1UserHandler(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
    auth.request_token = request_token
    try:
        auth.get_access_token(verifier)
        session['twitter_access_token'] = auth.access_token
        session['twitter_access_token_secret'] = auth.access_token_secret
        auth.set_access_token(auth.access_token, auth.access_token_secret)
        api = tweepy.API(auth)

        
        user = api.verify_credentials()
        if user:
            session['twitter_name'] = user.name  
            # session['twitter_username'] = user.screen_name


        session.pop('connect_all', None)
        return redirect(url_for('home'))
    except tweepy.TweepyException as e:
        return f"Twitter authorization failed: {e}"

@app.route('/disconnect/<platform>')
def disconnect(platform):
    if platform == 'linkedin':
        session.pop('linkedin_access_token', None)
        session.pop('linkedin_id', None)
    elif platform == 'twitter':
        session.pop('twitter_access_token', None)
        session.pop('twitter_access_token_secret', None)
    return redirect(url_for('home'))

@app.route('/post', methods=['GET', 'POST'])
def create_post():
    if not (session.get('linkedin_access_token') or session.get('twitter_access_token')):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        rss_urls = request.form.getlist('rss_urls')
        posts_per_day = int(request.form['posts_per_day'])
        frequency = request.form['frequency']
        schedule_type = request.form['schedule_type']
        first_post_time = datetime.strptime(request.form['first_post_time'], '%Y-%m-%dT%H:%M')

        if schedule_type == 'daily':
            total_posts = posts_per_day
        elif schedule_type == 'weekly':
            total_posts = posts_per_day * 7
        else:  # monthly
            total_posts = posts_per_day * 30

        all_entries = []
        for rss_url in rss_urls:
            response = requests.get(rss_url, verify=True)
            feed = feedparser.parse(response.content)
            all_entries.extend(feed.entries)
        selected_entries = random.sample(all_entries, min(total_posts, len(all_entries)))

        # selected_entries = sorted(
        #         all_entries,
        #         key=lambda entry: entry.published_parsed,
        #         reverse=False
        #     )[:total_posts]

        
        # selected_entries = sorted(
        #         all_entries,
        #         key=lambda entry: entry.published_parsed,
        #         reverse=False
        #     )[-3:]


        generated_posts = {'linkedin': [], 'twitter': []}
        if session.get('linkedin_access_token'):
            for entry in selected_entries:
                title = entry.title
                description = entry.get('description', entry.get('summary', ''))
                # image_url = None
                image_url = extract_image_url(entry)
                link = extract_link_from_rss_entry(entry)
                if not link:
                    link = "https://youtube.com/playlist?list=PLacDrP-7Ys6IsnPRN0ToTfjH8gQ4s6mL9&si=shb65ODGWXhcG1wq"

                transformed = agents.linkedin_transform(title, description)
                
                text = f"{transformed['new_title']} {transformed['new_description']}"
                generated_posts['linkedin'].append({
                    'text': text,
                    'image_url': image_url,
                    'link': link,
                    'platform': 'linkedin',
                    'access_token': session['linkedin_access_token'],
                    'linkedin_id': session['linkedin_id'],
                    'status': 'pending'
                })
        if session.get('twitter_access_token'):
            for entry in selected_entries:
                title = entry.title
                description = entry.get('description', entry.get('summary', ''))
                image_url = None
                link = extract_link_from_rss_entry(entry)
                if not link:
                    link = "https://youtube.com/playlist?list=PLacDrP-7Ys6IsnPRN0ToTfjH8gQ4s6mL9&si=shb65ODGWXhcG1wq"
       
                transformed = agents.twitter_transform(title, description,link)
                text = f"{transformed['new_title']} {transformed['new_description']}"
                
                
                generated_posts['twitter'].append({
                    'text': text,
                    'image_url': image_url,
                    'platform': 'twitter',
                    'access_token': session['twitter_access_token'],
                    'access_token_secret': session['twitter_access_token_secret'],
                    'status': 'pending'
                })
        
        post_id = str(uuid.uuid4())
        temp_posts[post_id] = {
            'posts': generated_posts,
            'first_post_time': first_post_time,
            'frequency': int(frequency)
        }
        return redirect(url_for('review_posts', post_id=post_id))
    
    return render_template('post.html')

@app.route('/review/<post_id>', methods=['GET', 'POST'])
def review_posts(post_id):
    if post_id not in temp_posts:
        return redirect(url_for('create_post'))
    
    now = datetime.now()

    current_time = now.strftime("%H:%M:%S")
   
    post_data = temp_posts[post_id]
    all_posts = []
    for platform_posts in post_data['posts'].values():
        all_posts.extend(platform_posts)
    
    if request.method == 'POST':
        first_post_time = post_data['first_post_time']
        frequency = post_data['frequency']
        
        # Schedule posts separately for each platform
        for platform, platform_posts in post_data['posts'].items():
            for i, post in enumerate(platform_posts):
                scheduled_time = first_post_time + timedelta(minutes=frequency * i)
                post['scheduled_time'] = scheduled_time
                posts.append(post)
                if platform == 'linkedin':
                    job = scheduler.add_job(post_to_linkedin, 'date', run_date=scheduled_time, args=[post])
                    post["job_id"] = job.id
                elif platform == 'twitter':
                    job = scheduler.add_job(post_to_twitter, 'date', run_date=scheduled_time, args=[post])
                    post["job_id"] = job.id
                    now = datetime.now()
                    current_time = now.strftime("%H:%M:%S")
                    print("end Time =", current_time)
        del temp_posts[post_id]
        return redirect(url_for('scheduled_posts'))
    
    return render_template('review.html', 
                         posts=all_posts,
                         first_post_time=post_data['first_post_time'].isoformat(),
                         frequency=post_data['frequency'])

@app.route('/scheduled')
def scheduled_posts():
    linkedin_posts = [p for p in posts if p['platform'] == 'linkedin' and p['status'] == 'pending']
    twitter_posts = [p for p in posts if p['platform'] == 'twitter' and p['status'] == 'pending']
    return render_template('scheduled.html', linkedin_posts=linkedin_posts, twitter_posts=twitter_posts)


@app.route('/delete_all_posts', methods=['POST'])
def delete_all_posts():
    global posts                   # Clear all saved tokens/accounts
    posts.clear()
    scheduler.remove_all_jobs()        # Stop all scheduled jobs
    return redirect(url_for('scheduled_posts'))


@app.route('/delete_post/<int:post_index>', methods=['POST'])
def delete_post(post_index):
    global posts
    
    if 0 <= post_index < len(posts):
        # Remove job from scheduler also
        job_id = posts[post_index].get("job_id")
        if job_id:
            try:
                scheduler.remove_job(job_id)
            except:
                pass
        
        posts.pop(post_index)

    return redirect(url_for('scheduled_posts'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT"))
    app.run(debug=True, host='0.0.0.0', port=port)
