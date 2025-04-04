from strac_app import app as flask
import pytest
from unittest.mock import patch, MagicMock
import io


@pytest.fixture
def client():
    flask.config['TESTING'] = True
    with flask.test_client() as client:
        yield client

@pytest.fixture
def fake_credentials():
    return {
        'token': 'fake-token',
        'refresh_token': 'fake-refresh-token',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'fake-client-id',
        'client_secret': 'fake-client-secret',
        'scopes': ['https://www.googleapis.com/auth/drive']
    }


# testing landing page which contains the sign-in
def test_landing_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Sign in with Google' in response.data

# testing if redirects to sign in if no user logged in
def test_dashboard_redirects_if_not_logged_in(client):
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/authorize' in response.headers['Location'] or '/'


def test_authorize_redirects_to_google(client):
    response = client.get('/authorize')
    assert response.status_code == 302
    assert 'accounts.google.com' in response.headers['Location']


# testing the dashboard with mock data.
def test_dashboard_authenticated(client, fake_credentials):

    with client.session_transaction() as sess:
        sess['credentials'] = fake_credentials

    # Mock Drive API response
    with patch('strac_app.build') as mock_build:
        mock_service = mock_build.return_value
        mock_files = mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            'files': [
                {'id': '123', 'name': 'Test File.txt', 'mimeType': 'text/plain', 'modifiedTime': '2025-04-03T12:00:00.000Z'}
            ]
        }

        # Mock breadcrumb to avoid actual API calls
        with patch('strac_app.get_breadcrumb', return_value=[{'id': 'root', 'name': 'My Drive'}]):
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'Test File.txt' in response.data
            assert b'My Drive' in response.data



def test_upload_file(client, fake_credentials):
    with client.session_transaction() as sess:
        sess['credentials'] = fake_credentials

    file_content = b'Hello, Drive!'
    data = {
        'file': (io.BytesIO(file_content), 'test.txt'),
        'folder_id': 'root'
    }

    with patch('strac_app.build') as mock_build, \
         patch('strac_app.MediaFileUpload') as mock_media_upload, \
         patch('strac_app.os.remove') as mock_os_remove:

        mock_service = mock_build.return_value
        mock_files = mock_service.files.return_value
        mock_files.create.return_value.execute.return_value = {}

        response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200




def test_delete_file(client, fake_credentials):
    with client.session_transaction() as sess:
        sess['credentials'] = fake_credentials

    with patch('strac_app.build') as mock_build:
        mock_service = mock_build.return_value
        mock_service.files.return_value.delete.return_value.execute.return_value = {}

        response = client.post('/delete/12345', data={'folder_id': 'root'}, follow_redirects=True)
        assert response.status_code == 200