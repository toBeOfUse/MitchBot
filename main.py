# python libraries
import asyncio
import inspect
import json
import os
import sys
from collections import defaultdict

# package dependencies
import tornado.httpclient
import tornado.web
import tornado.websocket

# project files
import MitchBot
from responders import add_responses

if sys.platform == 'win32':
    # required for tornado in python 3.8
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

discord_client = None  # instantiated in main() so as to use the event loop created when main() is run
http_client = tornado.httpclient.AsyncHTTPClient()


# basic websocket handler that emits and listens for events that are broadcast with websocket messages. heavily inspired
# by the SocketIO websocket library but without all the complicated "rooms" stuff. has three built-in events:
# 'connected' and 'closed', which it handles when those events happen, and 'set-state', which it emits to the websocket
# client when the built-in state_listener function is called with a new key and value for a state component.
class WebSocketEventHandler(tornado.websocket.WebSocketHandler):
    handlers = defaultdict(list)

    # internal logic:

    def __init__(self, *args):
        super().__init__(*args)
        self.state_listener = lambda key, value: self.emit('set-state', {key: value})

    def open(self):
        self.handle('connected', {"ip": self.request.remote_ip})

    def on_close(self):
        self.handle('closed')

    def on_message(self, message):
        m = json.loads(message)
        if 'event' not in m:
            print('Error: malformed ws event with no event name')
        else:
            if 'details' not in m:
                m['details'] = None
            self.handle(m['event'], m['details'])

    def handle(self, event_name, details=None):
        if event_name in self.handlers:
            [asyncio.create_task(x(self, details))
             if inspect.iscoroutinefunction(x) else x(self, details)
             for x in self.handlers[event_name]]
        else:
            print('received '+event_name+' event without having a handler to handle it')

    # public interface:

    # use this as a decorator to register event handlers
    @classmethod
    def on_event(cls, event_name):
        def decorator(f):
            cls.handlers[event_name].append(f)
            return f

        return decorator

    def emit(self, event_name, details=None):
        event = {"event": event_name, "details": details}
        self.write_message(event)


@WebSocketEventHandler.on_event('connected')
async def connected(connection, details):
    if details['ip'] == '::1' or '192.168' in details['ip']:
        print('websocket connected from local network')
    else:
        geo = json.loads((await http_client.fetch('https://ipinfo.io/'+details['ip']+'/geo')).body)
        print('websocket connected from', details['ip'], geo['country'], geo['region'], geo['city'])
    discord_client.set_prompts(discord_client.get_prompts())  # sounds legit
    connection.emit('set-state', discord_client.public_state)
    discord_client.public_state.add_listener(connection.state_listener)


@WebSocketEventHandler.on_event('closed')
def closed(connection, details):
    print('websocket closed')
    discord_client.public_state.remove_listener(connection.state_listener)


@WebSocketEventHandler.on_event('interrupt')
def stop(connection, details):
    discord_client.interrupt_current_audio()


@WebSocketEventHandler.on_event('switch_voice')
def switch_voice(connection, details):
    discord_client.change_voice()


@WebSocketEventHandler.on_event('say')
async def say(connection, details):
    await discord_client.say(details['text'])


@WebSocketEventHandler.on_event('vc_connect')
async def vc_connect(connection, details):
    await discord_client.connect_to_vc(int(details['channel_id']))


@WebSocketEventHandler.on_event('turn_off')
async def turn_off(connection, details):
    await discord_client.logout()


@WebSocketEventHandler.on_event('send_message')
async def send_message(connection, details):
    channel = discord_client.get_channel(int(details['channel_id']))
    await channel.send(details['message'])


@WebSocketEventHandler.on_event('start_song')
async def start_song(connection, details):
    await discord_client.start_playing('music/' + details['song'] + ".mp3", details['song'])


@WebSocketEventHandler.on_event('new-prompts')
def new_prompts(connection, details):
    discord_client.set_prompts(details)


static = os.path.join(os.getcwd(), "static\\")
server = tornado.web.Application([
    (r"/socket", WebSocketEventHandler),
    (r"/(.*)", tornado.web.StaticFileHandler, {"default_filename": "index.html", "path": static}),
])


async def main():
    global discord_client
    discord_client = MitchBot.MitchClient()
    add_responses(discord_client)
    server.listen(9876)
    token_file = open('login_token.txt')
    await discord_client.login(token_file.read())
    token_file.close()
    await discord_client.connect()

if __name__ == "__main__":  # if this file is being run directly, not imported or being tested
    asyncio.run(main())
