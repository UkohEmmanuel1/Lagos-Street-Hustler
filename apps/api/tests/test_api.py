import os
import secrets
from fastapi.testclient import TestClient

os.environ.setdefault('SQLITE_PATH', '/tmp/lagos-street-hustler-tests.db')
os.environ.setdefault('JWT_SECRET_KEY', 'test-only-secret-do-not-use-in-production-123456')

from app.main import app
client = TestClient(app)

def new_account():
    suffix = secrets.token_hex(4)
    username = 'test_' + suffix
    password = 'strong-test-password-' + suffix
    response = client.post('/auth/register', json={'username': username, 'password': password})
    assert response.status_code == 201, response.text
    return username, password, response.json()['access_token']

def test_health_and_missions_are_public():
    assert client.get('/health').status_code == 200
    response = client.get('/missions')
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_protected_player_route_requires_authentication():
    assert client.get('/players/me').status_code == 401

def test_register_login_and_player_profile():
    username, password, token = new_account()
    headers = {'Authorization': 'Bearer ' + token}
    profile = client.get('/players/me', headers=headers)
    assert profile.status_code == 200
    assert profile.json()['name'] == username
    login = client.post('/auth/login', json={'username': username, 'password': password})
    assert login.status_code == 200
    assert login.json()['token_type'] == 'bearer'
    assert client.post('/auth/login', json={'username': username, 'password': 'incorrect-password'}).status_code == 401

def test_phone_apps_require_authentication():
    _, _, token = new_account()
    response = client.get('/apps', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    app_ids = {item['id'] for item in response.json()['apps']}
    assert {'map', 'wallet', 'contacts', 'social', 'rides', 'jobs', 'chat', 'voice'} <= app_ids

def test_message_history_is_authenticated_and_bounded():
    _, _, token = new_account()
    headers = {'Authorization': 'Bearer ' + token}
    assert client.get('/messages').status_code == 401
    response = client.get('/messages?room=nearby&limit=10', headers=headers)
    assert response.status_code == 200
    assert len(response.json()['messages']) <= 10

def test_unknown_mission_returns_404():
    _, _, token = new_account()
    response = client.post('/missions/not-a-mission/complete', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 404
