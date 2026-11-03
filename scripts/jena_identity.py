"""Deployment entry point for Jena's private, independent token verifier.

Run in the pinned API image, bound only to loopback port 8001. Reuse the
installed identity blueprint and token codec; do not initialize the full API,
Redis or database connections. A separate worker pool prevents public requests
waiting for Jena from also occupying every worker needed by its callback.
"""
import os

from flask import Flask
from oldap_api.views.jena_identity_views import jena_identity_bp
from oldaplib.src.authentication import TokenSettings


def create_app():
    """Build only token verification and readiness routes, or fail at startup.

    Required environment: Jena backend selection, callback service key and the
    API access signing key. Issuer/audience must match the public API. This
    application deliberately receives no database or administrative credentials.
    """
    if os.getenv('OLDAP_BACKEND') != 'jena' or not os.getenv('OLDAP_JENA_IDENTITY_KEY'):
        raise RuntimeError('Private identity service requires Jena and its callback key.')
    TokenSettings.from_environment().require_access_secret()
    app = Flask(__name__)
    app.register_blueprint(jena_identity_bp)

    @app.get('/_ready')
    def ready():
        """Report process readiness without consulting any external service."""
        return {'status': 'ok'}

    return app
