SIZE = 4
EMPTY = [0, 1, 0]
idEMPTY = 0
idPLAYER = 1
idENEMY = 2
map = [[EMPTY for i in range(SIZE)] for j in range(SIZE)]
color = ['\033[37m', '\033[36m', '\033[31m']    # white, cyan, red
color_reset = '\033[0m'
show_dir = ['↑', '→', '↓', '←']

def show_map(map):
    sep_line = "+"+"---+"*SIZE
    print(sep_line)
    for line in map:
        for masu in line:
            if masu[0] > idEMPTY:
                print(f"| {color[masu[0]]}{show_dir[masu[1]]}{color_reset} ", end="")
            else:
                print("|   ", end="")
        print("|")
        print(sep_line)

class Charactor():
    """
    変数1 row: ヨコ。x軸
    変数2 col: タテ。y軸
    """
    GO = {0: [-1, 0], 1: [0, 1], 2: [1, 0], 3: [0, -1]}
    # 0:上, 1:右, 2:下, 3:左 *時計回り
    moveError = -200

    def __init__(self, id, row, col, dir):
        self.id = id    # 種類(自機、壁、雑魚敵、ボス)
        self.row = row  # x
        self.col = col  # y
        self.dir = dir  # {0:上, 1:右, 2:下, 3:左}
        self.hp = 0
        self.del_row = -1
        self.del_col = -1

    @classmethod
    def is_out_of_map(cls, col, row):
        """
        row, colがマップ外にでないか確認する'クラス'関数
        いろんなとこで使うのでCharactorのクラス関数に分離
        戻り値: True(map外に出た) / False(map内にいる)
        メモ: ボス戦と雑魚戦のマップサイズ違うから、
            グローバル定数にするのは間違っている
        """
        # 移動後map外に出ないか確認
        if row < 0 or SIZE-1 < row:
            return True
        if col < 0 or SIZE-1 < col:
            return True
        return False

    def move(self, goto):
        """
        gotoの方向へ位置を更新する
        goto: 0=上, 1=右, 2=下, 3=左
        """
        after_col = self.col + Charactor.GO[goto][0]
        after_row = self.row + Charactor.GO[goto][1]

        # マップ外チェックのタイミング、ほんとにココか？
        if Charactor.is_out_of_map(after_col, after_row):
            return Charactor.moveError
        
        # 元居た場所を記録->chara_drawで削除
        self.del_row = self.row
        self.del_col = self.col

        # 位置を更新
        self.col = after_col
        self.row = after_row
        self.dir = goto
    
    def chara_draw(self, map):
        """
        移動後に必ず実施する
        マップに反映させる関数
        """
        map[self.del_col][self.del_row] = EMPTY
        param = [self.id, self.dir, self.hp]
        map[self.col][self.row] = param
        return map

class Player(Charactor):
    """
    プレイヤーに関わるクラス
    """

    MOVE_DIRECTION = {"w": 0, "a": 3, "s": 2, "d": 1}

    def __init__(self):
        super().__init__(idPLAYER, 0, SIZE-1, 1)   # 左下を初期位置として設定
        self.hp = 25    # HP
        self.power = 5  # 攻撃力
        self.money = 0  # 所持金

    def user_move(self):
        """
        これを呼び出せば移動できるようにしたい
        入力動作を書く
        """
        while True:
            mdir = input("移動してください(WASD): ")
            mdir.lower()
            # デバッグ用: 立ち止まる
            if mdir == "p":
                break
            if not mdir in Player.MOVE_DIRECTION.keys():
                print("WASDを入力して下さい")
                continue
            if super().move(Player.MOVE_DIRECTION[mdir]) == super().moveError:
                print("マップ外です")
                continue
            break
    
    def setHP(self, hp):
        self.hp += hp

