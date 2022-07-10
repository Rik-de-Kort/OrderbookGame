from functools import wraps
import os
import tempfile
from typing import Callable

from fastapi.testclient import TestClient
from hypothesis import strategies as st, given, settings

import api as api
from db_utils import create_db

client = TestClient(api.app)  # Is it good to have a global test client?
api.N_REQUESTS = 1e10  # disable rate limit


# We use a decorator here rather than a pytest fixture because of interactions with Hypothesis.
def with_temp_db(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(*a, **kw):
        with tempfile.NamedTemporaryFile() as file:
            conn = create_db(file.name)
            conn.commit()
            conn.close()
            os.environ['DB_LOCATION'] = file.name
            return func(*a, **kw)

    return wrapped


@with_temp_db
def test_smoke():
    response = client.get('/')
    assert response.status_code == 200


@st.composite
def new_users(draw) -> dict:
    return {
        'name': draw(st.text()),
        'password': draw(st.text(min_size=1, alphabet=st.characters(whitelist_categories=['L', 'P', 'N', 'S']))),
    }


@settings(deadline=None)
@given(users=st.lists(new_users(), min_size=1, unique_by=lambda x: x['name']))
@with_temp_db
def test_signup(users):
    for user in users:
        response = client.post('/signup', params=user)
        assert response.status_code == 201, response.json()


some_users = [  # lists(new_users(), min_size=20, max_size=20, unique_by=lambda x: x['name']).example()
    {'name': '', 'password': '珎ĄH'}, {'name': '\x90\x17\x98jp', 'password': 'Ó¸wc@|'},
    {'name': 'ßèR\x92\U000e76a6y\n(`è', 'password': '𰟑塀ăĦ'},
    {'name': '\x92\x83Îl/\x07ëq~z', 'password': '³ðĈ¦ᔝÝĀòpeÁ<e🇩¥'},
    {'name': '5\x00å\x9f\x11öª³\x02{', 'password': 'ĜkĿČĞ'}, {'name': '\x9b7*Äæ', 'password': 'Ľ;Å'},
    {'name': '¹ÅV\x81e\x8b', 'password': 'MĉXĿ𰳚ô'}, {'name': 'g\x87', 'password': '𣺔'},
    {'name': '*»¬\x9d\U00043e80\U000a299d]A"0.', 'password': 'ı쫳Ñ𗅞sbxBľ'}, {'name': 'é', 'password': '𫖾℧ø'},
    {'name': '\U000bbd03\x1c\U000ae8aeW\x15\x98\x12', 'password': 'ģ仦'},
    {'name': 'Þr\x90\U00048257jû\U0009d1df|6', 'password': "&垡¬ç㝓ĐÞĉŁ`ÙuĄ§ėĖ𡞞ĳ¤}'Ģēwᇶ愮"},
    {'name': '\x1c(L\U000a571b', 'password': 'Ċ𭀁'}, {'name': '\x83𧖰\\LËi\x15=', 'password': 'Å'},
    {'name': '3\x03~', 'password': 'Æ𰙥|IT'}, {'name': 'CÀ\xad¢\x1fS', 'password': 'ī샧𬻩)1+ĨĉĠ"m𨭐'},
    {'name': '²¡\U0007f625', 'password': 'dwéøq'}, {'name': '\x14&q', 'password': '¤"[°𥭰'},
    {'name': '\U0005156d', 'password': 'ÿ¬)'}, {'name': '»', 'password': '÷'}
]
