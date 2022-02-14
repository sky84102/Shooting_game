import pygame
from pygame.locals import *
import numpy as np
import sys
import csv
import time

## 最初の設定
pygame.init() # 初期化
clock = pygame.time.Clock()
pygame.mixer.init(frequency=44100)
pygame.display.set_mode((1280, 960)) # ウィンドウサイズの指定
screen = pygame.Surface((1280, 960), 0) # システム内サイズの指定 pygame.SRCALPHA
pygame.display.set_caption("Shooting Game") # タイトルの指定
bg = pygame.image.load("img/bg.png").convert_alpha() # 背景画像の指定
rect_bg = bg.get_rect() # 画像のサイズ取得
(x_min, x_max, y_min, y_max) = (41, 711, 31, 925) # player可動域 670*891
font = pygame.font.Font(None, 45) # フォントの設定(px)
font_title = pygame.font.Font(None, 70) # フォントの設定(px)
starttime = time.time()
start_select = 0 # スタート画面の位置 6以上でキー停止


# フラグ関係
dispmode = 0 # 画面モード 0: スタート画面、1: ゲーム、2: スコア表示、3: スコア入力
globaltime, elapsedtime = 0, 0 # 経過時間(elapsedtimeは被弾中停止)
clear_flag, moveflag = 0, 1
boss_callflag = 0 # ボスが居るかどうか
hit_flag = 0 # 敵に弾があたっているかどうか
rand = np.random.rand(50) # 乱数
enemy_list, enemy_died, bullet_list, shot, item = [], [], [], [], [] # 各オブジェクトを入れる配列

# 音楽データの読み込み
death_sound = pygame.mixer.Sound("se/char_death.wav")
hit_sound = pygame.mixer.Sound("se/hit.wav")
bomb_sound = pygame.mixer.Sound("se/bom0.wav")
enemy_shot_sound = pygame.mixer.Sound("se/enemy_shot.wav")
item_get_sound = pygame.mixer.Sound("se/item_get.wav")
boss_change_sound = pygame.mixer.Sound("se/boss_change.wav")

# キー設定
key_left, key_right, key_up, key_down = K_LEFT, K_RIGHT, K_UP, K_DOWN
key_shot, key_bomb, key_slow = K_z, K_x, K_LSHIFT
pygame.key.set_repeat(500, 10)