class Enemy(Charactor):
    """
    雑魚敵に関するクラス
    必要->自動で動く機能, 
    目標マスを検出する→攻撃方法によって最適場所は異なる
    目標マスへの最短距離を算出。なるべく計算が少なく
    行動指針：ガンガン行こうぜ -> ダメージ覚悟で自分優位の場所を取りに行く
    武器によって有利な場所(attack_pos)を設定する。ex)プレイヤーから見て右上の場所
    そこ目指して最短距離で
    初期バージョンは壁なし想定で
    """
    def __init__(self):
        super().__init__(idENEMY, SIZE-1, 0, 3)   # 右上に設定 左向き
        self.hp = 10
        self.power = 5
        self.attack_pos = [[1, 0]]    # プレイヤーに対する有利位置
        # 右から攻撃するように設定
        # リストの最初が優先度が高く、達成できなそうな場合2番目、3番目となる

    def objective_place(self, map, player: Player):
        """
        目標地点まで最短距離で目指す
        変数1 map: 一応将来、壁に対応させるためのモノ
        変数2 player: cpuなんだからプレイヤーの位置は知ってていいでしょ
        """
        # 目的地設定
        obj_col = player.col + self.attack_pos[0][0]
        obj_row = player.row + self.attack_pos[0][1]

        # 方法1: マンハッタン距離探索
        # 上下左右のマスからのマンハッタン距離を計算
        # 一番小さい場所へ移動-> 最短距離
        # メリット: ループが4回のみ
        distance = 4294967296   # 2^32, 非常に大きな数で宣言
        # placeの順番大事(上、右、下、左)
        place = [[self.col-1, self.row], [self.col, self.row+1], [self.col+1, self.row], [self.col, self.row-1]]
        for i, p in enumerate(place):
            # マップ外チェック
            if super().is_out_of_map(p[0], p[1]):
                print("マップ外")
                continue
                # ここでマップ外チェックして、move()の時にもチェックする構造になっている
                # moveに座標でなく、上下左右を表す0~3を渡す構造にしたかったから
                # 誰か解決策あればplz
            # 距離計算
            check_distance = abs(obj_col-p[0]) + abs(obj_row-p[1])
            print(check_distance)
            if check_distance < distance:
                distance = check_distance
                next_move = i
        print(next_move)
        super().move(next_move) # マップ外チェック終わってるから、戻さなくていい
    
    def attack(self, player: Player):
        """
        プレイヤーに攻撃する関数
        PLのHPを直接いじるのはヤバプログラム -> PLのsetterに値を渡す関数にする
        展望として、ダメージを与えたエフェクトをマップに表示させるシステムをここで書きたい
        戻り値: True(攻撃成功) / False(いなかった)
        """
        # 攻撃範囲の座標計算
        # 試しに現在地+dirの方向へ+1の場所
        attack_area = [self.col+super().GO[self.dir][0], self.row+super().GO[self.dir][1]]
        if attack_area[0] == player.col and attack_area[1] == player.row:
            player.setHP(-self.power)
            print(attack_area)
            return True
        return False

    def change_direction(self, player: Player):
        """
        方向転換の関数
        上下左右にPLがいたときにここへ飛んでくる
        戻り値: True(PLがいた+方向転換した) / False(いなかった)
        """
        place = [[self.col-1, self.row], [self.col, self.row+1], [self.col+1, self.row], [self.col, self.row-1]]
        for i, p in enumerate(place):
            if p[0] == player.col and p[1] == player.row:
                self.dir = i
                return True
        return False
    
    def choice_action(self, player: Player, map):
        """
        CPUの動きを管理する関数
        """
        # 1.攻撃範囲にPLがいれば攻撃
        if self.attack(player):
            print("敵の攻撃！")
            print(f"{self.power}ダメージ！残りHP: {player.hp}")
            return
        # 2.上下左右にPLがいれば方向転換
        if self.change_direction(player):
            print("敵がこちらをむいた")
            super().chara_draw(map)
            return
        # 3.プレイヤーに向かって移動
        self.objective_place(map, player)
        super().chara_draw(map)
        
if __name__ == "__main__":
    # 初期設定
    pl = Player()
    map = pl.chara_draw(map)
    en = Enemy()
    map = en.chara_draw(map)
    while True:
        show_map(map)

        pl.user_move()
        map = pl.chara_draw(map)

        show_map(map)

        en.choice_action(pl, map)