import os
import uuid
import psycopg2, psycopg2.extras
from flask import Flask, session, render_template
from flask.ext.socketio import SocketIO, emit

app = Flask(__name__, static_url_path='')
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.debug = True
socketio = SocketIO(app)

messages = []
users = {}




def connectToDB():
  connectionString = 'dbname=irc user=postgres password=postgres host=localhost'
  try:
    return psycopg2.connect(connectionString)
  except:
    print("Can't connect to database")

def updateRoster():
    names = []
    for user_id in  users:
        print users[user_id]['username']
        if len(users[user_id]['username'])==0:
            names.append('Anonymous')
        else:
            names.append(users[user_id]['username'])
    print 'broadcasting names'
    emit('roster', names, broadcast=True)
    


@socketio.on('connect', namespace='/chat')
def test_connect():
    session['uuid']=uuid.uuid1()
    session['username']='starter name'
    print 'connected'
    
    users[session['uuid']]={'username':'New User'}
    updateRoster()
    
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    fetch_messages = "select text, username from messages join users on users.id = messages.name"
    cur.execute(fetch_messages)
    messages = cur.fetchall()
    
    keys = ['text', 'name']
    
    for message in messages:
        message = dict(zip(keys,message))
        print(message)
        emit('message', message)

@socketio.on('message', namespace='/chat')
def new_message(message):

    tmp = {'text':message, 'name':users[session['uuid']]['username']}
    messages.append(tmp)
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    message_insert = "INSERT INTO messages VALUES (default, %s, %s)";
    cur.execute(message_insert, (message, session['id']))
    conn.commit()
    emit('message', tmp, broadcast=True)
    
@socketio.on('identify', namespace='/chat')
def on_identify(message):
    print 'identify' + message
    users[session['uuid']]={'username':message}
    updateRoster()

@socketio.on('search', namespace='/chat')
def on_search(search):
    print 'search: ' 
    search = '%' + search + '%'
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    search_query = "select username, text from messages join users on messages.name = users.id where text like %s or username like %s"
    cur.execute(search_query, (search, search))
    results = cur.fetchall()
    keys = ['name', 'text']
    

    emit('clearResults', {})    
    for result in results:
    
        emit('search', dict(zip(keys,result)))
        
@socketio.on('login', namespace='/chat')
def on_login(data):
    
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    login_query = "select * from users where username = %s AND password = crypt(%s, password)"
    cur.execute(login_query, (data['username'], data['password']))
    result = cur.fetchone()
    if result:
        users[session['uuid']]={'username': data['username']}
        session['username'] = data['username']
        session['id'] = result['id']
        print 'successful login'
        updateRoster()

    
    
@socketio.on('disconnect', namespace='/chat')
def on_disconnect():
    print 'disconnect'
    if session['uuid'] in users:
        del users[session['uuid']]
        updateRoster()

@app.route('/')
def hello_world():
    print 'in hello world'
    #return app.send_static_file('index.html')
    return render_template('index.html')


@app.route('/js/<path:path>')
def static_proxy_js(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(os.path.join('js', path))
    
@app.route('/css/<path:path>')
def static_proxy_css(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(os.path.join('css', path))
    
@app.route('/img/<path:path>')
def static_proxy_img(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(os.path.join('img', path))
    
if __name__ == '__main__':
    print "A"

    socketio.run(app, host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT', 8080)))
     