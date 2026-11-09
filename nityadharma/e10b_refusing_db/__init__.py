"""Connection-refusing DB engine for E10B Celery worker probe only.

Not under nityadharma.settings — importing this package must not load
nityadharma.settings.__init__ (which pulls in dev/base).
"""
