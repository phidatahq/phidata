import json

from oauthlib.common import to_unicode


def douban_compliance_fix(session):
    def fix_token_type(r):
        token = json.loads(r.text)
        token.setdefault("token_type", "Bearer")
        fixed_token = json.dumps(token)
        r._content = to_unicode(fixed_token).encode("utf-8")
        return r

    session._client_default_token_placement = "query"
    session.register_compliance_hook("access_token_response", fix_token_type)

    return session
