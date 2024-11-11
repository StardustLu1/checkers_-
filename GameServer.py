import socketserver
import Config
import ast

class Player(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self._pid = -1
        self._state = 0

    def handle(self):
        while True:
            dms = self.receive_message()
            if not dms or 'CMD' not in dms:
                continue
            g = GameServer.get_game_handle()
            msgs = {}
            if dms['CMD'] == 'MOVE':
                new_pos = dms['NEW_POS']
                ball_id = dms['BALL_ID']
                g.move_ball(self._pid, ball_id, new_pos)

            elif dms['CMD'] == 'ADD':
                print("A player added in...")
                pid = g.get_valid_player_id()
                if pid >= 0:
                    msgs["MSG"] = "OK"
                    msgs['PID'] = pid + 1
                    self.send_message(msgs)
                else:
                    msgs['MSG'] = 'REFUSE'
                    self.send_message(msgs)
                    break
            elif dms['CMD'] == 'Joined':
                self._state = 1
                self._pid = dms['PID']
                print("Player ID:", self._pid)
                g.init_player_info(self)  # 网络连接成功，id已经存储，初始化服务器中的实例信息
            elif dms['CMD'] == 'READY':
                self._state = 2
                msgs = {'MSG': "RESP_READY"}
                self.send_message(msgs)
                g.start_game()
            elif dms['CMD'] == 'RESP_START':
                self._state = 3
                g.enter_game()

    def get_id(self):
        return self._pid

    def send_message(self, data):
        msg = f'{data}\n'
        self.request.sendall(msg.encode('utf-8'))

    def receive_message(self):
        try:
            stream = self.request.recv(1024).decode('utf-8')
            print(f"Data received: {stream}")  # 调试输出
            if stream is None or stream == '':
                return None
            dct = {}
            try:
                for s in stream.split('\n'):
                    if s != '':
                        dct.update(ast.literal_eval(s))
            except Exception as e:
                print(f"Error parsing message: {e}")
                return None
            return dct
        except Exception as e:
            print(f"Receive error: {e}")
            return None

    def set_id(self, pid):
        self._pid = pid

class GameServer:
    game = None

    def __init__(self):
        self._player_list = []
        self.cur_player_id = 0
        self.id_dispatch = [False for _ in range(6)]
        self._server = None
        self._state = 0

    @classmethod
    def get_game_handle(cls):
        if cls.game is None:
            cls.game = GameServer()
        return cls.game

    def init_player_info(self, player):
        self._player_list.append(player)  # 把玩家加入玩家列表
        print("Player ID:", player.get_id())
        self.id_dispatch[player.get_id() - 1] = True  # 设置玩家ID已经被使用
        pid_list = [p.get_id() for p in self._player_list]
        dct = {'MSG': 'NEW', 'PList': pid_list}
        self.notify_all_players(dct)  # 通知其他所有玩家

    def start_server(self):
        self._server = socketserver.ThreadingTCPServer((Config.ServerIP, Config.Port), Player)
        print("Start to waiting for new players to join")
        self._server.serve_forever()

    def get_valid_player_id(self):
        for pid in range(len(self.id_dispatch)):
            if not self.id_dispatch[pid]:
                return pid
        return -1

    def notify_all_players(self, dct):

        for p in self._player_list:
            p.send_message(dct)
            print(p)

    def start_game(self):  # 检测是否所有玩家已经进入准备状态
        for p in self._player_list:
            if p._state != 2:
                break
        else:  # 如果是，向所有玩家发出启动指令
            msgs = {'MSG': 'START'}
            print('Send start command to all players and waiting for their responses')
            self.notify_all_players(msgs)

    def enter_game(self):
        for p in self._player_list:
            if p._state != 3:
                break
        else:
            self._state = 1
            print('Game evently started')

    def move_ball(self, pid, ball_id, new_pos):
        move_msg = {
            'CMD': 'MOVE',
            'PID': pid,
            'BALL_ID': ball_id,
            'NEW_POS': new_pos
        }
        self.notify_all_players(move_msg)

game = GameServer()
game.start_server()