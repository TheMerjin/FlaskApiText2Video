import gunicorn.app.base
from gunicorn.six import iteritems
from app import app

class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = {key: value for key, value in iteritems(self.options)
                 if key in self.cfg.settings and value is not None}
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    options = {
        'bind': '0.0.0.0:8000',
        'workers': 4,
        'worker_class': 'sync',
        'timeout': 30,
    }
    StandaloneApplication(app, options).run() 