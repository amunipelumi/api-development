import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.oauth2 import access_token
from app import models

# from alembic import command


SQLALCHEMY_DATABASE_URL = (
    f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}-test'
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def session():
    print("my fixture ran")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture()
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

@pytest.fixture
def test_user(client):
    user_data = {"email": "mike@email.com",
                 "username": "mike",
                 "password": "mikepassword"}
    res = client.post("/users/register", json=user_data)

    assert res.status_code == 201

    new_user = res.json()
    new_user['password'] = user_data['password']
    return new_user

@pytest.fixture
def test_user2(client):
    user_data = {"email": "john@email.com",
                 "username": "john",
                 "password": "johnpassword"}
    res = client.post("/users/register/", json=user_data)

    assert res.status_code == 201

    new_user = res.json()
    new_user['password'] = user_data['password']
    return new_user

@pytest.fixture
def token(test_user):
    return access_token({"username": test_user['username']})

@pytest.fixture
def authorized_client(client, token):
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {token}"
    }
    return client

@pytest.fixture
def test_posts(test_user, session, test_user2):
    posts_data = [
        {
            "title": "1st title",
            "content": "1st content",
            "user_id": test_user['id']
        }, 
        {
            "title": "2nd title",
            "content": "2nd content",
            "user_id": test_user['id']
        },
        {
            "title": "3rd title",
            "content": "3rd content",
            "user_id": test_user['id']
        }, 
        {
            "title": "other title",
            "content": "other content",
            "user_id": test_user2['id']
        }
    ]

    def create_post_model(post):
        return models.Post(**post)

    post_map = map(create_post_model, posts_data)

    # session.add_all([
    #     models.Post(title="1st title", content="1st content", owner_id=test_user['id']),
    #     models.Post(title="2nd title", content="2nd content", owner_id=test_user['id']), 
    #     models.Post(title="3rd title", content="3rd content", owner_id=test_user['id']),
    # ])

    session.add_all(list(post_map))
    session.commit()
    posts = session.query(models.Post).order_by(models.Post.id).all()
    return posts
