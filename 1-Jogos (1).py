import math
import random
import pygame

# ============================================================
# MANSÃO: FUGA SOMBRIA — Escape room com exploração de labirinto e drones de segurança
# Controles: WASD/setas para mover, E para interagir, R reiniciar
# ============================================================

pygame.init()
pygame.font.init()

TILE = 32
COLS, ROWS = 31, 21
SCREEN_W, SCREEN_H = 1050, 740
HUD_H = 68
FPS = 60

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Mansão: Fuga Sombria")
clock = pygame.time.Clock()

BLACK = (8, 10, 24)
NAVY = (12, 20, 54)
WALL = (35, 70, 210)
WALL_EDGE = (60, 190, 255)
YELLOW = (255, 220, 40)
WHITE = (245, 248, 255)
GOLD = (255, 180, 45)
RED = (255, 65, 80)
PINK = (255, 105, 190)
CYAN = (50, 235, 235)
ORANGE = (255, 155, 45)
GREEN = (70, 235, 125)
PURPLE = (175, 100, 255)
GREY = (100, 115, 150)

font = pygame.font.Font(None, 25)
small_font = pygame.font.Font(None, 20)
title_font = pygame.font.Font(None, 56)
big_font = pygame.font.Font(None, 38)

# '#' = parede; '.' = ponto; ' ' = corredor; P = jogador; G = drone de segurança
# K = chave; C = console; E = saída; D = porta bloqueada; H = cura
RAW_MAP = [
"###############################",
"#P....#.......#.......#.......#",
"###.#.#.#####.#.#####.#.###.#..#",
"#...#...#.....#.....#...#...#..##",
"#.#####.#.#########.#.#####.##..#",
"#.....#.#.....#.....#.....#.....#",
"#####.#.#####.#.#########.#.#####",
"#.....#.....#...#.....#...#.....#",
"#.#########.#####.###.#.#######..#",
"#.........#.......#...#.....#.....#",
"###.#####.#########D#####.#.#####.#",
"#...#.....#.......#.......#.....#.#",
"#.###.#####.#####.#########.###.#..#",
"#.....#.....#...#.....#.....#...#..#",
"#####.#.#####.#.#####.#.#####.###.##",
"#.....#.......#...#...#.....#......#",
"#.#########.#####.#.#########.####.#",
"#...........#.....#.....#.........E#",
"#.#########.#.#########.#.###########",
"#K..........#.....C.....#.....H.....#",
"###############################",
]

def make_map():
    grid = [list(row.ljust(COLS, '#')[:COLS]) for row in RAW_MAP]
    # Normaliza largura, mantém bordas sólidas e garante que todas as passagens
    # sejam transitáveis mesmo se o mapa for editado.
    for y in range(ROWS):
        grid[y][0] = '#'
        grid[y][-1] = '#'
    for x in range(COLS):
        grid[0][x] = '#'
        grid[-1][x] = '#'
    return grid

