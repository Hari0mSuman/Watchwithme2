from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import random
import string

app = Flask(__name__)
app.secret_key = 'watchwithme-secret'
socketio = SocketIO(app, async_mode='eventlet')

rooms = {}  # In-memory storage: room_code → {video_id, playback_time, is_playing, messages}

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_room():
    room_code = generate_room_code()
    rooms[room_code] = {
        'video_id': '',
        'playback_time': 0,
        'is_playing': False,
        'messages': []
    }
    session['room'] = room_code
    return  redirect(url_for('watch', room_code=room_code))

@app.route('/watch/<room_code>')
def watch(room_code):
    session['room'] = room_code
    full_url = request.host_url + 'watch/' + room_code
    return render_template('playback.html', room_code=room_code, room_url=full_url)

# SocketIO EVENTS

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('init_state', rooms[room], room=request.sid)

@socketio.on('update_state')
def update_state(data):
    room = data['room']
    if room in rooms:
        rooms[room]['playback_time'] = data['time']
        rooms[room]['is_playing'] = data['is_playing']
        emit('sync_state', data, room=room, include_self=False)

@socketio.on('set_video')
def set_video(data):
    room = data['room']
    rooms[room]['video_id'] = data['video_id']
    emit('video_changed', data, room=room)

@socketio.on('send_message')
def send_message(data):
    room = data['room']
    msg = {'user': data['user'], 'text': data['text']}
    rooms[room]['messages'].append(msg)
    emit('new_message', msg, room=room)

@socketio.on('local_video_selected')
def handle_local_video_selected(data):
    # Forward to other users in the room
    emit('local_video_selected', data, room=data['room'], include_self=False)


@socketio.on('sync_local_video')
def handle_sync_local_video(data):
    # Share playback position across users
    emit('sync_local_video', data, room=data['room'], include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
    