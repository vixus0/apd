from cropdb import app
from cropdb.utils import template

# - index
#   GET:
#       Display the homepage.
@app.route('/')
def index():
    return template('index.html')
