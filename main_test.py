import os
import re

import google.auth
import main
import pytest
import requests
from six import BytesIO


credentials, project_id = google.auth.default()
os.environ['GOOGLE_CLOUD_PROJECT'] = project_id


@pytest.yield_fixture
def app(request):
    """This fixture provides a Flask app instance configured for testing.
    It also ensures the tests run within a request context, allowing
    any calls to flask.request, flask.current_app, etc. to work."""
    app = main.app

    with app.test_request_context():
        yield app


@pytest.yield_fixture
def firestore():

    import firestore
    """This fixture provides a modified version of the app's Firebase model that
    tracks all created items and deletes them at the end of the test.
    Any tests that directly or indirectly interact with the database should use
    this to ensure that resources are properly cleaned up.
    """

    # Ensure no images exist before running the tests. This typically helps if
    # tests somehow left the database in a bad state.
    delete_all_images(firestore)

    yield firestore

    # Delete all images that we created during tests.
    delete_all_images(firestore)


def delete_all_images(firestore):
    while True:
        images, _ = firestore.next_page(limit=50)
        if not images:
            break
        for image in images:
            firestore.delete(image['id'])


def test_list(app, firestore):
    for i in range(1, 12):
        firestore.create({'title': u'Image {0}'.format(i)})

    with app.test_client() as c:
        rv = c.get('/')

    assert rv.status == '200 OK'

    body = rv.data.decode('utf-8')
    assert 'Image 1' in body, "Should show images"
    assert len(re.findall('<h4>Image', body)) <= 10, (
        "Should not show more than 10 images")
    assert 'More' in body, "Should have more than one page"


def test_add(app):
    data = {
        'title': 'Test Image',
        'author': 'Test Author',
        'publishedDate': 'Test Date Published',
        'description': 'Test Description'
    }

    with app.test_client() as c:
        rv = c.post('images/add', data=data, follow_redirects=True)

    assert rv.status == '200 OK'
    body = rv.data.decode('utf-8')
    assert 'Test Image' in body
    assert 'Test Author' in body
    assert 'Test Date Published' in body
    assert 'Test Description' in body


def test_edit(app, firestore):
    existing = firestore.create({'title': "Temp Title"})

    with app.test_client() as c:
        rv = c.post(
            'images/%s/edit' % existing['id'],
            data={'title': 'Updated Title'},
            follow_redirects=True)

    assert rv.status == '200 OK'
    body = rv.data.decode('utf-8')
    assert 'Updated Title' in body
    assert 'Temp Title' not in body


def test_delete(app, firestore):
    existing = firestore.create({'title': "Temp Title"})

    with app.test_client() as c:
        rv = c.get(
            'images/%s/delete' % existing['id'],
            follow_redirects=True)

    assert rv.status == '200 OK'
    assert not firestore.read(existing['id'])


def test_upload_image(app):
    data = {
        'title': 'Test Image',
        'author': 'Test Author',
        'publishedDate': 'Test Date Published',
        'description': 'Test Description',
        'image': (BytesIO(b'hello world'), 'hello.jpg')
    }

    with app.test_client() as c:
        rv = c.post('images/add', data=data, follow_redirects=True)

    assert rv.status == '200 OK'
    body = rv.data.decode('utf-8')

    img_tag = re.search('<img.*?src="(.*)"', body).group(1)

    r = requests.get(img_tag)
    assert r.status_code == 200
    assert r.text == 'hello world'


def test_upload_bad_file(app):
    data = {
        'title': 'Test Image',
        'author': 'Test Author',
        'publishedDate': 'Test Date Published',
        'description': 'Test Description',
        'image': (BytesIO(b'<?php phpinfo(); ?>'),
                  '1337h4x0r.php')
    }

    with app.test_client() as c:
        rv = c.post('/images/add', data=data, follow_redirects=True)

    # check we weren't pwned
    assert rv.status == '400 BAD REQUEST'
