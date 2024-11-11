import ast
import socket
import time

import pygame
import Config
from math import *
from threading import Thread

class LocSprite(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.R = Config.NodeRadius
        self.image = pygame.Surface((self.R*2, self.R*2), pygame.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, Config.NodeColor, (self.R, self.R), self.R)
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = pos[0] - self.R, pos[1] - self.R
        self.filled = 0  # 指示当前位置是否被棋子覆盖
        self._movable = False  # 标记是否为可移动位置

    def set_movable(self, movable):
        self._movable = movable

    def draw(self):
        if self._movable:
            pygame.draw.circle(self.image, Config.MovableColor, (self.R, self.R), self.R)
        else:
            pygame.draw.circle(self.image, Config.NodeColor, (self.R, self.R), self.R)

    def update(self):
        self.draw()

    def update(self):
        self.draw()

    def p(self):
        return self.rect.x+self.R, self.rect.y + self.R

    def inbound(self, p):
        mask = pygame.mask.from_surface(self.image)  # 获取图像的透明度掩膜信息
        rt = self.rect
        return rt.collidepoint(p) and mask.get_at((p[0] - rt.x, p[1] - rt.y)) > 0


class BallSprite(pygame.sprite.Sprite):
    def __init__(self, img, p0, pid):
        super().__init__()
        self._image0 = pygame.Surface((Config.BallSize, Config.BallSize), pygame.SRCALPHA)
        self._image0.blit(img, (0, 0))
        self._image1 = pygame.Surface((Config.BallSize, Config.BallSize), pygame.SRCALPHA)
        self._image1.blit(img, (0, 0))
        BallSprite.cover_image(self._image1)
        self.image = self._image0
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = p0[0]-Config.BallSize//2, p0[1]-Config.BallSize//2
        self.selected = False
        self.bid = pid     #指示棋子是属于哪个玩家的
        self.current_position = p0

    @staticmethod
    def get_stress_color(clr):
        cvclr = Config.StressCover
        alpha = 0.7
        r = clr[0]*alpha + cvclr[0]*(1-alpha)
        g = clr[1]*alpha + cvclr[1]*(1-alpha)
        b = clr[2]*alpha + cvclr[2]*(1-alpha)
        return r, g, b, clr[3]

    @staticmethod
    def cover_image(sf):
        rt = sf.get_rect()
        w, h = rt.w, rt.h
        for i in range(h):
            for j in range(w):
                clr = sf.get_at((j, i))
                if clr.a > 0:
                    cclr = BallSprite.get_stress_color(clr)
                    sf.set_at((j, i), cclr)

    def clicked(self):
        if not self.selected:
            self.image = self._image1
            self.selected = True
        else:
            self.image = self._image0
            self.selected = False

    def inbound(self, p):
        mask = pygame.mask.from_surface(self.image)  # 获取图像的透明度掩膜信息
        rt = self.rect
        return rt.collidepoint(p) and mask.get_at((p[0] - rt.x, p[1] - rt.y)) > 0

    def moveto(self, new_pos):
        # Calculate the distance between current position and new position
        distance = sqrt((new_pos[0] - self.rect.x - Config.BallSize // 2) ** 2 +
                        (new_pos[1] - self.rect.y - Config.BallSize // 2) ** 2)

       # if distance <= Config.OneStepDistance:  # Check against OneStepDistance
        self.rect.x, self.rect.y = new_pos[0] - Config.BallSize // 2, new_pos[1] - Config.BallSize // 2
        self.current_position = new_pos  # Update current position
       # else:
       #     print("Move distance exceeds the allowed distance.")  # Handle case where distance is too large

    def getpos(self):
        return self.rect.x + Config.BallSize//2, self.rect.y + Config.BallSize//2
class Button(pygame.sprite.Sprite):
    def __init__(self, text, pos):
        super().__init__()
        self.font = pygame.font.SysFont('Arial', 20)
        self.text = text
        self.image = pygame.Surface((200, 50))
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = pos
        self.draw()

    def draw(self):
        self.image.fill((0, 0, 255))
        pygame.draw.rect(self.image, (0, 0, 0), self.rect, 2)
        text_surface = self.font.render(self.text, True, (122, 122, 122))
        text_rect = text_surface.get_rect(center=self.rect.center)
        self.image.blit(text_surface, text_rect)

    def handle_click(self):
        screen_width, screen_height = 800, 600
        screen = pygame.display.set_mode((screen_width, screen_height))

        self.image.fill((0, 255, 0))  # 按钮点击后变绿
        font = pygame.font.SysFont('Arial', 60)
        text_surface = font.render("Game Over - You Win!", True, (122, 122, 122))
        text_rect = text_surface.get_rect(center=(Config.FieldWidth - 100, Config.FieldHeight - 50))
        BoardGUI.screen.blit(text_surface, text_rect)
        pygame.display.update()
        time.sleep(2)  # 延迟两秒钟
        # 填充屏幕为黑色
        screen.fill((0, 0, 0))
        # 绘制文本到屏幕中间
        screen.blit(text_surface, (400, 300))
        time.sleep(4)  # 延迟两秒钟
        # 刷新屏幕
        pygame.display.flip()
        pygame.quit()

    def update(self):
        self.draw()

class BoardGUI:
    info = ['Click to connect the game server...',
            'server connected,please click to ready for game...',
            'ready for game,waiting for server to start game...',
            'playing...']

    def __init__(self, p0, owner):
        BoardGUI.load_texture_resource()
        self._owner = owner
        self.center = p0
        self.l2p = self.build_mapping_l_p(Config.StepLength)
        self.balls = [[] for _ in range(6)]   #存储6个玩家的棋子
        self.movable_locations = set()  # 存储所有可移动位置的 LocSprite 对象集合
        self.sprites_group = pygame.sprite.Group()
        for lsp in self.l2p.values():
            self.sprites_group.add(lsp)
        self.move_count = 0  # 添加移动计数器
        self.move_count_font = pygame.font.SysFont('timesnewroman', 20)  # 初始化计数显示字体
        self.move_count_pos = (Config.FieldWidth - 100, 20)  # 初始化计数显示位置
        self.win_positions = Config.WinPositions  # 假设在 Config 中定义了胜利条件的位置

        self.button = Button("End Game", (Config.FieldWidth - 210, Config.FieldHeight - 70))
        self.sprites_group.add(self.button)


    def check_for_victory(self, pid):
        for ball in self.balls[pid - 1]:
            if ball.getpos() not in self.win_positions[pid - 1]:
                return False
        return True

    def increment_move_count(self):
        self.move_count += 1

    def generate_player_balls(self, pid):
        if pid > len(Config.InitiPos):
            return None
        if len(self.balls[pid - 1]) == 0:
            for idx, bloc in enumerate(Config.InitiPos[pid - 1]):
                self.l2p[bloc].filled = pid
                img_idx = pid - 1  # 球形弹珠索引与玩家 ID 相关
                b = BallSprite(BoardGUI.IMAGES[img_idx], self.l2p[bloc].p(), pid)
                self.sprites_group.add(b)
                self.balls[pid - 1].append(b)

    def handle_click(self, pos):
        clicked_ball = self.select_on_ball(pos)
        if clicked_ball:
            if clicked_ball.selected:
                self.update_movable_locations(clicked_ball)
            else:
                self.clear_movable_locations()
        else:
            clicked_loc = self.select_on_loc(pos)
            if clicked_loc and clicked_loc._movable:
                clicked_loc._movable = False
                self.move_selected_ball(clicked_loc)
                self.increment_move_count()
            if clicked_loc:
                selected_ball = self.get_selected_ball()
                if selected_ball and clicked_loc in self.movable_locations:
                    self.move_ball(selected_ball.bid, self.balls[selected_ball.bid - 1].index(selected_ball),
                                   clicked_loc.p())
                    selected_ball.clicked()
                    clicked_loc.filled = selected_ball.bid
                    self.move_count += 1  # 更新移动计数器
                    print(f"Move count: {self.move_count}")  # 输出移动计数
                    self.clear_movable_locations()
            if self.check_for_victory(clicked_loc.filled):
                self.button.handle_click()  # 调用按钮的处理点击方法显示游戏胜利信息

    def move_selected_ball(self, clicked_loc):
        for ball in self.sprites_group:
            if isinstance(ball, BallSprite) and ball.selected:
                ball.moveto(clicked_loc.p())
                clicked_loc.filled = ball.bid

    def update_movable_locations(self, ball):
        self.clear_movable_locations()
        x, y = ball.getpos()
        for nbs in self.balls[ball.bid - 1]:
            if nbs.selected:
                nbs.clicked()
                break
        for lst in self.l2p.values():
            if not lst.filled and sqrt((lst.p()[0] - x) ** 2 + (lst.p()[1] - y) ** 2) < Config.StepLength:
                lst.set_movable(True)
                self.movable_locations.add(lst)
        for nbs in self.balls[ball.bid - 1]:
            if nbs.selected:
                nbs.clicked()
                break

    def clear_movable_locations(self):
        for l in self.movable_locations:
            l.set_movable(False)
        self.movable_locations.clear()

    def select_on_ball(self, pos):
        for ball in self.sprites_group:
            if isinstance(ball, BallSprite) and ball.inbound(pos):
                return ball
        return None

    def select_on_loc(self, pos):
        for l in self.sprites_group:
            if isinstance(l, LocSprite) and l.inbound(pos):
                return l
        return None

    @classmethod
    def load_texture_resource(cls):
        pygame.init()
        pygame.display.set_caption('Hopping game board')
        cls.screen = pygame.display.set_mode((Config.FieldWidth, Config.FieldHeight), flags=0)
        cls.IMAGES = []
        # 加载第一个球形弹珠
        textures = pygame.image.load('balls.png').convert_alpha()
        tts1 = pygame.transform.scale(textures.subsurface(292, 554, 630, 630),
                                      (Config.BallSize, Config.BallSize)).convert_alpha()
        cls.IMAGES.append(tts1)
        # 加载第二个球形弹珠
        tts2 = pygame.transform.scale(textures.subsurface(1096, 386, 475, 475),
                                      (Config.BallSize, Config.BallSize)).convert_alpha()
        cls.IMAGES.append(tts2)
        # 加载第三个球形弹珠
        tts3 = pygame.transform.scale(textures.subsurface(910, 1140, 550, 550),
                                      (Config.BallSize, Config.BallSize)).convert_alpha()
        cls.IMAGES.append(tts3)

    def get_selected_ball(self):
        for player_balls in self.balls:  # 遍历每个玩家的棋子
            for b in player_balls:  # 遍历每个棋子
                if b.selected:
                    return b
        return None

    def select_on_ball(self, pos):
        for player_balls in self.balls:  # 遍历每个玩家的棋子
            for b in player_balls:  # 遍历每个棋子
                if b.inbound(pos):
                    b.clicked()
                    return b
        return None

    def select_on_loc(self, pos):
        for loc in self.l2p:
            if self.l2p[loc].inbound(pos) and not self.l2p[loc].filled:
                return self.l2p[loc]
        return None

    def get_loc_sprite(self,p):
        for loc in self.l2p:
            if p == self.l2p[loc].p():
                return self.l2p[loc]
        return None

    def move_ball(self, pid, ball_id, new_pos):
        ball = self.balls[pid - 1][ball_id]
        ball.moveto(new_pos)

    def update_movable_locations(self, curb):
        self.clear_movable_locations()
        curb_pos = curb.getpos()
        for loc in self.l2p.values():
            if not loc.filled:
                distance = sqrt((loc.rect.x + Config.NodeRadius - curb_pos[0]) ** 2 +
                                (loc.rect.y + Config.NodeRadius - curb_pos[1]) ** 2)
                if distance <= Config.OneStepDistance:
                    loc.set_movable(True)
                    self.movable_locations.add(loc)

    def clear_movable_locations(self):
        for loc in self.movable_locations:
            loc.set_movable(False)
        self.movable_locations.clear()

    def gui_loop(self):
        q = False
        ffont = pygame.font.SysFont('timesnewroman', 14)  # 创建内置字体

        while not q:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if self.button.rect.collidepoint(pos):
                        self.button.handle_click()  # 处理按钮点击事件
                if event.type == pygame.QUIT:
                    q = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self._owner._state == 0:
                        self.click_to_connect_server()
                    elif self._owner._state == 1:
                        self.click_to_ready_for_game()
                    elif event.button == 1:
                        curb = self.get_selected_ball()
                        if curb:
                            lsp = self.select_on_loc(event.pos)
                            if lsp and lsp in self.movable_locations:
                                old_loc = self.get_loc_sprite(curb.getpos())
                                old_loc.filled = False
                                lsp.filled = True
                                curb.moveto(lsp.p())
                                # Send move command to server
                                ball_id = self.balls[curb.bid - 1].index(curb)
                                new_pos = lsp.p()
                                self._owner.send_move_command(ball_id, new_pos)
                                self.clear_movable_locations()
                            else:
                                self.update_movable_locations(curb)
                                print("所选位置超出跳棋可移动范围")  # Handle case where click is too far
                        else:
                            self.select_on_ball(event.pos)

                    elif event.button == 3:
                        curb = self.get_selected_ball()
                        if curb:
                            curb.clicked()

            msg = BoardGUI.info[self._owner._state]
            fontsurface = ffont.render(msg, False, (255, 255, 255))
            self.screen.fill(Config.BgkCOLOR)
            self.draw_grid_lines()
            for loc in self.l2p.values():
                loc.update()
            self.sprites_group.update()
            self.sprites_group.draw(BoardGUI.screen)
            BoardGUI.screen.blit(fontsurface, (0, 570))

            move_count_surface = self.move_count_font.render(f'Moves: {self.move_count}', True, (255, 255, 255))
            self.screen.blit(move_count_surface, self.move_count_pos)
            pygame.display.update()

        pygame.quit()

    def draw_grid_lines(self):  # 使用该函数需要先构建逻辑坐标系，获得逻辑坐标到物理坐标的映射
        begins = (-4, -4, -4, -8, -7, -6, -5, -4, -4, -4, -4, -4, 1, 2, 3)  # 15条线，y=-x-7一直到y=-x+7
        ends = (-3, -2, -1, 4, 4, 4, 4, 4, 5, 6, 7, 8, 4, 4, 4)
        for i in range(len(begins)):
            k = i - 7
            bl = begins[i], -begins[i] + k
            el = ends[i], -ends[i] + k
            b = self.l2p[bl].p()
            e = self.l2p[el].p()
            pygame.draw.line(BoardGUI.screen, Config.BoardLineColor, b, e, Config.LineWidth)
        begins = (4, 4, 4, 8, 7, 6, 5, 4, 4, 4, 4, 4, -1, -2, -3)  # 15条线，从x=-7 一直到 x=7
        ends = (3, 2, 1, -4, -4, -4, -4, -4, -5, -6, -7, -8, -4, -4, -4)
        for i in range(-7, 8):
            b = self.l2p[(i, begins[i + 7])].p()
            e = self.l2p[(i, ends[i + 7])].p()
            pygame.draw.line(BoardGUI.screen, Config.BoardLineColor, b, e, Config.LineWidth)

        begins = (-4, -4, -4, -8, -7, -6, -5, -4, -4, -4, -4, -4, 1, 2, 3)  # y=7一直到y=-7
        ends = (-3, -2, -1, 4, 4, 4, 4, 4, 5, 6, 7, 8, 4, 4, 4)
        ys = range(7, -8, -1)
        for i in range(15):
            b = self.l2p[(begins[i], ys[i])].p()
            e = self.l2p[ends[i], ys[i]].p()
            pygame.draw.line(BoardGUI.screen, Config.BoardLineColor, b, e, Config.LineWidth)

    def draw_board_locations(self):
        for loc in self.l2p.values():
            loc.update()
            p = self.l2p[loc]
            pygame.draw.circle(BoardGUI.screen, Config.NodeColor, p, Config.NodeRadius)

    def build_mapping_l_p(self, r0):
        mp = {}
        begins = (4, 3, 2, 1, -4, -4, -4, -4, -4, -5, -6, -7, -8, -4, -4, -4, -4)
        ends = (4, 4, 4, 4, 8, 7, 6, 5, 4, 4, 4, 4, 4, -1, -2, -3, -4)
        for i in range(-8, 9):
            for j in range(begins[i + 8], ends[i + 8] + 1):
                lpt = (i, j)
                ppt = (self.center[0] + r0 * i + r0 * j * cos(pi / 3), self.center[1] - r0 * j * sin(pi / 3))
                mp[lpt] = LocSprite(ppt)
        return mp

    def click_to_connect_server(self):
        return self._owner.connect_server()

    def click_to_ready_for_game(self):
        return self._owner.ready_for_game()


class PlayerClient:

    def __init__(self):
        self._state = 0
        self.board = BoardGUI(Config.BoardCenter,self)
        self._pid = -1
        self._playerlist = []
        self._conn = None

    def send_move_command(self, ball_id, new_pos):
        curb = self.board.get_selected_ball()
        if curb:
            curb.moveto(new_pos)  # 在客户端直接调用 moveto 方法，进行位置更新
            move_msg = {
                'CMD': 'MOVE',
                'BALL_ID': ball_id,
                'NEW_POS': new_pos
            }
            self.send_message(move_msg)
            self.board.increment_move_count()  # 更新移动计数器
            if self.board.check_for_victory(self._pid):  # 胜利检测
                self.handle_victory()

    def cheat_win(self):
        for pid in range(1, 7):
            for ball_id in range(len(self.board.balls[pid - 1])):
                win_pos = Config.WinPositions[pid - 1][ball_id]
                self.board.move_ball(pid, ball_id, win_pos)
                move_msg = {
                    'CMD': 'MOVE',
                    'BALL_ID': ball_id,
                    'NEW_POS': win_pos
                }
                self.send_message(move_msg)

    def show_board(self):
        self.board.gui_loop()

    def recieve_message(self):
        data = self._conn.recv(1024).decode('utf-8')
        print(f"data recieved:{data}xxx")
        if data is None or data == '':
            return None
        dct = {}
        for s in data.split('\n'):
            if s != '':
                dct.update(ast.literal_eval(s))
        return dct

    def send_message(self,data):
        msg = f'{data}'
        self._conn.sendall(msg.encode('utf-8'))

    def connect_server(self):
        try:
            self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._conn.connect((Config.ServerIP,Config.Port))
        except socket.error as err:
            print("Error:",err)
            self._conn = None
        else:   # 网络连接成功
            msgs = {"CMD": "ADD"}
            self.send_message(msgs)
            while True:
                d = self.recieve_message()
                if d is None:
                    continue
                if d['MSG'] == 'REFUSE':
                    self._state = 0
                    self._conn = None
                    return None
                elif d['MSG'] == 'OK':
                    break
            self._pid = d['PID']
            print('add into the game successfully')
            msgs['CMD'] = 'Joined'
            msgs['PID'] = d['PID']
            self._state = 1
            self.send_message(msgs)
            thd = Thread(target=PlayerClient.wait_for_start, args=(p,))
            thd.start()


    def ready_for_game(self):
        msgs = {'CMD': 'READY'}
        self.send_message(msgs)

    def initial_player_balls(self):
        for pid in self._playerlist:
            self.board.generate_player_balls(pid)

    @staticmethod
    def wait_for_start(p):
        while True:
            d = p.recieve_message()
            if d is None:
                continue
            print(f"Received data: {d}")  # 添加调试输出
            if 'MSG' in d and d['MSG'] == 'NEW':
                p._playerlist = d['PList']
                p.initial_player_balls()
            elif 'MSG' in d and d['MSG'] == 'RESP_READY':
                p._state = 2
            elif 'MSG' in d and d['MSG'] == 'START':
                p._state = 3
                dct = {'CMD': 'RESP_START'}
                p.send_message(dct)
                break
        thd = Thread(target=PlayerClient.game_loop, args=(p,))
        thd.start()

    def send_move_command(self, ball_id, new_pos):
        curb = self.board.get_selected_ball()
        if curb:
            curb.moveto(new_pos)  # 在客户端直接调用 moveto 方法，进行位置更新
            move_msg = {
                'CMD': 'MOVE',
                'BALL_ID': ball_id,
                'NEW_POS': new_pos
            }
            self.send_message(move_msg)

    def recieve_message(self):
        data = self._conn.recv(1024).decode('utf-8')
        if data is None or data == '':
            return None
        dct = {}
        for s in data.split('\n'):
            if s != '':
                dct.update(ast.literal_eval(s))
        if 'CMD' in dct and dct['CMD'] == 'MOVE':
            self.handle_ball_move(dct)
        return dct

    def handle_ball_move(self, d):
        pid = d['PID']
        ball_id = d['BALL_ID']
        new_pos = d['NEW_POS']
        self.board.move_ball(pid, ball_id, new_pos)
        self.board.increment_move_count()  # 更新移动计数器
        if self.board.check_for_victory(pid):  # 胜利检测
            self.handle_victory()

    def handle_victory(self):
        print(f"Player {self._pid} wins!")  # 可以根据需要更改为其他胜利处理逻辑
        # 例如，向服务器发送胜利消息或更新界面
        self._state = 4  # 假设状态4表示游戏结束

    @staticmethod
    def game_loop(p):
        while True:
            d = p.recieve_message()

            print("hello",d)
            pass


p = PlayerClient()
p.show_board()