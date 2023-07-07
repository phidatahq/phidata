from json import dumps

try:
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import parse_qsl

from oauthlib.common import to_unicode


def facebook_compliance_fix(session):
    def _compliance_fix(r):
        # if Facebook claims to be sending us json, let's trust them.
        if "application/json" in r.headers.get("content-type", {}):
            return r

        # Facebook returns a content-type of text/plain when sending their
        # x-www-form-urlencoded responses, along with a 200. If not, let's
        # assume we're getting JSON and bail on the fix.
        if "text/plain" in r.headers.get("content-type", {}) and r.status_code == 200:
            token = dict(parse_qsl(r.text, keep_blank_values=True))
        else:
            return r

        expires = token.get("expires")
        if expires is not None:
            token["expires_in"] = expires
        token["token_type"] = "Bearer"
        r._content = to_unicode(dumps(token)).encode("UTF-8")
        return r

    session.register_compliance_hook("access_token_response", _compliance_fix)
    return session
