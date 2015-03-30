import os
import uuid
import psycopg2, psycopg2.extras
from flask import Flask, session, render_template, jsonify, request
from flask.ext.socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__, static_url_path='')
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.debug = True
socketio = SocketIO(app)

messages = []
users = {}
rooms = []



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
    
@socketio.on('update_rooms', namespace='/chat')
def updateRooms():
    emit('rooms', rooms)
    
    
@socketio.on('joinRoom', namespace ='/chat')
def joinRoom(data):    
    con = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    join_query = "INSERT INTO users_rooms values (%s, %s)"
    cur.execute(join_query, (session['id'], data['room']['id']))
    conn.commit()
    emit('yesPrivilege', 'garbage')
    on_join({'username': session['username'], 'room' : data['room']})
    
@socketio.on('leaveRoom', namespace ='/chat')
def leaveRoom(data):    
    con = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        leave_query = "DELETE FROM users_rooms WHERE user_id = %s AND room_id =  %s"
        cur.execute(leave_query, (session['id'], data['room']['id']))
        conn.commit()
        emit('noPrivilege', 'garbage')
        on_leave({'username': session['username'], 'room' : data['room']})
    except Exception as e:
        print('fail to delete')
    
@socketio.on('join', namespace ='/chat')
def on_join(data):
    username = data['username']
    room = data['room']
    
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    can_join_query = "SELECT * FROM users_rooms WHERE user_id = %s AND room_id = %s"
    cur.execute(can_join_query, (session['id'], room['id']))
    result = cur.fetchone()
    if result:
        
        join_room(str(room['id']))
        message_query = "select text, username from messages join users on users.id = messages.name WHERE room = %s"
        cur.execute(message_query, (room['id'],))
        results = cur.fetchall()
        for result in results:
            result = {'text': result['text'], 'name' : result['username']}
            emit('message', result)
        emit('yesPrivilege', 'garbage')
        print("%s successfully joined room %s" % (username, room['name']))
    else:
        emit('noPrivilege', 'garbage')
        print("%s could not join %s because he does not have privilege" % (username, room['name']))
    #emit(username + ' has entered the room.', room=room)

@socketio.on('leave', namespace = '/chat')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(str(room['id']))
    print("%s successfully left room %s" % (username, room['name']))
    
@socketio.on('new_room', namespace='/chat')
def new_room(data):
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    new_room_query = "SELECT * FROM rooms where name = %s"
    cur.execute(new_room_query, (data['name'],))
    result = cur.fetchone()
    if not result:
        insert_room_query = "INSERT INTO rooms VALUES ( default, %s ) RETURNING id"
        cur.execute(insert_room_query, (data['name'],))
        id_of_new_row = cur.fetchone()[0]
        conn.commit()
        
        rooms.append({'name' : data['name'], 'id' : id_of_new_row})
        print 'updating rooms'
        updateRooms()
        print('rooms: ' + str(rooms))
    cur.close()
    conn.close()
        

# @app.route('/room_list', methods=['GET'])
# def room_list():
#     return 

@socketio.on('connect', namespace='/chat')
def test_connect():
    session['uuid']=uuid.uuid1()
    session['username']='starter name'
    print 'connected'
    
    users[session['uuid']]={'username':'New User'}
    updateRoster()
    updateRooms()
  

@socketio.on('message', namespace='/chat')
def new_message(message):

    tmp = {'text':message['text'], 'room':message['room'], 'name':users[session['uuid']]['username']}
    room= message['room']
    messages.append(tmp)
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    message_insert = "INSERT INTO messages VALUES (default, %s, %s, %s)";
    cur.execute(message_insert, (message['text'], session['id'], room['id']))
    conn.commit()
    print(str(room['id']))
    emit('message', tmp, room=str(room['id']))
    
@socketio.on('identify', namespace='/chat')
def on_identify(message):
    if 'uuid' in session:
        users[session['uuid']]={'username':message}
        updateRoster()
    else:
        print 'sending information'
        session['uuid']=uuid.uuid1()
        session['username']='starter name'
  
    
        updateRoster()
        updateRooms()

        for message in messages:
            emit('message', message)

@socketio.on('search', namespace='/chat')
def on_search(search):
    print 'search: ' 
    searchTerm = '%' + search['searchTerm'] + '%'
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    search_query = "select username, text from messages join users on messages.name = users.id where (text like %s or username like %s) AND room = %s"
    cur.execute(search_query, (searchTerm, searchTerm, search['room']['id']))
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
        
        # conn = connectToDB()
        # cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # fetch_messages = "select text, username from messages join users on users.id = messages.name"
        # cur.execute(fetch_messages)
        # messages = cur.fetchall()
        # keys = ['text', 'name']
        
        # for message in messages:
        #     message = dict(zip(keys,message))
        #     print(message)
        #     emit('message', message)
        
        room_names = "select name from rooms join rooms_users on rooms.id = rooms_users.room_id JOIN users on rooms_users.user_id = users.id"
        cur.execute(room_names)
        the_rooms = cur.fetchall()
        on_join({'username': session['username'], 'room': {'name': 'firstlogin', 'id': '1'}})
        for room in the_rooms:
            room = {'name': room[0]}
            print('adding room ', room)
            emit('room', room)
        
        
        
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
    return app.send_static_file('index.html')
    #return render_template('index.html')


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
    conn = connectToDB()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    room_names = "select name, id from rooms"
    cur.execute(room_names)
    the_rooms = cur.fetchall()
    for room in the_rooms:
        room = {'name': room[0], 'id' : room[1]}
        rooms.append(room)
        print("on boot: added room: ", room)
    socketio.run(app, host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT', 8080)))
    

     