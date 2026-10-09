import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from heart.api.routes_google_auth import _verify_google_token


@pytest.mark.asyncio
async def test_google_identity_verifies_signature_nonce_issuer_and_verified_email():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public['kid'] = 'test-key'
    client = AsyncMock()
    client.get.return_value = httpx.Response(200, json={'keys':[public]}, request=httpx.Request('GET','https://www.googleapis.com/oauth2/v3/certs'))
    now = int(time.time())
    base = {'iss':'https://accounts.google.com','aud':'test-client','sub':'1234','email':'hello@gmail.com','email_verified':True,'nonce':'test-nonce','iat':now,'exp':now+60}
    with patch('heart.api.routes_google_auth.settings.google_client_id', 'test-client'):
        for override, succeeds in [({},True), ({'nonce':'wrong'},False), ({'iss':'https://attacker.invalid'},False), ({'aud':'other'},False), ({'email_verified':False},False), ({'exp':now-1},False), ({'azp':'other'},False)]:
            token=jwt.encode({**base,**override},key,algorithm='RS256',headers={'kid':'test-key'})
            if succeeds:
                assert (await _verify_google_token(token,'test-nonce',client))['sub']=='1234'
            else:
                with pytest.raises((ValueError,jwt.PyJWTError)):
                    await _verify_google_token(token,'test-nonce',client)
    assert all(call.args[0]=='https://www.googleapis.com/oauth2/v3/certs' for call in client.get.call_args_list)
