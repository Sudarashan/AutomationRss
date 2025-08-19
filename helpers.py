import re
from io import BytesIO
import requests
import tweepy

import os
from dotenv import load_dotenv
load_dotenv()

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")

# def extract_image_url(entry):
#     """Extract an image URL from an RSS feed entry."""
#     for enclosure in entry.get('enclosures', []):
#         if enclosure.get('type', '').startswith('image/'):
#             return enclosure.get('url')
#     for media in entry.get('media_content', []):
#         if media.get('type', '').startswith('image/'):
#             return media.get('url')
#     for thumbnail in entry.get('media_thumbnail', []):
#         if thumbnail.get('url'):
#             return thumbnail.get('url')
#     if 'image' in entry:
#         image = entry['image']
#         if isinstance(image, dict) and 'url' in image:
#             return image['url']
#         elif isinstance(image, list):
#             for img in image:
#                 if 'url' in img:
#                     return img['url']
#     if 'itunes_image' in entry:
#         return entry['itunes_image'].get('href')
#     for field in ['description', 'summary', 'content']:
#         if field in entry:
#             content = entry[field]
#             if isinstance(content, list):
#                 content = content[0].get('value', '')
#             elif isinstance(content, dict):
#                 content = content.get('value', '')
#             else:
#                 content = str(content)
#             match = re.search(r'<img[^>]+src=["\'](.*?)["\']', content, re.I)
#             if match:
#                 return match.group(1)
#     return None

def post_to_linkedin(post):
    """Post content to LinkedIn with optional image."""
    if post['status'] not in ['pending', 'posting']:
        return
    access_token = post['access_token']


    print("linkedin_access_token",access_token)
    linkedin_id = post['linkedin_id']
    image_url = post.get('image_url')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    if image_url:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            image_content = response.content
            register_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
            register_body = {
                'registerUploadRequest': {
                    'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                    'owner': f'urn:li:person:{linkedin_id}',
                    'serviceRelationships': [
                        {'relationshipType': 'OWNER', 'identifier': 'urn:li:userGeneratedContent'}
                    ]
                }
            }
            register_response = requests.post(register_url, headers=headers, json=register_body)
            if register_response.status_code == 200:
                upload_data = register_response.json()['value']
                upload_url = upload_data['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                asset = upload_data['asset']
                print("uploaaaaaaaaadddddddddddd",asset)
                upload_headers = {'Authorization': f'Bearer {access_token}'}
                upload_response = requests.put(upload_url, headers=upload_headers, data=image_content)
                if upload_response.status_code == 201:
                    api_url = 'https://api.linkedin.com/v2/ugcPosts'
                    post_body = {
'author': f'urn:li:person:{linkedin_id}',
'lifecycleState': 'PUBLISHED',
'specificContent': {
'com.linkedin.ugc.ShareContent': {
'shareCommentary': {
'text': f"{post['text']}"
},
'shareMediaCategory': 'ARTICLE',
'media': [
{
'status': 'READY',
'description': {
'text': 'EYE ON AI'
},
'originalUrl': 'https://youtube.com/playlist?list=PLacDrP-7Ys6IsnPRN0ToTfjH8gQ4s6mL9',
'title': {
'text': 'EYE ON AI'
}
}
]
}
},
'visibility': {
'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
}
}
                    response = requests.post(api_url, headers=headers, json=post_body)
                    post['status'] = 'posted' if response.status_code == 201 else 'failed'
                    print(f"LinkedIn post attempt: {response.status_code} - {response.text}")
                else:
                    print(f"Image upload failed: {upload_response.status_code}")
            else:
                print(f"Upload registration failed: {register_response.status_code}")
        else:
            print(f"Image download failed: {response.status_code}")
        if post['status'] != 'posted':
            api_url = 'https://api.linkedin.com/v2/ugcPosts'
            post_body = {
                'author': f'urn:li:person:{linkedin_id}',
                'lifecycleState': 'PUBLISHED',
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {'text': post['text']},
                        'shareMediaCategory': 'NONE'
                    }
                },
                'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
            }
            response = requests.post(api_url, headers=headers, json=post_body)
            post['status'] = 'posted' if response.status_code == 201 else 'failed'
            print(f"LinkedIn text-only post: {response.status_code} - {response.text}")
    else:
        api_url = 'https://api.linkedin.com/v2/ugcPosts'
        post_body = {
            'author': f'urn:li:person:{linkedin_id}',
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {'text': post['text']},
                    'shareMediaCategory': 'NONE'
                }
            },
            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'}
        }
        response = requests.post(api_url, headers=headers, json=post_body)
        post['status'] = 'posted' if response.status_code == 201 else 'failed'
        print(f"LinkedIn post attempt: {response.status_code} - {response.text}")

def post_to_twitter(post):
    """Post content to Twitter with optional image."""
    if post['status'] not in ['pending', 'posting']:
        return
    client = tweepy.Client(
        consumer_key=TWITTER_CLIENT_ID,
        consumer_secret=TWITTER_CLIENT_SECRET,
        access_token=post['access_token'],
        access_token_secret=post['access_token_secret']
    )
    print("access_token_secret",client.access_token_secret)
    image_url = post.get('image_url')
    if image_url:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            image_content = BytesIO(response.content)
            try:
                api = tweepy.API(tweepy.OAuth1UserHandler(
                    TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET,
                    post['access_token'], post['access_token_secret']
                ))
                media = api.media_upload(filename='image', file=image_content)
                client.create_tweet(text=post['text'], media_ids=[media.media_id])
                post['status'] = 'posted'
                print("Twitter post with image successful")
            except tweepy.TweepyException as e:
                print(f"Twitter image post error: {e}")
                try:
                    client.create_tweet(text=post['text'])
                    post['status'] = 'posted'
                    print("Twitter text-only post successful")
                except tweepy.TweepyException as e:
                    post['status'] = 'failed'
                    print(f"Twitter text-only error: {e}")
            except Exception as e:
                print(f"Media upload error: {e}")
        else:
            print(f"Image download failed: {response.status_code}")
            try:
                client.create_tweet(text=post['text'])
                post['status'] = 'posted'
                print("Twitter text-only post successful")
            except tweepy.TweepyException as e:
                post['status'] = 'failed'
                print(f"Twitter text-only error: {e}")
    else:
        try:
            client.create_tweet(text=post['text'])
            post['status'] = 'posted'
            print("Twitter post successful")
        except tweepy.TweepyException as e:
            post['status'] = 'failed'
            print(f"Twitter error: {e}")