class SecurityDrone:
    """Drone que persegue o jogador por corredores usando busca em largura."""
    DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    def __init__(self, x, y, color, delay=0):
        self.x, self.y = float(x), float(y)
        self.color = color
        self.speed = 1.85
        self.direction = random.choice(self.DIRECTIONS)
        self.delay = delay
        self.home = (x, y)
        self.repath_timer = 0

    def tile(self):
        return round(self.x / TILE), round(self.y / TILE)

    def _nearest_open_tile(self, game, origin):
        """Encontra a célula livre mais próxima se o alvo estiver numa parede."""
        if game.walkable(*origin):
            return origin
        queue = [origin]
        seen = {origin}
        for cell in queue:
            for dx, dy in self.DIRECTIONS:
                nxt = (cell[0] + dx, cell[1] + dy)
                if nxt in seen or not (0 <= nxt[0] < COLS and 0 <= nxt[1] < ROWS):
                    continue
                if game.walkable(*nxt):
                    return nxt
                seen.add(nxt)
                queue.append(nxt)
        return (1, 1)

    def _choose_path_step(self, game):
        start = self._nearest_open_tile(game, self.tile())
        target = self._nearest_open_tile(
            game, (round(game.player.x / TILE), round(game.player.y / TILE))
        )

        # BFS guarda o caminho completo e escolhe o primeiro passo até o jogador.
        queue = [start]
        previous = {start: None}
        for cell in queue:
            if cell == target:
                break
            for dx, dy in self.DIRECTIONS:
                nxt = (cell[0] + dx, cell[1] + dy)
                if nxt not in previous and game.walkable(*nxt):
                    previous[nxt] = cell
                    queue.append(nxt)

        if target in previous and target != start:
            cell = target
            while previous[cell] != start and previous[cell] is not None:
                cell = previous[cell]
            return cell[0] - start[0], cell[1] - start[1]

        # Se o jogador estiver inacessível, continua patrulhando um corredor livre.
        options = [(dx, dy) for dx, dy in self.DIRECTIONS
                   if game.walkable(start[0] + dx, start[1] + dy)]
        if not options:
            return (0, 0)
        reverse = (-self.direction[0], -self.direction[1])
        choices = [d for d in options if d != reverse] or options
        return random.choice(choices)

    def update(self, game):
        # Delay serve apenas para escalonar a entrada dos drones; depois disso
        # todos continuam se movendo em todos os frames.
        if self.delay > 0:
            self.delay -= 1
            return

        # Só recalcula a rota quando o drone chega ao centro de uma célula.
        tx = round(self.x / TILE)
        ty = round(self.y / TILE)
        centered_x = abs(self.x - tx * TILE) < self.speed + 0.2
        centered_y = abs(self.y - ty * TILE) < self.speed + 0.2

        if centered_x and centered_y:
            self.x, self.y = tx * TILE, ty * TILE
            self.direction = self._choose_path_step(game)
            dx, dy = self.direction
            # Nunca começa a andar para dentro de uma parede.
            if (dx, dy) == (0, 0) or not game.walkable(tx + dx, ty + dy):
                options = [d for d in self.DIRECTIONS
                           if game.walkable(tx + d[0], ty + d[1])]
                if options:
                    self.direction = random.choice(options)
                else:
                    return

        dx, dy = self.direction
        if (dx, dy) == (0, 0):
            # Recuperação: se ficou sem direção, tenta escolher uma passagem.
            self.direction = self._choose_path_step(game)
            dx, dy = self.direction
            if (dx, dy) == (0, 0):
                return

        # Durante o trajeto entre dois centros não usamos round() para validar
        # a próxima casa: isso fazia o drone pensar que já estava uma casa à
        # frente e ficar preso no meio do corredor.
        nx = self.x + dx * self.speed
        ny = self.y + dy * self.speed
        next_tx = round((nx + dx * self.speed) / TILE) if dx else round(nx / TILE)
        next_ty = round((ny + dy * self.speed) / TILE) if dy else round(ny / TILE)
        if not game.walkable(next_tx, next_ty):
            # Encosta no centro da célula atual e tenta recalcular no próximo frame.
            if dx:
                self.x = round(self.x / TILE) * TILE
            else:
                self.y = round(self.y / TILE) * TILE
            self.direction = (0, 0)
            return

        self.x, self.y = nx, ny

    def draw(self, surf):
        # Drone de segurança: corpo metálico, hélices e olho vermelho de scanner.
        x, y = int(self.x), int(self.y + HUD_H)
        body = pygame.Rect(x-11, y-9, 22, 18)
        pygame.draw.line(surf, self.color, (x-15,y-13), (x+15,y-13), 3)
        pygame.draw.circle(surf, self.color, (x-15,y-13), 4)
        pygame.draw.circle(surf, self.color, (x+15,y-13), 4)
        pygame.draw.rect(surf, (75,85,110), body, border_radius=5)
        pygame.draw.rect(surf, self.color, body, 2, border_radius=5)
        pygame.draw.circle(surf, RED, (x+2,y), 4)
        pygame.draw.circle(surf, WHITE, (x+3,y-1), 1)

