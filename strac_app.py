import os
import io
from flask import Flask, render_template, redirect, request, url_for, session, send_file
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
import tempfile
from datetime import datetime


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_key")
CORS(app, supports_credentials=True)



CLIENT_SECRETS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
# to run in http instead of https
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'



@app.route('/')
def index():
    #require sign-in every time landing page is reached
    session.pop('credentials', None)
    return render_template('landing.html')



'''
This route has the main view containing the files. This is My Drive folder by default.
'''
@app.route('/dashboard')
def dashboard():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    

    try:
        credentials = Credentials(**session['credentials'])

        service = build('drive', 'v3', credentials=credentials)

        folder_id = request.args.get('folder_id', 'root')
    
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, pageSize= 100, fields = "files(id, name, mimeType, modifiedTime)").execute()


    except HttpError as error:
        print(f"An error occurred in service build: {error}")

    files = results.get('files', [])

    for file in files:
        if 'modifiedTime' in file:
            file['modifiedTime'] = format_time(file['modifiedTime'])

    # gets folder heirarchy to display parents of a folder for navigation
    breadcrumbs = get_breadcrumb(service, folder_id)

    return render_template('index.html', files = files, current_folder=folder_id, breadcrumbs=breadcrumbs)




'''
parses the client secret and scope and redirects to google sign in 
'''
@app.route('/authorize')
def authorize():

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url, state = flow.authorization_url(
        access_type = 'offline',
        include_granted_scopes = 'true',
        prompt = 'select_account consent'
    )

    session['state'] = state

    return redirect(auth_url)


'''
converts credentials to a dict format
'''
def make_credentials_dict(credentials):

    return{
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }



'''
after the user authenticates, redirects here. Credentials are extracted and redirects to dashboard
'''
@app.route('/oauth2callback')
def oauth2callback():
    
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes = SCOPES,
            redirect_uri = REDIRECT_URI)

        flow.fetch_token(authorization_response=request.url)

    except HttpError as error:
        print(f"An error occurred in oauth2callback: {error}")

    session['credentials'] = make_credentials_dict(flow.credentials)

    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('index'))



'''
Uploads the user-selected file to the current folder that user has navigated to 
'''
@app.route('/upload', methods=['POST'])
def upload():

    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    file = request.files['file']
    folder_id = request.form.get('folder_id', 'root')


    # using tempfile to avoid dealing with system paths. works on all platforms easily
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file.save(temp_file.name)
        filepath = temp_file.name


    credentials = Credentials(**session['credentials'])

    service = build('drive', 'v3', credentials=credentials)

    media = MediaFileUpload(filepath, resumable=False)

    file_metadata = {
        "name": file.filename,
        "parents": [folder_id]
    }

    service.files().create(body=file_metadata, media_body=media).execute()

    temp_file.close()

    return redirect(url_for('dashboard', folder_id=folder_id))



'''
Initiates the file download in the browser
'''
@app.route('/download/<file_id>')
def download(file_id):
    try:
        credentials = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=credentials)

        file_metadata = service.files().get(fileId=file_id, fields="name").execute()
        file_name = file_metadata.get('name', f"{file_id}.downloaded")

        request_file = service.files().get_media(fileId = file_id)

        file = io.BytesIO()

        downloader = MediaIoBaseDownload(file, request_file)

        done = False

        while not done:
            dl_status, done = downloader.next_chunk()
            print(f"Download {int(dl_status.progress() * 100)}.")

    except HttpError as error:
        print(f"An error in download occurred: {error}")
        file = None
    
    file.seek(0)
    return send_file(file, as_attachment=True, download_name=file_name)


'''
deletes the selected file
'''
@app.route('/delete/<file_id>', methods=['POST'])
def delete(file_id):
    
    try:
        folder_id = request.form.get('folder_id', 'root')
        print(folder_id)
        credentials = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=credentials)

        service.files().delete(fileId = file_id).execute()

    except HttpError as error:
        print(f"An error in deleting occurred: {error}")


    return redirect(url_for('dashboard', folder_id=folder_id))



'''
builds the folder heirarchy all the way to the root. 
'''
def get_breadcrumb(service, folder_id):
    breadcrumbs = []

    while folder_id and folder_id != 'root':

        #getting folder metadata
        folder = service.files().get(fileId=folder_id, fields="id, name, parents").execute()
        #insert parent at the begining of the list
        breadcrumbs.insert(0, {"id": folder['id'], "name": folder['name']})
        folder_id = folder.get("parents", [None])[0]

    return breadcrumbs

'''
Format date-time in metadata to simpler format  
'''
def format_time(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%b %d, %Y — %I:%M %p")
    except Exception:
        return "Unknown"



if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)