# キャラクターの設定
class Character():
    def __init__(self, kind):
        self.kind = kind
        self.power = 1.0 # パワー
        self.maxpower = 6.0
        self.decreasepower = 1.0
        self.poweritem = 0
        self.greenitem = 0
        self.score = 0 # スコア
        self.life = [9999, 3, 3][self.kind] # 残機数
        self.bomb_default = [99, 2, 2][self.kind] # 初期ボム数
        self.bomb = self.bomb_default
        self.bomb_state = 0 # ボム使用状態かどうか
        self.invincible = 0 # 無敵状態とカウント(正:無敵、負:喰らいボム)
        self.kuraitime = 12 # 喰らいボム受付時間
        self.x_def, self.y_def = (x_min + x_max)/2, y_max - 30 # 自機の初期座標
        self.x, self.y = self.x_def, self.y_def # 自機の現在の座標
        self.r = 4.1 if self.kind != 2 else 3.5
        self.difficulty = 1
        self.direction = 0
        self.graze = 0

        # 画像
        self.imgpath = "img/player0.png"
        self.player_imgList = []
        self.player_img_all = pygame.image.load(self.imgpath).convert_alpha()
        for j in range(0, 219, 73):
            for i in range(0, 292, 73):
                surface = pygame.Surface((73,73))
                surface.blit(self.player_img_all, (0,0), (i,j,73,73))
                surface.set_colorkey(surface.get_at((0,0)), RLEACCEL)
                surface.convert()
                self.player_imgList.append(surface)
        self.player_img = self.player_imgList[4] # 画像
        self.rect_player = self.player_img.get_rect() # 画像の大きさ
        self.player_alphaimg = pygame.image.load("img/player_alpha.png").convert_alpha()

    def move(self): # 移動処理
        # 被弾していないとき
        if(self.invincible >= 0):
            pressed_key = pygame.key.get_pressed()
            move_x, move_y = 0, 0
            distance = 7
            if pressed_key[key_slow]:
                distance = 3
            if pressed_key[key_left]:
                move_x = -distance
            elif pressed_key[key_right]:
                move_x = distance
            if pressed_key[key_up]:
                move_y = -distance
            elif pressed_key[key_down]:
                move_y = distance
            if(move_x != 0 and move_y != 0):
                move_x /= 2**0.5
                move_y /= 2**0.5
            new_x, new_y = self.x + move_x, self.y + move_y
            self.x = min(max(x_min+73//7, new_x), x_max-73//7)
            self.y = min(max(y_min+73//3, new_y), y_max-73//3)

        # 被弾したとき
        elif(self.invincible + self.kuraitime <= 0 or self.bomb == 0):
            self.x, self.y = self.x_def, self.y_def
            self.life -= 1 # ライフ減少
            if(self.difficulty == 1):
                self.poweritem = max(self.poweritem-self.decreasepower*100, -(self.graze//50 + self.greenitem//200) - 100)
            elif(self.difficulty == 2):
                self.poweritem = max(self.poweritem-self.decreasepower*100, -(self.graze//20 + self.greenitem//100) - 100)
            if(self.life < 0):
                global dispmode, start_select, enemy_list, bullet_list, str_position
                dispmode = 0
                start_select += 6*60
                str_position = 0
                pygame.mixer.music.fadeout(100)
                enemy_list.clear()
            self.bomb = self.bomb_default # ボムを初期に戻す
            bullet_list.clear() # 画面上のたまを消す
            death_sound.play()  # サウンドを再生
            self.invincible = 240 # 無敵時間
        self.rect_player.center = (int(self.x), int(self.y)) # 座標更新

        # 点滅動作
        if((self.invincible % 4 == 1 and self.invincible <= 36) or (self.invincible % 6 == 1 and self.invincible >= 36)):
            self.player_img = self.player_alphaimg
        else:
            self.player_img = self.player_imgList[(elapsedtime//8)%4 + self.direction*4] # アニメーション
            
        # 無敵 or 被弾カウントを減らす
        if(self.invincible != 0):
            self.invincible -= 1
        if(self.difficulty == 1):
            self.power = round(min(self.poweritem/100 + self.graze//50/100 + self.greenitem//200/100 + 1, self.maxpower), 2)
        elif(self.difficulty == 2):
            self.power = round(min(self.poweritem/100 + self.graze//20/100 + self.greenitem//100/100 + 1, self.maxpower), 2)



# ショット
s_imageList = []
for i in range(6):
    img_all = pygame.image.load("img/shot" + str(i) + ".png").convert_alpha() # 画像
    s_imageList.append(img_all)

class Shot():
    def __init__(self, x, y, angle, speed, power, kind, penetrate):
        self.flag = 1
        self.angle = angle
        self.speed = speed
        self.x, self.y = x, y
        self.power = power
        self.defaultpower = power
        self.kind = kind
        self.size = [0, 3, 2, 12, 2, 51][kind]
        self.penetrate = penetrate # 貫通
        self.img = s_imageList[self.kind]
        self.time = 0
        self.count = 0

    def changestate(self): # 座標計算と敵被弾判定
        global x_min, x_max, y_min, y_max, hit_flag
        if(player.invincible >= 0):
            if(self.kind == 2): # kind=2でホーミング
                tmp_matrix = [120000, 0, 0] # 最も近い敵[距離2乗, x, y]
                for i in enemy_list:
                    r = (i.x - self.x)**2 + (i.y - self.y)**2
                    if((tmp_matrix[0] > r) and (i.r > 0)):
                        tmp_matrix = [r, i.x, i.y]
                if(tmp_matrix[0] != 120000):
                    angle_line = np.degrees(np.arctan2(self.y-tmp_matrix[2], tmp_matrix[1]-self.x))
                    if(angle_line<0):
                        angle_line += 360
                    if(angle_line - self.angle > 180):
                        angle_line -= 360
                    elif(angle_line - self.angle < -180):
                        angle_line += 360
                    self.angle = (self.angle + angle_line * (4500/tmp_matrix[0]+0.01)) / (1+4500/tmp_matrix[0]+0.01)
            # elif(self.kind == 3): # kind=3で貫通ホーミング
            #     tmp_matrix = [270000, 0, 0] # 最も近い敵[距離2乗, x, y]
            #     for i in enemy_list:
            #         r = (i.x - self.x)**2 + (i.y - self.y)**2
            #         if((tmp_matrix[0] > r) and (i.r > 0)):
            #             tmp_matrix = [r, i.x, i.y]
            #     if(tmp_matrix[0] != 270000):
            #         angle_line = np.degrees(np.arctan2(self.y-tmp_matrix[2], tmp_matrix[1]-self.x))
            #         if(angle_line<0):
            #             angle_line += 360
            #         if(angle_line - self.angle > 180):
            #             angle_line -= 360
            #         elif(angle_line - self.angle < -180):
            #             angle_line += 360
            #         if(self.time <= 60):
            #             self.angle = (self.angle + angle_line * (min(0.053-self.time/1300, 1/(tmp_matrix[0]+0.001)**0.5+0.022))) / (1+min(0.053-self.time/1300, 1/(tmp_matrix[0]+0.001)**0.5+0.022))
            #             self.img = pygame.transform.rotate(s_imageList[self.kind], self.angle-90)

            elif(self.kind == 5): # kind=5でホーミング
                tmp_matrix = [800000, 0, 0] # 最も近い敵[距離2乗, x, y]

                if(self.time == 0):
                    self.speed *= 10
                elif(self.time < 120):
                    if(self.time == 2):
                        self.speed /= 10
                        self.angle = (self.angle + 90)%360
                    elif(self.time < 90):
                        self.angle = (self.angle + 360/40/np.pi)%360
                    else:
                        self.angle = (self.angle + 360/50/np.pi)%360

                for i in enemy_list:
                    r = (i.x - self.x)**2 + (i.y - self.y)**2
                    if((tmp_matrix[0] > r) and (i.r > 0)):
                        tmp_matrix = [r, i.x, i.y]
                if(tmp_matrix[0] != 800000):
                    angle_line = np.degrees(np.arctan2(self.y-tmp_matrix[2], tmp_matrix[1]-self.x))
                    if(angle_line<0):
                        angle_line += 360
                    if(angle_line - self.angle > 180):
                        angle_line -= 360
                    if(angle_line - self.angle < -180):
                        angle_line += 360

                    if(self.time >= 120):
                        self.angle = ((self.angle + angle_line * (0.038)) / (1+0.038))%360
                if(80<=self.time):
                    self.speed *= 0.998

                if(self.count < 40):
                    self.img = pygame.transform.rotozoom(s_imageList[self.kind], 0, (50-self.count)/50)
                    self.size = (51-self.count)
                    self.power = self.defaultpower * (50-self.count) / 50
                else:
                    self.flag = 0
                if(self.time > 480):
                    self.count += 1

            elif(self.kind == 1):
                if(self.time == 0):
                    self.img = pygame.transform.rotate(s_imageList[self.kind], self.angle-90)

            self.vx = self.speed * np.cos(np.radians(self.angle))
            self.vy = -self.speed * np.sin(np.radians(self.angle))
            break_flag = 0
            x_dat, y_dat = self.x, self.y
            num = int(self.speed // 10 + 1)
            for i in range(num):
                x_dat += self.vx / num
                y_dat += self.vy / num
                for j in range(len(enemy_list)):
                    if((enemy_list[j].r + self.size >= ((enemy_list[j].x-x_dat) ** 2 + ((enemy_list[j].y-y_dat)*1.2) ** 2) ** 0.5) and (enemy_list[j].r > 0)):
                        # if(player.bomb_state==0):
                        if(enemy_list[j].time >= enemy_list[j].barriertime):
                            enemy_list[j].hp -= self.power
                        else:
                            enemy_list[j].hp -= self.power / 50
                        if(self.kind == 5):
                            self.count += 1
                        hit_flag = 1

                        self.power *= self.penetrate # 貫通
                        if(self.penetrate == 0):
                            break_flag = 1
                            x_dat -= self.vx / num
                            y_dat -= self.vy / num
                            break
                if(self.kind == 5):
                    remove_flag = []
                    for j in range(len(bullet_list)):
                        if((bullet_list[j].flag > 0) and (bullet_list[j].size + self.size >= ((bullet_list[j].x-x_dat) ** 2 + ((bullet_list[j].y-y_dat)*1.2) ** 2) ** 0.5)):
                            remove_flag.append(bullet_list[j])
                            item.append(Item(2, bullet_list[j].x, bullet_list[j].y, 1, -25))
                    for k in remove_flag:
                        bullet_list.remove(k)
            self.x, self.y = x_dat, y_dat
            self.time += 1

def shot_act():
    global player, globaltime
    x, y = player.x, player.y
    if(pygame.key.get_pressed()[key_shot] and player.invincible >= 0 and globaltime >= 2):
        num = int(round(player.power, 2))
        if(pygame.key.get_pressed()[key_slow]):
            shot.append(Shot(x-10, y+15, 90, 70, 37-num*1, 0, 0))
            shot.append(Shot(x+10, y+15, 90, 70, 37-num*1, 0, 0))
        else:
            shot.append(Shot(x-12, y+15, 90.3, 55, 38-num*2, 0, 0))
            shot.append(Shot(x+12, y+15, 89.7, 55, 38-num*2, 0, 0))

        if(player.kind == 2):
            if(pygame.key.get_pressed()[key_slow]): # 低速 計74 - 80:72+8 - 85.5:70+15.5 - 90.5:68+22.5 - 95:66+29 - 99:64+35 - 102.5:62+40.5
                if(globaltime%8 == 0):
                    for i in range(num):
                        shot.append(Shot(x+40*np.cos(np.pi*(i+1)/(num+1)), y+28*np.sin(np.pi*(i+1)/(num+1)), 90+(i+0.5-num/2)/num*10, 8.4, (8.25-num/4)*8, 2, 0))
                        
            else: # 高速 計76 - 83:72+11 - 89:68+21 - 94:64+30 - 98:60+38 - 101:56+45 - 103:52+51
                if(globaltime%8 == 0):
                    for i in range(num):
                        shot.append(Shot(x+42*np.cos(np.pi*4/3*(i+1)/(num+1)-np.pi/6), y+32*np.sin(np.pi*4/3*(i+1)/(num+1)-np.pi/6), 90+(i+0.5-num/2)/num*30, 8.1, (11.5-num/2)*8, 2, 0))
        
        elif(player.kind == 3):
            if(pygame.key.get_pressed()[key_slow]): # 低速 計74 - 80:72+8 - 85.5:70+15.5 - 90.5:68+22.5 - 95:66+29 - 99:64+35 - 102.5:62+40.5
                if(globaltime%8 == 0):
                    # for i in range(num):
                        # shot.append(Shot(x+40*np.cos(np.pi*(i+1)/(num+1)), y+28*np.sin(np.pi*(i+1)/(num+1)), 90+(i+0.5-num/2)/num*10, 8.4, (8.25-num/4)*8, 2, 0))
                    if((num>=1)):
                        shot.append(Shot(x-30, y-15, 90, 10.0, (8.25-num/4)*num*0.96, 3, 0.8))
                        shot.append(Shot(x+30, y-15, 90, 10.0, (8.25-num/4)*num*0.96, 3, 0.8))

        elif(player.kind == 1):
            if(pygame.key.get_pressed()[key_slow]): # 低速 計74 - 92:72+20 - 100:70+30 - 106:68+38 - 114:66+48 - 120:64+56 - 128:62+66
                if((num>=1)):
                    shot.append(Shot(x-15, y+5, 91, 105, 3+(num//2)*1, 1, 0)) # 0 3 4 4 5 5 6
                    shot.append(Shot(x  , y+25, 90, 105, 6+num*8, 1, 0)) # 0 14 22 30 38 46 54
                    shot.append(Shot(x+15, y+5, 89, 105, 3+(num//2)*1, 1, 0)) # 0 3 4 4 5 5 6
            else: # 高速 計76 - 110:72+38 - 119:68+51 - 128:64+64 - 137:60+77 - 146:56+90 - 155:52+103
                if((num>=1)):
                    shot.append(Shot(x-12, y+5, 98, 84, 7+num*1, 1, 0)) # 0 8 9 10 11 12
                    shot.append(Shot(x+12, y+5, 82, 84, 7+num*1, 1, 0))
                    shot.append(Shot(x-30, y+15, 86, 70, 5.5+num*5.5, 1, 0)) # 0 11 16.5 22 27.5 33 38.5
                    shot.append(Shot(x+30, y+15, 94, 70, 5.5+num*5.5, 1, 0))

    remove_flag = []
    for i in range(len(shot)):
        shot[i].changestate() # ショットの更新
        if(shot[i].flag == 1):
            # shot_image = shot[i].img.convert_alpha()
            shot_image = shot[i].img
            rect_shot = shot_image.get_rect()
            rect_shot.center = (int(shot[i].x), int(shot[i].y))
            screen.blit(shot_image, rect_shot)
            if(shot[i].x < x_min-75 or shot[i].x > x_max+75 or shot[i].y < y_min-75 or shot[i].y > y_max+325):
                shot[i].flag = 0
        if(shot[i].flag == 0):
            remove_flag.append(shot[i])
        elif(shot[i].power == 0):
            shot[i].flag = 0
    global hit_flag, elapsedtime
    if((hit_flag == 1) and (globaltime%8 == 0)):
        hit_sound.play()
        hit_flag = 0
    for i in remove_flag:
        shot.remove(i)

    # ボム
    if(pygame.key.get_pressed()[key_bomb] and player.bomb_state == 0 and player.bomb >= 1 and player.invincible <= 10):
        player.bomb_state = 85
        if(player.kind == 1):
            player.invincible = 240
        elif(player.kind == 2):
            player.invincible = 510
        player.bomb -= 1
        bonusflag = 0
        bomb_sound.play()
        for i in range(len(item)):
            item[i].state = 1
        if(player.kind == 2):
            for i in range(6):
                shot.append(Shot(x, y, 60*i, 6.0, 360, 5, 1))
    elif((player.bomb_state == 5) and (player.kind == 1)):
        player.bomb_state -= 1
        for j in bullet_list:
            item.append(Item(2, j.x, j.y, 1, -25))
        bullet_list.clear()
        item_get_sound.play()
        player.bomb_state -= 1
        bullet_list.clear()
        item_get_sound.play()

    elif(player.bomb_state > 0):
        player.bomb_state -= 1
        if(player.kind == 2):
            elapsedtime += 1
    if(player.kind == 1 and 1 <= player.bomb_state < 5):
        for i in enemy_list:
            if(i.r != 0):
                i.hp -= 7000/4



# アイテム
i_imageList = []
for i in range(5):
    img_all = pygame.image.load("img/item" + str(i) + ".png").convert_alpha() # 画像
    i_imageList.append(img_all)

class Item():
    def __init__(self, kind, x_in, y_in, state, time=0):
        self.x, self.y = x_in, y_in # 座標
        self.state = state
        self.kind = int(kind) # 弾の種類
        self.vx, self.vy = 0, -1.5 # 速度
        self.ay = 0
        self.flag = 1 # フラグ
        self.img = i_imageList[self.kind]
        self.time = time
            
    def changestate(self):
        if(self.kind == 2):
            self.vy = -0.2
        elif(player.y <= 280):
            self.state = 1
        elif(player.invincible < 0):
            self.state = 0
        
        x_diff = player.x - self.x
        y_diff = player.y - self.y
        if(x_diff ** 2 + y_diff ** 2 <= 25 ** 2):
            if(self.kind == 0 and player.power < player.maxpower): # パワーアイテム
                player.poweritem += 1
                item_get_sound.play()
            # elif(self.kind == 0 or self.kind == 1): # 得点アイテム
                # player.score += int(player.point)
                # item_get_sound.play()
            elif(self.kind == 2): # みどり点
                player.greenitem += 1
            elif(self.kind == 3 and player.power < player.maxpower): # 大パワーアイテム
                player.poweritem += 10
                item_get_sound.play()
            elif(self.kind == 4): # ボム
                player.bomb += 1
            self.flag = 0
        elif(x_diff**2 + y_diff**2 <= 60**2 or (pygame.key.get_pressed()[key_slow] and x_diff**2 + y_diff**2 <= 100**2)):
            self.vx = x_diff / (x_diff ** 2 + y_diff ** 2) ** 0.5 * 12
            self.vy = y_diff / (x_diff ** 2 + y_diff ** 2) ** 0.5 * 12
            self.ay = 0

        elif((self.state == 1) and (self.time >= 0)):
            # 自機に集める
            self.vx = x_diff / (x_diff ** 2 + y_diff ** 2) ** 0.5 * 12
            self.vy = y_diff / (x_diff ** 2 + y_diff ** 2) ** 0.5 * 12
            self.ay = 0
        elif(self.state == 0):
            self.ay = 0.026 if self.vy < 2.6 else 0
        if(player.invincible >= 0):
            self.x += self.vx
            self.vy += self.ay
            self.y += self.vy
            self.time += 1

# 全部のアイテムの移動処理
def item_act():
    remove_flag = []
    for i in range(len(item)):
        item[i].changestate() # Itemの更新
        if(item[i].flag == 1):
            item_image = item[i].img
            # item_image = item[i].img.convert_alpha()
            rect_item = item_image.get_rect()
            rect_item.center = (int(item[i].x), int(item[i].y)) # 描画用のアイテムの座標を更新
            screen.blit(item_image, rect_item) # アイテムの描画
            if(item[i].x < x_min - 5 or item[i].x > x_max + 5 or item[i].y < y_min - 25 or item[i].y > y_max + 10):
                item[i].flag = 0
                remove_flag.append(item[i])
        else:
            remove_flag.append(item[i])
    for i in remove_flag:
        item.remove(i)




e_imageList = {}
for i in [0, 1, 2, 3, 11]:
    img_all = pygame.image.load("img/enemy" + str(i) + ".png").convert_alpha() # 画像
    e_imageList[i] = []
    width, height = img_all.get_size()
    for k in range(0, height, int(height/3)):
        for m in range(0, width, int(width/3)):
            surface = pygame.Surface((int(width/3),int(height/3)))
            surface.blit(img_all, (0,0), (m,k,int(width/3),int(height/3)))
            surface.set_colorkey(surface.get_at((0,0)), RLEACCEL)
            surface.convert()
            e_imageList[i].append(surface)
# 敵
class Enemy():
    global e_imageList
    def __init__(self, appeartime, id_in, x_in, y_in, r_in, kind, hp_max, barriertime, actdict="", bulletdict=""):
        self.appeartime = appeartime # (正で出現時間、負で従属先id)
        self.id = id_in # id(倒されるときに次の敵を呼ぶための変数)
        self.x, self.y, self.r = x_in, y_in, r_in # 座標
        self.vx, self.vy, self.ax, self.ay, self.direction = 0, 0, 0, 0, 1 # 速度, 向き
        self.angle_flag, self.angle, self.dangle, self.speed = 0, 0, 0, 0 # 角座標
        self.time, self.truetime = 0, 0 # 出現からの時間
        self.barriertime = barriertime
        self.flag = 1 # フラグ
        self.hp, self.hp_max = hp_max, hp_max
        self.kind = kind # 敵の種類
        self.bossflag = int(kind//100)
        self.barray = [] # 弾の情報を入れる配列
        self.actdict = {}
        self.bulletdict = {}
        self.item_drop = {1: 28, 0: 12} # 落とすアイテム

        if(self.bossflag == 0):
            self.img = e_imageList[self.kind][3]
        else:
            self.img = pygame.image.load("img/boss" + str(int(self.kind) % 100) + ".png")


    def changestate(self, minx, maxx, miny, maxy, player): # 動きの設定
        # if(player.invincible >= 0 and (player.bomb_state == 0 or player.kind == 1)):
        if(player.invincible >= 0):
            # 速度と弾発生フラグの設定
            if(self.time in self.actdict):
                for vary in self.actdict[self.time].items():
                    if(type(vary[1]) == str):
                        if(vary[1][0:8] == "approach"):
                            if(vary[0] == "vx"):
                                v = float(vary[1][8:]) if self.x < player.x else -float(vary[1][8:])
                            elif(vary[0] == "vy"):
                                v = float(vary[1][8:]) if self.y < player.y else -float(vary[1][8:])
                            else:
                                v = 0
                            exec("self.{} = {}".format(vary[0], v))
                        elif(vary[1][0:4] == "rand"):
                            v = float(vary[1][4:])*(np.random.rand()-0.5)
                            exec("self.{} = {}".format(vary[0], v))
                    else:
                        exec("self.{} = {}".format(vary[0], vary[1]))
            if((self.time + 1) in self.bulletdict):
                for vary in self.bulletdict[(self.time+1)].items():
                    self.barray.append([(self.time+1)] + vary[1])

            # 角座標フラグの確認
            if(self.angle_flag == 1):
                self.vx = self.speed * np.cos(np.radians(self.angle))
                self.vy = -self.speed * np.sin(np.radians(self.angle))
                self.angle += self.dangle
            else:
                self.vx += self.ax
                self.vy += self.ay
            self.x += self.vx
            self.y += self.vy
            self.x = min(maxx-self.r/2, max(minx+self.r/2, self.x)) if self.bossflag>0 else self.x
            self.y = min((maxy-miny)*0.9-self.r/2, max(miny+self.r/2, self.y)) if (self.bossflag>0 and self.r > 0) else self.y

            if(self.bossflag == 0):
                self.img = e_imageList[self.kind][(self.time//10)%3+3*self.direction] # 敵のアニメーション
                
            self.time += 1
            self.truetime += 1


# 死んだあとの敵        
class DiedEnemy():
    def __init__(self, x_in, y_in):
        self.x, self.y, self.time = x_in, y_in, 15
    
    def changestate(self): # 動きの設定
        self.time -= 1



# 弾
b_imageList = []
b_colarray = [5, 9, 10, 8, 6, 9, 9, 3]
b_size = [8, 4, 6, 2, 9, 16, 4, 4]
for i, j in enumerate(b_colarray):
    img_all = pygame.image.load("img/bullet" + str(i) + ".png").convert_alpha() # 画像
    b_imageList.append([])
    width, height = img_all.get_size()
    for k in range(0, width, int(width/j)):
        surface = pygame.Surface((int(img_all.get_size()[0]/b_colarray[i]), int(img_all.get_size()[1])))
        surface.blit(img_all, (0,0), (k, 0, int(img_all.get_size()[0]/b_colarray[i]), img_all.get_size()[1]))
        surface.set_colorkey(surface.get_at((0,0)), RLEACCEL)
        surface.convert()
        b_imageList[i].append(surface)


class Bullet():
    global b_imageList, b_colarray, b_size
    def __init__(self, kind, enemy_x, enemy_y, player_x, player_y, pattern, speed, actdict=""):
        self.x, self.y = enemy_x, enemy_y # 座標

        def bullet_pattern(pattern, x_in, y_in, player_x, player_y): # pattern: n(種類).xxx(角度)、speed: v.v(速度)ww(加速度 1:加速 2:減速)
            angle = 0
            if(0 <= pattern < 1): # 方向固定
                # angle = int(pattern * 1000)
                angle = int(pattern * 10000) / 10
            if(pattern >= 1): # 自機依存
                if(player_x-x_in != 0):
                    angle = np.rad2deg(np.arctan(-(player_y-y_in) / (player_x-x_in)))
                else:
                    angle = 90 if (player_y-y_in < 0) else 270
                if(player_x-x_in < 0):
                    angle += 180
                angle += int((pattern-1) * 1000)
            return angle

        self.angle, self.speed = bullet_pattern(pattern, enemy_x, enemy_y, player_x, player_y), speed # 方向、速度
        self.angle_flag = 1
        self.vx, self.vy, self.ax, self.ay = 0, 0, 0, 0 # 速度
        self.dangle, self.dspeed = 0, 0
        self.kind = int(kind) # 弾の種類
        self.color = int(round((kind - int(kind)) * 10, 1))
        self.flag = 1 # フラグ 2で反射, 3で瞬間時期狙い
        self.time = 0
        self.grazeflag = 1
        self.actdict = {}
        exec("self.actdict.update({})".format(actdict))
        if(self.kind in [1, 6, 7, 8]):
            self.img = pygame.transform.rotate(b_imageList[self.kind][self.color], self.angle+90)
        else:
            self.img = b_imageList[self.kind][self.color]
        self.size = b_size[self.kind]


    # 動きの設定
    def changestate(self, minx, maxx, miny, maxy, player):
        if(player.invincible >= 0 and (player.bomb_state==0 or player.kind==2)):
            # 速度と弾発生フラグの設定
            if(self.time in self.actdict):
                for vary in self.actdict[self.time].items():
                    exec("self.{} = {}".format(vary[0], vary[1]))
            # 角座標フラグの確認
            if(self.angle_flag == 1):
                self.vx = self.speed * np.cos(np.radians(self.angle))
                self.vy = -self.speed * np.sin(np.radians(self.angle))
                self.angle += self.dangle
                self.speed += self.dspeed
                if((self.dangle != 0) and (self.kind in [1, 6, 7, 8])):
                    self.img = pygame.transform.rotate(b_imageList[self.kind][self.color], self.angle+90)
            else:
                self.angle = np.degrees(np.arctan(self.vx/(self.vy-0.0001))) + 270
                if(self.vy < 0):
                    self.angle += 180
                # if(self.angle != 270 and self.kind in [1, 6, 7, 8]):
                #     self.img = pygame.transform.rotate(b_imageList[self.kind][self.color], self.angle+90)
                
            self.vx += self.ax
            self.vy += self.ay
            self.x += self.vx
            self.y += self.vy

            # 反射の設定
            """
            2: 上左右で反射
            2.1: 上左右で反射(1回だけ)
            2.5: 上左右で確率反射
            """
            if((self.flag == 2) or (self.flag == 2.1) or (self.flag == 2.5 and np.random.rand()<0.6)):
                if(self.x > maxx):
                    self.x = maxx * 2 - self.x
                    self.vx = -self.vx
                    if(self.flag == 2.5):
                        self.ay = 0.015
                        self.vy = (np.random.rand()+0.2) * 0.83
                        self.vx = self.vx * (np.random.rand()+0.2) * 0.4
                    elif(self.flag == 2.1):
                        self.flag = 1
                elif(self.x < minx):
                    self.x = minx * 2 - self.x
                    self.vx = -self.vx
                    if(self.flag == 2.5):
                        self.ay = 0.015
                        self.vy = (np.random.rand()+0.2) * 0.83
                        self.vx = self.vx * (np.random.rand()+0.2) * 0.4
                    elif(self.flag == 2.1):
                        self.flag = 1
                if(self.y < miny):
                    self.y = miny * 2 - self.y
                    self.vy = -self.vy
                    if(self.flag == 2.5):
                        self.ay = 0.015
                        self.vy *= 0.5
                        self.vx = self.vx * np.random.rand() * 0.7
                    elif(self.flag == 2.1):
                        self.flag = 1
                
            elif(self.flag == 2.5):
                if(self.x > maxx or self.x < minx or self.y < miny):
                    self.flag = 1

            # 時間経過後の自機狙い
            if(self.flag == 3):
                if(player.x-self.x != 0):
                    angle = np.rad2deg(np.arctan(-(player.y-self.y) / (player.x-self.x)))
                else:
                    angle = 90 if (player.y-self.y < 0) else 270
                if(player.x-self.x < 0):
                    angle += 180
                self.angle = angle # 方向
                self.flag = 1
                if(self.angle != 270 and self.kind in [1, 6, 7, 8]):
                    self.img = pygame.transform.rotate(b_imageList[self.kind][self.color], self.angle+90)

            self.time += 1
        elif((player.bomb_state > 5) and (player.kind == 1) and (self.color != b_colarray[self.kind] - 1)):
            self.color = b_colarray[self.kind] - 1
            if(self.kind in [1, 6, 7, 8]):
                self.img = pygame.transform.rotate(b_imageList[self.kind][self.color], self.angle+90)
            else:
                self.img = b_imageList[self.kind][self.color]
        if(self.time > 0 and player.r + self.size >= ((self.x-player.x) ** 2 + (self.y-player.y) ** 2) ** 0.5 and player.invincible == 0):
            player.invincible = -1
        elif(player.r + self.size + 28 >= ((self.x-player.x) ** 2 + (self.y-player.y) ** 2) ** 0.5  and self.grazeflag == 1):
            player.graze += 1
            if(player.power == player.maxpower):
                if(player.difficulty == 1):
                    player.poweritem = int(player.maxpower * 100 - 100 - player.graze//50 - player.greenitem//200)
                elif(player.difficulty == 2):
                    player.poweritem = int(player.maxpower * 100 - 100 - player.graze//20 - player.greenitem//100)
            self.grazeflag = 0
            # self.img = pygame.transform.rotate(b_imageList[self.kind][-1], self.angle+90)



def enemy_act():
    global boss_callflag, item, clear_flag, player, bullet_list
    remove_flag = []

    for i in range(len(enemy_list)):
        enemy_list[i].changestate(x_min, x_max, y_min, y_max, player) # Enemyの更新
        if(enemy_list[i].flag == 1):
            enemy_image = enemy_list[i].img.convert_alpha()
            rect_enemy = enemy_image.get_rect()
            rect_enemy.center = (int(enemy_list[i].x), int(enemy_list[i].y)) # 描画用の敵の座標を更新
            screen.blit(enemy_image, rect_enemy) # 敵の描画
            if(enemy_list[i].bossflag == 1):
                pygame.draw.rect(screen, (255,85,42), (45,35,int(660*enemy_list[i].hp/enemy_list[i].hp_max),5)) # HPバーの表示

            # pygame.draw.ellipse(screen, (255,255,0), (int(round((enemy_list[i].x-enemy_list[i].r))),int(round(enemy_list[i].y-enemy_list[i].r/2)), enemy_list[i].r*2, enemy_list[i].r)) # 敵当たり判定を黄色表示

            # 弾発生処理
            num = len(enemy_list[i].barray) # 配列長さの一時的変数
            bullet_create_list = []
            for j in range(len(enemy_list[i].barray)):
                if(enemy_list[i].time == enemy_list[i].barray[num-j-1][0] and len(bullet_list) < 9000):

                    if(enemy_list[i].barray[num-j-1][4] >= 2.0): # patternが2で方向固定
                        if(player.x-enemy_list[i].x != 0):
                            angle = np.rad2deg(np.arctan(-(player.y-enemy_list[i].y) / (player.x-enemy_list[i].x)))
                        else:
                            angle = 90 if (player.y-enemy_list[i].y < 0) else 270
                        if(player.x-enemy_list[i].x < 0):
                            angle += 180
                        if(angle <= 0):
                            angle += 360
                        enemy_list[i].barray[num-j-1][4] = enemy_list[i].barray[num-j-1][4]%1.0 + angle/1000
                    
                    if(len(enemy_list[i].barray[num-j-1]) == 7):
                        bullet_create_list.append(Bullet(enemy_list[i].barray[num-j-1][3], enemy_list[i].x, enemy_list[i].y, player.x, player.y, enemy_list[i].barray[num-j-1][4], enemy_list[i].barray[num-j-1][5], enemy_list[i].barray[num-j-1][6]))
                        # enemy_shot_sound.play()
                    else:
                        bullet_create_list.append(Bullet(enemy_list[i].barray[num-j-1][3], enemy_list[i].x, enemy_list[i].y, player.x, player.y, enemy_list[i].barray[num-j-1][4], enemy_list[i].barray[num-j-1][5]))
                        # enemy_shot_sound.play()
                    if(enemy_list[i].barray[num-j-1][2] == 1):
                        enemy_list[i].barray.pop(num-j-1)
                    else:
                        enemy_list[i].barray[num-j-1][0] += enemy_list[i].barray[num-j-1][1]
                        enemy_list[i].barray[num-j-1][2] -= 1
            if(len(bullet_create_list)>0):
                bullet_list = bullet_list + bullet_create_list

        if(enemy_list[i].flag == 0 or enemy_list[i].hp <= 0):
            enemy_list[i].flag == 0
            remove_flag.append(enemy_list[i])
            if(enemy_list[i].bossflag == 1):
                if((enemy_list[i].id * -1) in enemydata.keys()):
                    boss_callflag = enemy_list[i].id
                    for j, k in enemy_list[i].item_drop.items():
                        for num in range(k):
                            item_x = enemy_list[i].x + enemy_list[i].r * (np.random.rand()*2-1)
                            item_y = enemy_list[i].y + enemy_list[i].r * (np.random.rand()*2-1)
                            item.append(Item(j, item_x, item_y, 0, 0))
                else:
                    clear_flag = 1 # クリア判定
                    pygame.mixer.Sound("se/endtime.wav").play()
                    for j, k in enemy_list[i].item_drop.items():
                        for num in range(k):
                            item_x = enemy_list[i].x + enemy_list[i].r * (np.random.rand()*2-1)
                            item_y = enemy_list[i].y + enemy_list[i].r * (np.random.rand()*2-1)
                            item.append(Item(j, item_x, item_y, 1, -30))
            elif(enemy_list[i].flag == 1):
                for j, k in enemy_list[i].item_drop.items():
                    for num in range(k):
                        item_x = enemy_list[i].x + enemy_list[i].r * (np.random.rand()*2-1)
                        item_y = enemy_list[i].y + enemy_list[i].r * (np.random.rand()*2-1)
                        item.append(Item(j, item_x, item_y, 0, 0))

    for i in remove_flag:
        if(i.bossflag == 0):
            enemy_died.append(DiedEnemy(i.x, i.y))
            enemy_list.remove(i)
            if(i.hp <= 0):
                pygame.mixer.Sound("se/enemy_death.wav").play()
        else:
            for j in bullet_list:
                item.append(Item(2, j.x, j.y, 1, -12))
            bullet_list.clear()
            # item_get_sound.play()
            enemy_list.clear()


    remove_flag = []
    for i in range(len(enemy_died)):
        enemy_died[i].changestate() # Enemyの更新
        hit_effect_image = pygame.image.load("img/hit_effect.png").convert_alpha()
        rect_image = hit_effect_image.get_rect()
        rect_image.center = (enemy_died[i].x, enemy_died[i].y) # 描画用の敵の座標を更新
        screen.blit(hit_effect_image, rect_image) # エフェクトの描画
        if(enemy_died[i].time == 0):
            remove_flag.append(enemy_died[i])
    for i in remove_flag:
        enemy_died.remove(i)



                
# 弾
# 全部の弾の移動処理
def bullet_act():
    remove_flag = []
    for i in range(len(bullet_list)):
        bullet_list[i].changestate(x_min, x_max, y_min, y_max, player) # Bulletの更新
        if(bullet_list[i].flag > 0):
            bullet_image = bullet_list[i].img
            rect_bullet = bullet_image.get_rect()
            rect_bullet.center = (int(bullet_list[i].x), int(bullet_list[i].y)) # 描画用の弾の座標を更新
            screen.blit(bullet_image, rect_bullet) # 弾の描画
            # pygame.draw.circle(screen, (255,0,0), (int(round(bullet_list[i].x)),int(round(bullet_list[i].y))), int(bullet_list[i].size)) # 弾当たり判定を赤く表示
            if(bullet_list[i].x < x_min - 20 or bullet_list[i].x > x_max + 20 or bullet_list[i].y < y_min - 20 or bullet_list[i].y > y_max + 20):
                bullet_list[i].flag = 0
                remove_flag.append(bullet_list[i])
    for i in remove_flag:
        bullet_list.remove(i)




enemydata = {}
def set_enemy(difficulty):
    global enemydata
    enemydata.clear() # 初期化


    for i in range(10):
        zako = Enemy(70+i*4, 1, 376+(i-4.5)*50, 0, 20, 1, 500, 30)
        zako.item_drop = {0: 2}
        zako.actdict = {0: {"vy": 4}, 30: {"vy": abs(i-4.5)/1.2+0.5, "vx":2-(i+5.5)%10/2.75}, 80: {"vy": 0, "vx": 0}, 340: {"vx": 1.5/(i-4.5)+(i-4.5)}, 1000: {"flag": 0}}
        if(difficulty == 1):
            zako.bulletdict = {90: {"B0": [20, 240/20, 6.4, 1.0, 25.0, {1: {"speed": 2.0}, 15: {"dspeed": 0.18}}]}}
        elif(difficulty == 2):
            zako.bulletdict = {100: {"B0": [40, 240/40, 6.4, 1.0, 4.5]}}

        if(not(zako.appeartime in enemydata)):
            enemydata[zako.appeartime] = []
        enemydata[zako.appeartime].append(zako)

    for i in range(8):
        zako = Enemy(500+i*5, 1, 376+(i-3.5)*60, 0, 20, 1, 500, 30)
        zako.item_drop = {0: 2}
        zako.actdict = {0: {"vy": 4}, 30: {"vy": abs(i-3.5)/1.2+1, "vx":2-(i+4.5)%8/2}, 80: {"vy": 0, "vx": 0}, 190: {"vx": -1.5/(i-3.5)-(i-3.5)}, 1000: {"flag": 0}}
        if(difficulty == 1):
            zako.bulletdict = {90: {"B0": [20, 240/20, 6.3, 1.025, 25.0, {1: {"speed": 2.0}, 15: {"dspeed": 0.18}}], "B1": [20, 240/20, 6.3, 1.335, 25.0, {1: {"speed": 1.5}, 15: {"dspeed": 0.18}}]}}
        elif(difficulty == 2):
            zako.bulletdict = {100: {"B0": [40, 240/40, 6.4, 1.04, 4.5], "B1": [40, 240/40, 6.4, 1.32, 4.5]}}

        if(not(zako.appeartime in enemydata)):
            enemydata[zako.appeartime] = []
        enemydata[zako.appeartime].append(zako)

    for i in range(4):
        zako2 = Enemy(1020+i**2*9, 1, 376+350-i*10, 49+i*30, 40, 2, 4000, 90)
        zako2.item_drop = {0: 5}
        zako2.actdict = {0: {"angle_flag": 1, "angle": 190, "speed": 1.5}, 450: {"ax": -0.004}, 1200: {"flag": 0}}
        for i in [120, 180, 240, 300, 360]:
            zako2.actdict.update({i:{"angle_flag": 0, "vx": "rand0.8", "ax":-0.008}})
        if(difficulty == 2):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.4, (n/11*360+m/5)%1000/1000+0.001, 50, {1: {"speed": 4.1, "dspeed": -0.038}, 70: {"dspeed":0}}] for n in range(11)} for m in range(80, 720, 80)}
        elif(difficulty == 1):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.4, (n/22*360+m/5)%1000/1000+0.001, 55, {1: {"speed": 4.9, "dspeed": -0.05}, 70: {"dspeed":0}}] for n in range(22)} for m in range(80, 740, 60)}
        if(not(zako2.appeartime in enemydata)):
            enemydata[zako2.appeartime] = []
        enemydata[zako2.appeartime].append(zako2)

    for i in range(4):
        zako2 = Enemy(1440+i**2*9, 1, 376-350+i*10, 49+i*30, 40, 2, 4000, 90)
        zako2.item_drop = {0: 5}
        zako2.actdict = {0: {"angle_flag": 1, "angle": 350, "speed": 1.5}, 450: {"ax": 0.004}, 1200: {"flag": 0}}
        for i in [120, 180, 240, 300, 360]:
            zako2.actdict.update({i:{"angle_flag": 0, "vx": "rand0.8", "ax":0.008}})
        if(difficulty == 2):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.0, (n/11*360+m/5)%1000/1000+0.001, 50, {1: {"speed": 4.1, "dspeed": -0.038}, 70: {"dspeed":0}}] for n in range(11)} for m in range(80, 720, 80)}
        elif(difficulty == 1):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.0, (n/22*360+m/5)%1000/1000+0.001, 55, {1: {"speed": 4.9, "dspeed": -0.05}, 70: {"dspeed":0}}] for n in range(22)} for m in range(80, 740, 60)}
        if(not(zako2.appeartime in enemydata)):
            enemydata[zako2.appeartime] = []
        enemydata[zako2.appeartime].append(zako2)

    for i in range(3):
        zako3 = Enemy(2140+i*730, 1, 136+(400+160*i)%480, 0, 50, 3, 30000, 60)
        zako3.item_drop = {0: 17}
        zako3.actdict = {0: {"vy": 4.5}, 50: {"vy": 0}, 650: {"vy": -5}, 750: {"flag": 0}}
        if(difficulty == 2):
            zako3.bulletdict = {m: {"B"+str(n): [0, 1, round(2.1+n//6/10,1), (0.0+m/1000+n*0.06)%0.72, 50, {1: {"speed": 0, "dangle": 80*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 3.2}}] for n in range(12)} for m in range(60, 620, 10)}
            zako3.bulletdict.update({m+1: {"B"+str(n): [0, 1, round(0.1+n//6/10,1), (0.03+m/1000+n*0.06)%0.72, 55, {1: {"speed": 0, "dangle": -80*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 2.8}}] for n in range(12)} for m in range(60, 620, 10)})
        elif(difficulty == 1):
            zako3.bulletdict = {m: {"B"+str(n): [0, 1, round(2.1+n//8/10,1), (m/980+n*0.045)%0.72, 50, {1: {"speed": 0, "dangle": 90*(n//8-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 4.2}}] for n in range(16)} for m in range(60, 620, 8)}
            zako3.bulletdict.update({m+1: {"B"+str(n): [0, 1, round(0.1+n//6/10,1), (0.03+m/990+n*0.06)%0.72, 55, {1: {"speed": 0, "dangle": -90*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 2.4}}] for n in range(12)} for m in range(60, 620, 8)})

        if(not(zako3.appeartime in enemydata)):
            enemydata[zako3.appeartime] = []
        enemydata[zako3.appeartime].append(zako3)

    for i in range(6):
        zako4 = Enemy(4250+(i//2)*8, 1, (i%2)*752, 200+80*(i//2), 20, 1, 500, 30)
        zako4.item_drop = {0: 2}
        zako4.actdict = {0: {"vx": (0.5-(i%2))*4.5}, 50: {"vx": 0}, 550: {"vx": ((i%2)-0.5)*12}, 800: {"flag": 0}}
        if(difficulty == 1):
            zako4.bulletdict = {90: {"B0": [20, 240/20, 6.4, 1.0, 25.0, {1: {"speed": 2.0}, 15: {"dspeed": 0.18}}]}}
        elif(difficulty == 2):
            zako4.bulletdict = {100: {"B0": [40, 240/40, 6.4, 1.0, 4.5]}}

        if(not(zako4.appeartime in enemydata)):
            enemydata[zako4.appeartime] = []
        enemydata[zako4.appeartime].append(zako4)

    zako4 = Enemy(4830, 1, 376, 0, 50, 11, 64000, 120)
    zako4.item_drop = {0: 14, 3: 2, 4: 1} # p34
    zako4.actdict = {0: {"vy": 5}, 50: {"vy": 0}, 1200: {"vy": -3.5}, 1300-1: {"flag": 0}}
    if(difficulty == 2):
        zako4.bulletdict = {m+80:{("B"+str(n)): [0, 1, round(6.0+(n%6)/10,1), (0.360+n*0.03+((-0.0045*m**2+0.8*m)%360)/1000)%0.36, 40, {1: {"speed":2.5}}] for n in range(0,12)} for m in range(0,1110,6)}
    elif(difficulty == 1):
        zako4.bulletdict = {m+80:{("B"+str(n)): [0, 1, round(6.0+(n%6)/10,1), (0.360+n*0.02+((-0.0045*m**2+0.8*m)%360)/1000)%0.36, 40, {1: {"speed":3.3}}] for n in range(0,18)} for m in range(0,1110,5)}
    if(not(zako4.appeartime in enemydata)):
        enemydata[zako4.appeartime] = []
    enemydata[zako4.appeartime].append(zako4)

    for i in range(4):
        zako2 = Enemy(6250+i**2*20, 1, 376+350-i*10, 49+i*30, 40, 2, 4000, 90)
        zako2.item_drop = {0: 5}
        zako2.actdict = {0: {"angle_flag": 1, "angle": 190, "speed": 1.5}, 1200: {"flag": 0}}
        for i in [120, 180, 240, 300, 360]:
            zako2.actdict.update({i:{"angle_flag": 0, "vx": "rand0.9", "ax":-0.005}})
        if(difficulty == 2):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.4, (n/15*360+m/5)%1000/1000+0.001, 40, {1: {"speed": 4.1, "dspeed": -0.06}, 40: {"dspeed":0}}] for n in range(15)} for m in range(80, 880, 80)}
        elif(difficulty == 1):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.4, (n/24*360+m/5)%1000/1000+0.001, 40, {1: {"speed": 4.4, "dspeed": -0.06}, 40: {"dspeed":0}}] for n in range(24)} for m in range(80, 880, 40)}
        if(not(zako2.appeartime in enemydata)):
            enemydata[zako2.appeartime] = []
        enemydata[zako2.appeartime].append(zako2)

    for i in range(4):
        zako2 = Enemy(6300+i**2*20, 1, 376-350+i*10, 49+i*30, 40, 2, 4000, 90)
        zako2.item_drop = {0: 5}
        zako2.actdict = {0: {"angle_flag": 1, "angle": 350, "speed": 1.5}, 1200: {"flag": 0}}
        for i in [120, 180, 240, 300, 360]:
            zako2.actdict.update({i:{"angle_flag": 0, "vx": "rand0.9", "ax":0.005}})
        if(difficulty == 2):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.0, (n/15*360+m/5)%1000/1000+0.001, 40, {1: {"speed": 4.1, "dspeed": -0.06}, 40: {"dspeed":0}}] for n in range(15)} for m in range(80, 880, 80)}
        elif(difficulty == 1):
            zako2.bulletdict = {m: {"B"+str(n): [1, 1, 2.0, (n/24*360+m/5)%1000/1000+0.001, 40, {1: {"speed": 4.4, "dspeed": -0.06}, 40: {"dspeed":0}}] for n in range(24)} for m in range(80, 880, 40)}
        if(not(zako2.appeartime in enemydata)):
            enemydata[zako2.appeartime] = []
        enemydata[zako2.appeartime].append(zako2)

    for i in range(2):
        zako3 = Enemy(7460, 1, 136+(400+160*i)%480, 0, 50, 3, 30000, 60)
        zako3.item_drop = {0: 17}
        zako3.actdict = {0: {"vy": 4.5}, 50: {"vy": 0}, 1350: {"vy": -5}, 1450: {"flag": 0}}
        if(difficulty == 2):
            zako3.bulletdict = {m: {"B"+str(n): [0, 1, round(2.1+i/10,1), (0.0+m/1000+n*0.06)%0.72, 50, {1: {"speed": 0, "dangle": 80*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 3.2}}] for n in range(6)} for m in range(60, 1320, 20)}
            zako3.bulletdict.update({m+1: {"B"+str(n): [0, 1, round(0.1+i/10,1), (0.03+m/1000+n*0.06)%0.72, 55, {1: {"speed": 0, "dangle": -80*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 2.8}}] for n in range(6)} for m in range(60, 1320, 15)})
        elif(difficulty == 1):
            zako3.bulletdict = {m: {"B"+str(n): [0, 1, round(2.1+i/10,1), (m/980+n*0.045)%0.72, 50, {1: {"speed": 0, "dangle": 90*(n//8-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 3.7}}] for n in range(8)} for m in range(60, 1320, 12)}
            zako3.bulletdict.update({m+1: {"B"+str(n): [0, 1, round(0.1+i/10,1), (0.03+m/990+n*0.06)%0.72, 55, {1: {"speed": 0, "dangle": -90*(n//6-0.5)*2}, 2: {"dangle": 0}, 15:{"speed": 2.5}}] for n in range(6)} for m in range(60, 1320, 10)})

        if(not(zako3.appeartime in enemydata)):
            enemydata[zako3.appeartime] = []
        enemydata[zako3.appeartime].append(zako3)


    # ボス 第1攻撃
    enemy1 = Enemy(9000, 1, 376, 100, 65, 101, 100000, 150)
    enemy1.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 580-1: {"time": 180-1},
        525: {"vx": "approach1.0", "vy": "rand0.4"}, 570: {"vy": 0, "vx": 0},
        }
    enemy1.item_drop = {0: 12, 3: 4} # p52
    if(difficulty == 1):
        enemy1.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n-3.5)/10-0.05,1), 0.450+(n-3.5)*23/1000+round(np.sin(m*4.7*np.pi*2/180)*40/1000,3), 1.9-abs(n-3.5)/5, {0: {"flag":2}, 20: {"angle_flag": 0, "ay": 0.012, "angle": 180}}
            ] for n in range(0,8)} for m in range(200,515,7)}
    elif(difficulty == 2):
        enemy1.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n-3.5)/10-0.05,1), 0.450+(n-3.5)*22/1000+round(np.sin(m*4.7*np.pi*2/180)*40/1000,3), 1.8-abs(n-3.5)*1.5/5, {0: {"flag":2}, 25: {"angle_flag": 0, "ay": 0.013, "angle": 180}}
            ] for n in range(0,8)} for m in range(200,440,12)}
    if(not(enemy1.appeartime in enemydata)):
        enemydata[enemy1.appeartime] = []
    enemydata[enemy1.appeartime].append(enemy1)
    
    # ボス 第2攻撃
    enemy2 = Enemy(-1, 2, 376, 100, 65, 101, 140000, 150)
    enemy2.actdict = {
        0: {"vy": 2.5}, 40: {"vy": 0}, 525-1: {"time": 155-1},
        465: {"vx": "approach2.0"}, 485: {"vy": 0, "vx": 0},
        }
    enemy2.item_drop = {0: 10, 3: 4, 4: 1} # p50
    if(not(enemy2.appeartime in enemydata)):
        enemydata[enemy2.appeartime] = []
    enemydata[enemy2.appeartime].append(enemy2)

    enemy2_1 = Enemy(-1, 2, 376, 90, 0, 0, 5000, 0)
    enemy2_1.actdict = {
        159: {"vx": -30}, 160: {"angle_flag": 1,  "angle": 195, "dangle": 0.5, "speed": 1.8},
        460: {"dangle": 0, "speed": 0}, 464: {"angle_flag": 0, "vx": 30}, 465:{"vx": "approach2.0"}, 485: {"vx": 0}, 
        525: {"y": 150, "time": 155, "speed": 0}
        }
    if(difficulty == 1):
        enemy2_1.bulletdict = {160+m*5: dict(**{("B"+str(n)): [0,1,1.2,(n*180+m*19)%720/1000,2.2,{10: {"dspeed":-0.04}, 40: {"dspeed":0}}] for n in range(0,2)}) for m in range(54)}
    elif(difficulty == 2):
        pass
    if(not(enemy2_1.appeartime in enemydata)):
        enemydata[enemy2_1.appeartime] = []
    enemydata[enemy2_1.appeartime].append(enemy2_1)

    enemy2_2 = Enemy(-1, 2, 376, 90, 0, 0, 5000, 0)
    enemy2_2.actdict = {
        159: {"vx": 30}, 160: {"angle_flag": 1, "angle": 345, "dangle": -0.5, "speed": 1.8},
        460: {"dangle": 0, "speed": 0}, 464: {"angle_flag": 0, "vx": -30}, 465:{"vx": "approach2.0"}, 485: {"vx": 0}, 
        525: {"y": 150, "time": 155, "speed": 0}
        }
    if(difficulty == 1):
        enemy2_2.bulletdict = {160+m*5: dict(**{("B"+str(n)): [0,1,1.4,(n*180-m*19)%720/1000,2.2,{10: {"dspeed":-0.04}, 40: {"dspeed":0}}] for n in range(0,2)}) for m in range(54)}
    elif(difficulty == 2):
        pass
    if(not(enemy2_2.appeartime in enemydata)):
        enemydata[enemy2_2.appeartime] = []
    enemydata[enemy2_2.appeartime].append(enemy2_2)

    enemy2_3 = Enemy(-1, 2, 376, 170, 0, 0, 5000, 0)
    enemy2_3.actdict = {
        160: {"angle_flag": 1,  "angle": 180, "dangle": 360/150, "speed": 0.7},
        460: {"speed": 0}, 465:{"angle_flag": 0, "vx": "approach2.0"}, 485: {"vx": 0}, 
        525: {"y": 170, "time": 155, "speed": 0}
        }
    if(difficulty == 1):
        enemy2_3.bulletdict = {161+m*2: dict(**{("B"+str(n)): [0,1,1.3,(n*120+m*39)%720/1000,-2.2,{10: {"dspeed":0.1*(m+10)/210}, 240-m: {"dspeed":0}}] for n in range(0,3)}) for m in range(135)}
    elif(difficulty == 2):
        enemy2_3.bulletdict = {161+m*3: dict(**{("B"+str(n)): [0,1,1.3,(n*120+m*24)%720/1000,-2.0,{10: {"dspeed":0.1*(m+10)/210}, 200-m: {"dspeed":0}}] for n in range(0,3)}) for m in range(90)}
    if(not(enemy2_3.appeartime in enemydata)):
        enemydata[enemy2_3.appeartime] = []
    enemydata[enemy2_3.appeartime].append(enemy2_3)
    

    # ボス 第3攻撃
    enemy3 = Enemy(-2, 3, 376, 100, 65, 101, 150000, 150)
    enemy3.actdict = {
        0: {"vy": 2.5}, 80: {"vy": 0}, 710-1: {"time": 160-1},
        515: {"vx": "approach1.0"}, 580: {"vy": 0, "vx": 0},
        }
    enemy3.item_drop = {0: 10, 3: 7} # p80
    if(difficulty == 1):
        enemy3.bulletdict = {174:{("B"+str(n)): [
            0, 1, round(5.0+n/10,1), 0.36-n*60/1000, 4.4, {}
            ] for n in range(0,6)}}
    elif(difficulty == 2):
        enemy3.bulletdict = {174:{("B"+str(n)): [
            0, 1, round(5.0+n/10,1), 0.36-n*60/1000, 4.4, {}
            ] for n in range(0,6)}}
    if(not(enemy3.appeartime in enemydata)):
        enemydata[enemy3.appeartime] = []
    enemydata[enemy3.appeartime].append(enemy3)

    for i in range(6):
        enemy3_1 = Enemy(-2, 3, 376, 90, 0, 0, 5000, 0)
        enemy3_1.actdict = {
            60: {"x": 376, "y": 300}, 710-1: {"time": 160-1},
            180: {"vx": np.cos(i*60*np.pi/180)*4.4, "vy": np.sin(i*60*np.pi/180)*4.4}, 480: {"vx": -np.cos(i*60*np.pi/180)*44, "vy": -np.sin(i*60*np.pi/180)*44},
            510: {"vy": 0, "vx": 0}, 515: {"vx": "approach1.0"}, 580: {"vy": 0, "vx": 0}
            }
        if(difficulty == 1):
            enemy3_1.bulletdict = {188+m*2: dict(**{("B"+str(n)): [0,1,round(1.0+i/10,1),(90-i*60)%720/1000,28.0*np.sin((n*180+m*11)*np.pi/180),{1: {"speed":0, "angle":(n*180+m*12-i*60+90)%360}, 275-m*3: {"dspeed":0.012}, 340-m*3: {"dspeed":0.006}, 410-m*3: {"dspeed":0}}] for n in range(0,2)}) for m in range(90)}
        elif(difficulty == 2):
            enemy3_1.bulletdict = {188+m*6: dict(**{("B"+str(n)): [0,1,round(1.0+i/10,1),(n*180+m*54)%720/1000,11.0,{1: {"speed":0}, 275-m*6: {"dspeed":0.008}, 340-m*6: {"dspeed":0.004}, 410-m*6: {"dspeed":0}}] for n in range(0,2)}) for m in range(37)}
        if(not(enemy3_1.appeartime in enemydata)):
            enemydata[enemy3_1.appeartime] = []
        enemydata[enemy3_1.appeartime].append(enemy3_1)



    # ボス 第4攻撃
    enemy4 = Enemy(-3, 4, 376, 100, 65, 101, 150000, 170)
    enemy4.actdict = {
        0: {"vy": 2.5}, 120: {"vy": 0}, 680-1: {"time": 170-1}
        }
    enemy4.item_drop = {0: 3, 3: 5, 4: 1} # p45
    if(difficulty == 1):
        enemy4.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n%4-3.5)/10-0.05,1), 0.370+0.160*(n//4)+(abs(n-3.5)-2)*16/1000+round(np.sin(m*6.4*np.pi*2/180)*20/1000,3), 18, {0: {"flag":2}, 1: {"speed": 1.9-(n%4-3.5)/12}, 50: {"angle_flag": 0, "ay": 0.019}, 350: {"flag":1}}
            ] for n in range(0,8)} for m in range(180,380,4)}
    elif(difficulty == 2):
        enemy4.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n%4-3.5)/10-0.05,1), 0.370+0.160*(n//4)+(abs(n-3.5)-2)*12/1000+round(np.sin(m*3.2*np.pi*2/180)*10/1000,3), 18, {0: {"flag":2}, 1: {"speed": 1.7-(n%4-3.5)/16}, 50: {"angle_flag": 0, "ay": 0.02}, 350: {"flag":1}}
            ] for n in range(0,8)} for m in range(180,380,20)}
    if(not(enemy4.appeartime in enemydata)):
        enemydata[enemy4.appeartime] = []
    enemydata[enemy4.appeartime].append(enemy4)

    for i in range(2):
        enemy4_1 = Enemy(-3, 4, 376, 100, 0, 0, 5000, 0)
        enemy4_1.actdict = {
            680-1: {"time": 170-1},
            175: {"x": 376, "y": 400+(360*6/np.pi/2)*(i-0.5)*2}, 180: {"angle": 180+180*i, "angle_flag": 1, "dangle": 1, "speed": 6}, 380:{"dangle": 0, "speed": 0}
            }
        if(difficulty == 1):
            enemy4_1.bulletdict = {180+m*2: dict(**{("B"+str(n)): [0,1,round(4.0+i*4/10,1),(m*2+i*180+90)/1000,0.0,{1: {"speed":0}, 220-m: {"dspeed":0.025, "flag": 3}}] for n in range(0,1)}) for m in range(90)}
        elif(difficulty == 2):
            enemy4_1.bulletdict = {180+m*4: dict(**{("B"+str(n)): [0,1,round(4.0+i*4/10,1),(m*2)/1000,0.0,{1: {"speed":0}, 220-m*2: {"dspeed":0.04, "flag": 3}, 340-m*2: {"dspeed":0.0}}] for n in range(0,1)}) for m in range(45)}
        if(not(enemy4_1.appeartime in enemydata)):
            enemydata[enemy4_1.appeartime] = []
        enemydata[enemy4_1.appeartime].append(enemy4_1)

    # ボス 第5攻撃
    enemy5 = Enemy(-4, 5, 376, 100, 65, 101, 120000, 240)
    enemy5.actdict = {0:{"vy": 2.5}, 60:{"vy": 0}, 1340-1:{"time": 1280-1}}
    enemy5.item_drop = {0: 8, 3: 5} # p58
    if(not(enemy5.appeartime in enemydata)):
        enemydata[enemy5.appeartime] = []
    enemydata[enemy5.appeartime].append(enemy5)

    random_list = np.random.rand(100)
    enemy5_1 = Enemy(-4, 5, 376, 250, 0, 0, 5000, 0)
    enemy5_1.actdict = {m: {"y": np.random.rand()*50+225, "x": np.random.rand()*80+336} for m in range(140, 1040, 50)}
    enemy5_1.actdict.update({1070-1:{"time": 170-1}})
    if(difficulty == 1):
        enemy5_1.bulletdict = {m+1: {("B"+str(n)): [5, 5, 4.3, n*18/1000+random_list[m//20]/10, 80, {1: {"speed": 3.5}}] for n in range(0, 20)} for m in range(140, 1040, 50)}
    elif(difficulty == 2):
        enemy5_1.bulletdict = {m+1: {("B"+str(n)): [5, 3, 4.3, n*20/1000+random_list[m//20]/10, 80, {1: {"speed": 2.8}}] for n in range(0, 18)} for m in range(140, 1040, 50)}
    if(not(enemy5_1.appeartime in enemydata)):
        enemydata[enemy5_1.appeartime] = []
    enemydata[enemy5_1.appeartime].append(enemy5_1)

    enemy5_2 = Enemy(-4, 5, 76, 300, 0, 0, 5000, 0)
    enemy5_2.actdict = {m:{"y": np.random.rand()*100+300} for m in range(450, 1800, 75)}
    enemy5_2.actdict.update({1800-1:{"time": 450-1}})
    if(difficulty == 1):
        enemy5_2.bulletdict = {m+2: {("B"+str(n)): [5, 3, 4.4, (n*8+180)/1000+random_list[m//18]/25, 120, {1: {"speed": 4.1}}] for n in range(0, 45-8)} for m in range(450, 1800, 75)}
    elif(difficulty == 2):
        enemy5_2.bulletdict = {m+2: {("B"+str(n)): [6, 3, 4.4, (n*9+180)/1000+random_list[m//18]/10, 120, {1: {"speed": 2.7}}] for n in range(0, 40)} for m in range(450, 1800, 150)}
    if(not(enemy5_2.appeartime in enemydata)):
        enemydata[enemy5_2.appeartime] = []
    enemydata[enemy5_2.appeartime].append(enemy5_2)

    enemy5_3 = Enemy(-4, 5, 676, 300, 0, 0, 5000, 0)
    enemy5_3.actdict = {m:{"y": np.random.rand()*100+300} for m in range(450, 1800, 75)}
    enemy5_3.actdict.update({1800-1:{"time": 450-1}})
    if(difficulty == 1):
        enemy5_3.bulletdict = {m+3: {("B"+str(n)): [5, 3, 4.4, n*8/1000+random_list[m//19]/25, 120, {1: {"speed": 4.1}}] for n in range(0, 45-8)} for m in range(450, 1800, 75)}
    elif(difficulty == 2):
        enemy5_3.bulletdict = {m+3: {("B"+str(n)): [6, 3, 4.4, n*9/1000+random_list[m//19]/10, 120, {1: {"speed": 2.7}}] for n in range(0, 40)} for m in range(450, 1800, 150)}
    if(not(enemy5_3.appeartime in enemydata)):
        enemydata[enemy5_3.appeartime] = []
    enemydata[enemy5_3.appeartime].append(enemy5_3)


    # ボス 第6攻撃
    enemy6 = Enemy(-5, 6, 376, 100, 65, 101, 110000, 80)
    enemy6.actdict = {
        0: {"vy": 2}, 80: {"vy": 0}
        }
    enemy6.item_drop = {0: 40, 3: 3} # p70
    if(not(enemy6.appeartime in enemydata)):
        enemydata[enemy6.appeartime] = []
    enemydata[enemy6.appeartime].append(enemy6)

    enemy6_1 = Enemy(-5, 6, 376, 90, 0, 0, 5000, 0)
    enemy6_1.actdict = {
        0: {"vy": 2}, 80: {"vy": 0}, 221-1: {"time": 81-1}
        }
    enemy6_1.actdict.update({m: {"vx": "approach0.4", "vy": "approach0.6"} for m in range(81, 381, 2)})
    
    if(difficulty == 1):
        enemy6_1.bulletdict = {150:{("B"+str(n)): [
            0, 1, 0.1, 0.008+n/30*0.36+m/1000, 9, {1: {"speed": 3.5, "dspeed":-0.03}, 90: {"dspeed":0}}
            ] for n in range(0,30)},
            151:{("B"+str(n)): [
            0, 1, 0.2, 0.008+n/15*0.36+m/1000, 9, {1: {"speed": 4.0, "dspeed":-0.03}, 100: {"dspeed":0}}
            ] for n in range(0,15)}}
        enemy6_1.actdict.update({201-1: {"time": 81-1}})

    elif(difficulty == 2):
        enemy6_1.bulletdict = {150:{("B"+str(n)): [
            0, 1, 0.1, 0.008+n/20*0.36+m/1000, 9, {1: {"speed": 3.0, "dspeed":-0.025}, 80: {"dspeed":0}}
            ] for n in range(0,20)}}
    if(not(enemy6_1.appeartime in enemydata)):
        enemydata[enemy6_1.appeartime] = []
    enemydata[enemy6_1.appeartime].append(enemy6_1)


    
    # ボス 第7攻撃
    enemy7 = Enemy(-6, 7, 376, 100, 65, 101, 130000, 120)
    enemy7.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 630-1: {"time": 180-1},
        505: {"vx": "approach1.0", "vy": "rand0.5"}, 540: {"vy": 0, "vx": 0},
        }
    enemy7.item_drop = {0: 30, 3: 7} # p100
    if(difficulty == 1):
        enemy7.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(0.1+m//201/10, 1), 0.008+n/16*0.36+m/1000, 25, {0: {"flag":2}, 1: {"speed":2, "dangle": 4}, 49: {"speed":4.5}, 50: {"angle_flag": 0, "ay": 0.003}, 900: {"flag":1}}
            ] for n in range(0,16)} for m in range(200,515,105)}
        enemy7.bulletdict.update({m+1:{("B"+str(n)): [
            0, 1, round(5.3+m//201/10, 1), 0.008+(n+0.5)/8*0.36+m/1000, 25, {0: {"flag":2}, 1: {"speed":2, "dangle": 4}, 49: {"speed":4.0}, 50: {"angle_flag": 0, "ay": 0.003}, 900: {"flag":1}}
            ] for n in range(0,8)} for m in range(200,515,105)})
    elif(difficulty == 2):
        enemy7.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(0.1+m//250/10, 1), 0.008+n/6*0.36+m/1000, 25, {0: {"flag":2}, 1: {"speed":2, "dangle": 4}, 49: {"speed":3.5}, 50: {"angle_flag": 0, "ay": 0.005}, 900: {"flag":1}}
            ] for n in range(0,6)} for m in range(200,500,150)}
        enemy7.bulletdict.update({m+1:{("B"+str(n)): [
            0, 1, round(5.3+m//250/10, 1), 0.008+n/6*0.36+m/1000, 25, {0: {"flag":2}, 1: {"speed":2, "dangle": 4}, 49: {"speed":2.7}, 50: {"angle_flag": 0, "ay": 0.005}, 900: {"flag":1}}
            ] for n in range(0,6)} for m in range(200,500,150)})
    if(not(enemy7.appeartime in enemydata)):
        enemydata[enemy7.appeartime] = []
    enemydata[enemy7.appeartime].append(enemy7)


    # ボス 第8攻撃
    enemy8 = Enemy(-7, 8, 376, 100, 65, 101, 280000, 180)
    enemy8.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 3450-1: {"time": 3000-1},
        }
    enemy8.item_drop = {}
    if(difficulty == 1):
        enemy8.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n%4-3.5)/10-0.05,1), 0.370+0.160*(n//4)+(abs(n-3.5)-2)*16/1000+round(np.sin(m*6.4*np.pi*2/180)*20/1000,3), 18, {0: {"flag":2}, 1: {"speed": 1.6-(n%4-3.5)/12}, 50: {"angle_flag": 0, "ay": 0.023}, 350: {"flag":1}}
            ] for n in range(0,8)} for m in range(3030,3270,8)}
    elif(difficulty == 2):
        enemy8.bulletdict = {m:{("B"+str(n)): [
            0, 1, round(abs(n%4-3.5)/10-0.05,1), 0.370+0.160*(n//4)+(abs(n-3.5)-2)*16/1000+round(np.sin(m*6.4*np.pi*2/180)*20/1000,3), 18, {0: {"flag":2}, 1: {"speed": 1.5-(n%4-3.5)/12}, 50: {"angle_flag": 0, "ay": 0.022}, 350: {"flag":1}}
            ] for n in range(0,8)} for m in range(3030,3240,14)}
    if(not(enemy8.appeartime in enemydata)):
        enemydata[enemy8.appeartime] = []
    enemydata[enemy8.appeartime].append(enemy8)

    enemy8_1 = Enemy(-7, 8, 376, 100, 0, 0, 5000, 0)
    enemy8_1.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 630-1: {"time": 150-1},
        }
    if(difficulty == 1):
        enemy8_1.bulletdict = {m:{("B"+str(n)): [
            0, 1, 6.0+(m-150)//60*0.1, 1.360+(n-3)*0.02, 12*(abs(n%3-1.5)**2+6.75)**0.5, {1: {"angle_flag": 1, "speed":3.4, "dangle": -(n-3)*20}, 2: {"dangle": 0}}
            ] for n in range(0,7)} for m in range(150,630,60)}
    elif(difficulty == 2):
        enemy8_1.bulletdict = {m:{("B"+str(n)): [
            0, 1, 6.0+(m-150)//60*0.1, 1.360+(n-3)*0.015, 12*(abs(n%3-1.5)**2*0.75+6.75)**0.5, {1: {"angle_flag": 1, "speed":3.1, "dangle": -(n-3)*15}, 2: {"dangle": 0}}
            ] for n in range(0,7)} for m in range(150,630,80)}
    if(not(enemy8_1.appeartime in enemydata)):
        enemydata[enemy8_1.appeartime] = []
    enemydata[enemy8_1.appeartime].append(enemy8_1)

    enemy8_2 = Enemy(-7, 8, 376, 100, 0, 0, 5000, 0)
    enemy8_2.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 630-1: {"time": 150-1},
        }
    if(difficulty == 1):
        enemy8_2.bulletdict = {m:{("B"+str(n)): [
            0, 1, 5.0 + [0,7,6,5,4,3,2,1][(m-150)//60] / 10, 1.0, 0.3, {2: {"angle_flag": 1, "speed": 3.4}}
            ] for n in range(0,11)} for m in range(150,630,60)}
    elif(difficulty == 2):
        enemy8_2.bulletdict = {m:{("B"+str(n)): [
            0, 1, 5.0 + [0,7,6,5,4,3,2,1][(m-150)//60] / 10, 1.0, 0.2, {3: {"angle_flag": 1, "speed": 3.1}}
            ] for n in range(0,11)} for m in range(150,630,80)}
    if(not(enemy8_2.appeartime in enemydata)):
        enemydata[enemy8_2.appeartime] = []
    enemydata[enemy8_2.appeartime].append(enemy8_2)

    enemy8_3 = Enemy(-7, 8, 376, 100, 0, 0, 5000, 0)
    enemy8_3.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 630-1: {"time": 150-1},
        }
    if(difficulty == 1):
        enemy8_3.bulletdict = {m:{("B"+str(n)): [
            0, 1, 6.0+(m-150)//60*0.1, 1.360, 0.3, {6: {"speed": 3.15+abs(n-5)/20}, 7: {"angle_flag": 1, "dangle": -(n-5)*0.4}, 25: {"dangle": 0}, 26: {"dangle": (n-5)*0.18}, 90: {"dangle": 0}}
            ] for n in range(0,11)} for m in range(150,630,60)}
    elif(difficulty == 2):
        enemy8_3.bulletdict = {m:{("B"+str(n)): [
            0, 1, 6.0+(m-150)//60*0.1, 1.360, 0.2, {8: {"speed": 2.95+abs(n-3)/20}, 9: {"angle_flag": 1, "dangle": -(n-3)*0.4}, 28: {"dangle": 0}, 29: {"dangle": (n-3)*0.19}, 69: {"dangle": 0}}
            ] for n in range(0,7)} for m in range(150,630,80)}
    if(not(enemy8_3.appeartime in enemydata)):
        enemydata[enemy8_3.appeartime] = []
    enemydata[enemy8_3.appeartime].append(enemy8_3)

    enemy8_4 = Enemy(-7, 8, 376, 100, 0, 0, 5000, 0)
    enemy8_4.actdict = {
        0: {"vy": 2}, 50: {"vy": 0}, 2070-1: {"time": 1590-1},
        }
    if(difficulty == 1):
        enemy8_4.bulletdict = {m:{("B"+str(n)): [
            0, 1, 6.0+(m-1590)//60*0.1, 1.360, 0.3, {6: {"speed": 3.15+abs(n-5)/20}, 7: {"angle_flag": 1, "dangle": -(n-5)*0.4}, 25: {"dangle": 0}, 26: {"dangle": (n-5)*0.18}, 90: {"dangle": 0}}
            ] for n in [-2, -1, 11, 12]} for m in range(1590,2070,60)}
    elif(difficulty == 2):
        pass
    if(not(enemy8_4.appeartime in enemydata)):
        enemydata[enemy8_4.appeartime] = []
    enemydata[enemy8_4.appeartime].append(enemy8_4)

    

    for i in range(8):
        enemy8_6 = Enemy(-7, 8, 376+(i-3.5)*25, 140, 0, 0, 5000, 0)
        enemy8_6.actdict = {
            0: {"vy": 2}, 50: {"vy": 0}, 1621-1: {"time": 901-1}
            }
        if(difficulty == 1):
            enemy8_6.bulletdict = {901+m:{("B"+str(n)): [
                0, 1, round(2.0+i/10, 1), np.random.rand()*0.36, 9, {1: {"speed": 3.5*np.random.rand()}, 2: {"angle_flag": 0, "ay": 0.05}, 12: {"ay": 0.01}}
                ] for n in range(0,1)} for m in range(0, 720, 30)}
        elif(difficulty == 2):
            enemy8_6.bulletdict = {901+m:{("B"+str(n)): [
                0, 1, round(2.0+i/10, 1), np.random.rand()*0.36, 9, {1: {"speed": 2.8*np.random.rand()}, 2: {"angle_flag": 0, "ay": 0.04}, 12: {"ay": 0.01}}
                ] for n in range(0,1)} for m in range(0, 720, 72)}
        if(not(enemy8_6.appeartime in enemydata)):
            enemydata[enemy8_6.appeartime] = []
        enemydata[enemy8_6.appeartime].append(enemy8_6)


def main():
    global dispmode, start_select, player, shot, elapsedtime, globaltime, enemydata, enemy_list, boss_callflag, moveflag, clear_flag, starttime
    pygame.mixer.music.load("bgm/sm20439564.ogg")
    pygame.mixer.music.set_volume(0.35)
    
    while(True):
        pressed_key = pygame.key.get_pressed()


        if(dispmode == 0):
            screen.fill((0, 0, 0, 255)) # 背景色の指定。
            text0 = font_title.render("Normal", True, (255,249,249))
            text1 = font_title.render("player1", True, (255,249,249)) if start_select%6==0 else font_title.render("player1", True, (170,170,170))
            text2 = font_title.render("player2", True, (255,249,249)) if start_select%6==1 else font_title.render("player2", True, (170,170,170))
            text3 = font_title.render("Easy", True, (255,249,249))
            text4 = font_title.render("player1", True, (255,249,249)) if start_select%6==2 else font_title.render("player1", True, (170,170,170))
            text5 = font_title.render("player2", True, (255,249,249)) if start_select%6==3 else font_title.render("player2", True, (170,170,170))
            text6 = font_title.render("Exit", True, (255,249,249)) if start_select%6>=4 else font_title.render("Exit", True, (170,170,170))
            screen.blit(text0, [300, 500])# 文字列の表示位置
            screen.blit(text1, [550, 500])# 文字列の表示位置
            screen.blit(text2, [750, 500])# 文字列の表示位置
            screen.blit(text3, [300, 600])# 文字列の表示位置
            screen.blit(text4, [550, 600])# 文字列の表示位置
            screen.blit(text5, [750, 600])# 文字列の表示位置
            screen.blit(text6, [550, 720])# 文字列の表示位置

            if(pressed_key[key_up] and start_select <= 5):
                start_select = start_select + 6*15-2
            elif(pressed_key[key_down] and start_select <= 5):
                start_select = start_select + 6*15+2
            elif((pressed_key[key_left] or pressed_key[key_right]) and start_select <= 5):
                start_select = start_select + 6*15+1 if start_select%2 == 0 else start_select + 6*15-1
            else:
                start_select = max(start_select%6, start_select-6)

            if(pressed_key[key_shot] and (not pressed_key[key_bomb]) and start_select <= 5):
                dispmode, globaltime, elapsedtime, clear_flag = 1, 0, 0, 0
                starttime = time.time()
                shot.clear()
                if(start_select%6 == 0):
                    player = Character(1)
                elif(start_select%6 == 1):
                    player = Character(2)
                elif(start_select%6 == 2):
                    player = Character(1)
                    player.difficulty = 2
                    player.decreasepower = 0.5
                    player.kuraitime = 21
                elif(start_select%6 == 3):
                    player = Character(2)
                    player.difficulty = 2
                    player.decreasepower = 0.5
                    player.kuraitime = 21
                elif(start_select%6 >= 4):
                    pygame.quit()
                    sys.exit()
        if(dispmode == 1):

            # 音楽の設定
            if(elapsedtime == 25):
                pygame.mixer.music.play(-1)
            if(elapsedtime == 9025):
                pygame.mixer.music.fadeout(100)
            if(elapsedtime == 9120):
                pygame.mixer.music.load("bgm/m-art_BetryalAlice_i.ogg")
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)

            if((pressed_key[K_ESCAPE] or (moveflag==0 and pressed_key[K_z])) and start_select < 6):
                moveflag = [1,0][moveflag]
                start_select += 6*25
            elif(pressed_key[K_a] and start_select < 6):
                player.kind = [0, 2, 1][player.kind]
                start_select += 6*25
            elif(start_select >= 6):
                start_select -= 6


            if(moveflag == 1):
                # 敵出現判定
                if(elapsedtime == 1):
                    set_enemy(player.difficulty)
                if(elapsedtime in enemydata.keys() or boss_callflag != 0):
                    if(boss_callflag != 0):
                        for i in enemydata[-boss_callflag]:
                            enemy_list.append(i)
                            if(i.bossflag == 1):
                                boss_change_sound.play()
                                bonusflag = 10000000
                        boss_callflag = 0
                    else:
                        for i in enemydata[elapsedtime]:
                            enemy_list.append(i)
                            if(i.bossflag == 1):
                                boss_change_sound.play()
                                bonusflag = 10000000

                time0 = time.time()
                screen.fill((63, 127, 191, 255)) # 背景色の指定。
                player.move() # 移動処理
                time1 = time.time()
                item_act() # 全部のアイテムの移動処理
                enemy_act() # 全部の敵の移動処理
                shot_act() # ショットの処理
                screen.blit(player.player_img, player.rect_player) # キャラの描画
                pygame.draw.circle(screen, (255,85,42), (int(round(player.x)),int(round(player.y))), int(max(np.ceil(player.r)+1, 1))) # player当たり判定を橙表示
                pygame.draw.circle(screen, (255,255,255), (int(round(player.x)),int(round(player.y))), int(max(np.ceil(player.r)-1, 1)))
                bullet_act() # 全部の弾の移動処理
                time2 = time.time()
                screen.blit(bg, rect_bg) # 背景画像の描画
                time3 = time.time()


                disp = ["Life: {:1d}".format(player.life),
                        "Bomb: {:1d}".format(player.bomb),
                        "Power: {:.2f} / 6.00".format(player.power),
                        # "Poweritem: {:d}".format(player.poweritem),
                        "Graze: {:1d}".format(player.graze),
                        # "real time: {:.2f}".format(time.time() - starttime),
                        # "bullet: {:1d}".format(len(bullet_list)),
                        # "time1 {:.5f}".format(time1 - time0),
                        # "time2 {:.5f}".format(time2 - time1),
                        # "time3 {:.5f}".format(time3 - time2)
                        ]
                for i, s in enumerate(disp):
                    screen.blit(font.render(s, True, (0,63,31)), [788, 41+i*50+40])
                    screen.blit(font.render(s, True, (255,255,255)), [785, 40+i*50+40])

                if(clear_flag == 1):
                    clear_flag = elapsedtime
                    cleartime = globaltime
                elif(clear_flag >= 1 and elapsedtime - clear_flag >= 30):
                    text = font_title.render("ALL CLEAR", True, (239,239,239))
                    screen.blit(text, [240, 120])
                    pygame.mixer.music.fadeout(2200)
                    if(globaltime - cleartime >= 125 and pygame.key.get_pressed()[key_shot]):
                        dispmode = 0
                        start_select += 6*30


                if(player.invincible >= 0):
                    elapsedtime += 1

            else:
                text = pygame.font.Font(None, 120).render("PAUSE", True, (239,239,239))
                screen.blit(text, [255, 320])# 文字列の表示位置

        globaltime += 1
        pygame.display.update() # 画面更新
        pygame.transform.scale(screen, (1280, 960), pygame.display.get_surface())
        clock.tick(60)
        

        for event in pygame.event.get(): # 終了処理
            if event.type == KEYDOWN:
                if event.key == K_F4:
                    pygame.quit()
                    sys.exit()
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

if __name__=="__main__":
    player = Character(1)
    main()