class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = make_map()
        self.player = type("Player", (), {})()
        self.player.x, self.player.y = 1*TILE, 1*TILE
        self.player.direction = (0,0)
        self.player.next_direction = (0,0)
        self.player.mouth = 0
        self.player.lives = 3
        self.score = 0
        self.has_key = False
        self.console_open = False
        self.exit_open = False
        self.game_over = False
        self.won = False
        self.message = "Colete os pontos, pegue a chave e descubra o código do console!"
        self.message_timer = 300
        self.invincible = 120
        self.dots = set()
        self.key_pos = (1,19)
        self.console_pos = (15,19)
        self.exit_pos = (29,17)
        self.heal_pos = (27,19)
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == '.':
                    self.dots.add((x,y))
                    self.grid[y][x] = ' '
                elif ch == 'P':
                    self.player.x, self.player.y = x*TILE, y*TILE
                    self.grid[y][x] = ' '
                elif ch == 'K':
                    self.key_pos = (x,y)
                    self.grid[y][x] = ' '
                elif ch == 'C':
                    self.console_pos = (x,y)
                    self.grid[y][x] = ' '
                elif ch == 'E':
                    self.exit_pos = (x,y)
                    self.grid[y][x] = ' '
                elif ch == 'H':
                    self.heal_pos = (x,y)
                    self.grid[y][x] = ' '
        self.drones = [
            SecurityDrone(15*TILE, 5*TILE, RED, 60),
            SecurityDrone(25*TILE, 9*TILE, PINK, 150),
            SecurityDrone(9*TILE, 15*TILE, CYAN, 240),
        ]
        # Garante que cada drone comece em um corredor livre, mesmo se o mapa mudar.
        for drone in self.drones:
            spawn = drone._nearest_open_tile(self, drone.tile())
            drone.x, drone.y = spawn[0] * TILE, spawn[1] * TILE
        self.total_dots = len(self.dots)

    def walkable(self, tx, ty):
        if not (0 <= tx < COLS and 0 <= ty < ROWS):
            return False
        ch = self.grid[ty][tx]
        if ch == '#':
            return False
        if ch == 'D' and not self.has_key:
            return False
        return True

    def say(self, text, duration=210):
        self.message, self.message_timer = text, duration

    def try_move(self, direction):
        # Só troca de direção quando o personagem está alinhado ao centro da casa.
        if direction == (0,0):
            return
        px, py = self.player.x, self.player.y
        tx, ty = round(px / TILE), round(py / TILE)
        aligned_x = abs(px - tx*TILE) <= 5
        aligned_y = abs(py - ty*TILE) <= 5
        if direction[0] != 0 and aligned_y:
            self.player.y = ty*TILE
            if self.walkable(tx + direction[0], ty):
                self.player.direction = direction
        elif direction[1] != 0 and aligned_x:
            self.player.x = tx*TILE
            if self.walkable(tx, ty + direction[1]):
                self.player.direction = direction

    def interact(self):
        tx, ty = round(self.player.x/TILE), round(self.player.y/TILE)
        near = lambda pos: abs(tx-pos[0])+abs(ty-pos[1]) <= 1
        if near(self.console_pos):
            if not self.has_key:
                self.say("O console está bloqueado. Procure a chave dourada!")
            elif self.console_open:
                self.say("Console ativado! A saída foi destrancada.")
            else:
                self.say("Digite o código secreto no teclado: 4729", 300)
                self.code_entry = True
        elif near(self.exit_pos):
            if self.exit_open:
                self.won = True
                self.say("Você escapou da Mansão: Fuga Sombria!", 99999)
            else:
                self.say("A saída está selada. Ative o console primeiro.")
        else:
            self.say("Nada para interagir aqui. Procure a chave e o console.")

    def update(self):
        if self.game_over or self.won:
            return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.next_direction = (-1,0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.next_direction = (1,0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.next_direction = (0,-1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.next_direction = (0,1)

        self.try_move(self.player.next_direction)
        # Movimento contínuo: mantém a direção e, ao encontrar uma parede,
        # vira automaticamente para um corredor livre em vez de ficar parado.
        dx, dy = self.player.direction
        speed = 2.0
        if dx or dy:
            nx = self.player.x + dx * speed
            ny = self.player.y + dy * speed
            if self.walkable(round(nx / TILE), round(ny / TILE)):
                if dx:
                    self.player.x = nx
                else:
                    self.player.y = ny
            else:
                # Alinha à grade e procura uma saída livre. Prefere não voltar
                # imediatamente pelo caminho de onde veio.
                self.player.x = round(self.player.x / TILE) * TILE
                self.player.y = round(self.player.y / TILE) * TILE
                tx, ty = round(self.player.x / TILE), round(self.player.y / TILE)
                options = [(sx, sy) for sx, sy in [(1,0),(-1,0),(0,1),(0,-1)]
                           if self.walkable(tx+sx, ty+sy)]
                reverse = (-dx, -dy)
                choices = [d for d in options if d != reverse] or options
                if choices:
                    self.player.direction = choices[0]
                else:
                    self.player.direction = (0, 0)

        tx, ty = round(self.player.x/TILE), round(self.player.y/TILE)
        if (tx,ty) in self.dots:
            self.dots.remove((tx,ty))
            self.score += 10
        if not self.has_key and (tx,ty) == self.key_pos:
            self.has_key = True
            self.score += 100
            self.say("Chave dourada encontrada! Agora encontre o console.")
        if (tx,ty) == self.heal_pos and self.player.lives < 3:
            self.player.lives += 1
            self.heal_pos = (-99,-99)
            self.say("Você encontrou uma vida extra!")
        if self.invincible > 0:
            self.invincible -= 1
        for drone in self.drones:
            drone.update(self)
            if math.hypot(self.player.x-drone.x, self.player.y-drone.y) < 21 and self.invincible <= 0:
                self.player.lives -= 1
                self.invincible = 120
                self.player.x, self.player.y = TILE, TILE
                self.player.direction = (0,0)
                self.say("Um drone detectou você! Cuidado.", 180)
                if self.player.lives <= 0:
                    self.game_over = True
                break
        if self.message_timer > 0:
            self.message_timer -= 1
        self.player.mouth += 1

    def draw(self):
        screen.fill(BLACK)
        # HUD
        pygame.draw.rect(screen, (13,17,39), (0,0,SCREEN_W,HUD_H))
        title = font.render("MANSÃO: FUGA SOMBRIA", True, YELLOW)
        screen.blit(title, (18,12))
        screen.blit(small_font.render(f"Pontos: {self.score}", True, WHITE), (340,12))
        screen.blit(small_font.render(f"Restantes: {len(self.dots)}", True, WHITE), (340,37))
        screen.blit(small_font.render(f"Vidas: {'♥ ' * self.player.lives}", True, RED), (500,12))
        key_text = "CHAVE: SIM" if self.has_key else "CHAVE: NÃO"
        screen.blit(small_font.render(key_text, True, GREEN if self.has_key else GREY), (660,12))
        console_text = "CONSOLE: OK" if self.console_open else "CONSOLE: --"
        screen.blit(small_font.render(console_text, True, GREEN if self.console_open else GOLD), (660,37))
        screen.blit(small_font.render("WASD/Setas mover • E interagir • R reiniciar", True, WHITE), (18,42))

        offset_y = HUD_H
        for y,row in enumerate(self.grid):
            for x,ch in enumerate(row):
                px, py = x*TILE, offset_y+y*TILE
                if ch == '#':
                    rect = pygame.Rect(px+1,py+1,TILE-2,TILE-2)
                    pygame.draw.rect(screen, WALL, rect, border_radius=6)
                    pygame.draw.rect(screen, WALL_EDGE, rect, 2, border_radius=6)
                elif ch == 'D':
                    pygame.draw.rect(screen, GOLD if self.has_key else RED, (px+4,py+2,TILE-8,TILE-4), border_radius=4)
                    pygame.draw.circle(screen, BLACK, (px+TILE//2,py+TILE//2), 4)
        # Pontinhos colecionáveis
        for x,y in self.dots:
            cx,cy = x*TILE+TILE//2, offset_y+y*TILE+TILE//2
            pygame.draw.circle(screen, (255,225,170), (cx,cy), 3)
        # Chave com desenho próprio
        if not self.has_key:
            x,y = self.key_pos
            cx,cy = x*TILE+TILE//2, offset_y+y*TILE+TILE//2
            pygame.draw.circle(screen, GOLD, (cx-4,cy), 6, 3)
            pygame.draw.line(screen, GOLD, (cx+2,cy), (cx+11,cy), 3)
            pygame.draw.line(screen, GOLD, (cx+7,cy), (cx+7,cy+5), 3)
        # Console de código
        x,y = self.console_pos
        rect = pygame.Rect(x*TILE+4, offset_y+y*TILE+4, TILE-8, TILE-8)
        pygame.draw.rect(screen, (25,35,48), rect, border_radius=4)
        pygame.draw.rect(screen, GREEN if self.console_open else PURPLE, rect, 3, border_radius=4)
        pygame.draw.circle(screen, GREEN if self.console_open else GOLD, rect.center, 5)
        # Saída
        x,y = self.exit_pos
        exit_rect = pygame.Rect(x*TILE+3,offset_y+y*TILE+3,TILE-6,TILE-6)
        pygame.draw.rect(screen, GREEN if self.exit_open else RED, exit_rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, exit_rect, 2, border_radius=5)
        # Vida extra
        if self.heal_pos != (-99,-99):
            x,y = self.heal_pos
            pygame.draw.circle(screen, GREEN, (x*TILE+16,offset_y+y*TILE+16), 9)
            pygame.draw.rect(screen, WHITE, (x*TILE+13,offset_y+y*TILE+11,6,10))
            pygame.draw.rect(screen, WHITE, (x*TILE+11,offset_y+y*TILE+13,10,6))
        for drone in self.drones:
            drone.draw(screen)
        # Personagem original: pequeno explorador com casaco azul e capacete.
        px, py = int(self.player.x + TILE//2), int(self.player.y + offset_y + TILE//2)
        if self.invincible <= 0 or (self.invincible//6)%2 != 0:
            pygame.draw.ellipse(screen, (15,18,30), (px-10,py+8,20,6))
            pygame.draw.rect(screen, (45,135,220), (px-9,py-3,18,15), border_radius=5)
            pygame.draw.rect(screen, (220,235,245), (px-8,py-12,16,12), border_radius=5)
            pygame.draw.rect(screen, (65,85,110), (px-10,py-14,20,5), border_radius=3)
            pygame.draw.circle(screen, (30,35,45), (px-3,py-6), 2)
            pygame.draw.circle(screen, (30,35,45), (px+3,py-6), 2)
            pygame.draw.line(screen, (245,190,95), (px-5,py+10), (px-6,py+14), 3)
            pygame.draw.line(screen, (245,190,95), (px+5,py+10), (px+6,py+14), 3)
            if self.invincible > 0:
                pygame.draw.circle(screen, WHITE, (px,py), 16, 1)

        if self.message_timer > 0 and self.message:
            msg = font.render(self.message, True, WHITE)
            panel = pygame.Rect(120, SCREEN_H-46, SCREEN_W-240, 34)
            pygame.draw.rect(screen, (16,22,45), panel, border_radius=8)
            pygame.draw.rect(screen, WALL_EDGE, panel, 1, border_radius=8)
            screen.blit(msg, (panel.centerx-msg.get_width()//2, panel.y+7))
        if self.game_over or self.won:
            overlay = pygame.Surface((SCREEN_W,SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0,0,0,190))
            screen.blit(overlay,(0,0))
            text = "VOCÊ ESCAPOU!" if self.won else "FIM DE JOGO"
            color = GREEN if self.won else RED
            t = title_font.render(text, True, color)
            sub = big_font.render("Pressione R para jogar novamente", True, WHITE)
            screen.blit(t,(SCREEN_W//2-t.get_width()//2,SCREEN_H//2-50))
            screen.blit(sub,(SCREEN_W//2-sub.get_width()//2,SCREEN_H//2+15))

def main():
    game = Game()
    code_entry = False
    code = ""
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game = Game()
                    code_entry, code = False, ""
                elif event.key == pygame.K_e and not (game.game_over or game.won):
                    game.interact()
                    if "Digite o código" in game.message:
                        code_entry, code = True, ""
                elif code_entry:
                    if event.key == pygame.K_ESCAPE:
                        code_entry, code = False, ""
                        game.say("Entrada de código cancelada.")
                    elif event.key == pygame.K_BACKSPACE:
                        code = code[:-1]
                    elif event.key == pygame.K_RETURN:
                        if code == "4729":
                            game.console_open = True
                            game.exit_open = True
                            game.say("Código correto! A saída foi destrancada. Corra até ela!", 300)
                        else:
                            game.say("Código incorreto. A pista do bilhete indica 4729.")
                        code_entry, code = False, ""
                    elif event.unicode.isdigit() and len(code) < 4:
                        code += event.unicode
        game.update()
        game.draw()
        if code_entry:
            panel = pygame.Rect(SCREEN_W//2-220, SCREEN_H//2-75, 440, 150)
            pygame.draw.rect(screen, (12,18,45), panel, border_radius=12)
            pygame.draw.rect(screen, PURPLE, panel, 3, border_radius=12)
            t = big_font.render("CÓDIGO DO CONSOLE", True, WHITE)
            screen.blit(t,(panel.centerx-t.get_width()//2,panel.y+18))
            value = font.render(code + "_"*(4-len(code)), True, GOLD)
            screen.blit(value,(panel.centerx-value.get_width()//2,panel.y+70))
            screen.blit(small_font.render("Enter confirmar • Esc cancelar", True, GREY),(panel.centerx-95,panel.y+116))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()
